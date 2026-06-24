import tempfile, os
from fastapi import APIRouter, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import hash_password, verify_password, login_user, logout_user, require_student
from app.database import (
    create_student, get_student_by_roll, get_student_by_id,
    create_course_request, get_all_requests_for_student,
    get_request_by_id, confirm_request,
    get_certificate_by_request, save_certificate,
    get_total_credits, is_cert_used, mark_cert_used,
    get_faculty_by_department, update_student_semester,
)
from app.constants import SCHOOLS_DEPARTMENTS, SEMESTERS
from app.qr_extractor import extract_qr_url, QRExtractionError
from app.official_fetch import fetch_official_pdf, OfficialFetchError
from app.pdf_parser import extract_certificate_data
from app.comparator import compare_certificates, all_passed
from app.eligibility import calculate_credits
from app.file_validation import validate_uploaded_pdf

router = APIRouter(prefix="/student")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("student/register.html", {
        "request": request,
        "schools": SCHOOLS_DEPARTMENTS,
        "semesters": SEMESTERS,
        "error": None,
    })


@router.post("/register")
def register_submit(
    request: Request,
    name: str = Form(...),
    roll: str = Form(...),
    cls: str = Form(...),
    semester: str = Form(...),
    school: str = Form(...),
    department: str = Form(...),
    password: str = Form(...),
):
    ok, err = create_student(name.strip(), roll.strip(), cls.strip(),
                              semester, school, department, hash_password(password))
    if not ok:
        return templates.TemplateResponse("student/register.html", {
            "request": request, "schools": SCHOOLS_DEPARTMENTS,
            "semesters": SEMESTERS, "error": err,
        })
    return RedirectResponse("/student/login?registered=1", status_code=302)


@router.get("/login")
def login_page(request: Request, registered: str = None):
    return templates.TemplateResponse("student/login.html", {
        "request": request,
        "error": None,
        "success": "Registration successful! Please log in." if registered else None,
    })


@router.post("/login")
def login_submit(request: Request, roll: str = Form(...), password: str = Form(...)):
    student = get_student_by_roll(roll.strip())
    if not student or not verify_password(password, student["password"]):
        return templates.TemplateResponse("student/login.html", {
            "request": request, "error": "Invalid roll number or password.", "success": None,
        })
    login_user(request, "student", student["id"], student["name"])
    return RedirectResponse("/student/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/student/login", status_code=302)


@router.get("/dashboard")
def dashboard(request: Request):
    redir = require_student(request)
    if redir:
        return redir

    student = get_student_by_id(request.session["user_id"])
    requests = get_all_requests_for_student(student["id"])
    total_credits = get_total_credits(student["id"])
    faculty = get_faculty_by_department(student["department"])
    requests_open = faculty["requests_open"] if faculty else 0

    courses = []
    for req in requests:
        cert = get_certificate_by_request(req["id"])
        courses.append({"req": req, "cert": cert})

    return templates.TemplateResponse("student/dashboard.html", {
        "request": request,
        "student": student,
        "courses": courses,
        "total_credits": total_credits,
        "requests_open": requests_open,
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })


@router.post("/request-course")
def request_course(
    request: Request,
    course_name: str = Form(...),
    nptel_course_id: str = Form(...),
):
    redir = require_student(request)
    if redir:
        return redir

    sid = request.session["user_id"]
    student = get_student_by_id(sid)

    faculty = get_faculty_by_department(student["department"])
    if not faculty or not faculty["requests_open"]:
        return RedirectResponse("/student/dashboard?error=Course+requests+are+currently+closed.", status_code=302)

    existing_requests = get_all_requests_for_student(sid)
    cn = course_name.strip().lower()
    for r in existing_requests:
        if r["course_name"].strip().lower() == cn:
            if r["status"] in ("pending", "approved"):
                return RedirectResponse("/student/dashboard?error=You+already+have+an+active+request+for+this+course.", status_code=302)
            cert = get_certificate_by_request(r["id"])
            if cert and cert["certificate_status"] == "VERIFIED" and cert["credit_transfer_status"] == "ELIGIBLE":
                return RedirectResponse("/student/dashboard?error=Credit+for+this+course+has+already+been+transferred.", status_code=302)

    create_course_request(sid, course_name.strip(), nptel_course_id.strip())
    return RedirectResponse("/student/dashboard?success=Course+request+submitted.", status_code=302)


@router.post("/confirm-registration/{request_id}")
def confirm_registration(request: Request, request_id: int):
    redir = require_student(request)
    if redir:
        return redir
    sid = request.session["user_id"]
    req = get_request_by_id(request_id)
    if req and req["student_id"] == sid and req["status"] == "approved":
        confirm_request(request_id)
    return RedirectResponse("/student/dashboard?success=Registration+confirmed.", status_code=302)


@router.post("/upload-certificate/{request_id}")
async def upload_certificate(request: Request, request_id: int, file: UploadFile = File(...)):
    redir = require_student(request)
    if redir:
        return redir

    sid = request.session["user_id"]
    student = get_student_by_id(sid)
    course_req = get_request_by_id(request_id)

    if not course_req or course_req["student_id"] != sid:
        return RedirectResponse("/student/dashboard?error=Invalid+request.", status_code=302)
    if course_req["status"] != "approved" or not course_req["confirmed"]:
        return RedirectResponse("/student/dashboard?error=Not+eligible+to+upload+yet.", status_code=302)

    suffix = os.path.splitext(file.filename or "")[1] or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    cert_status = "REJECTED"
    credit_status = None
    certificate_id = None
    course_name = None
    course_code = None
    credits = None
    weeks = None
    rejection_reason = None

    try:
        fv = validate_uploaded_pdf(tmp_path, file.filename or "")
        if not fv.valid:
            return RedirectResponse(f"/student/dashboard?error={fv.error_message}", status_code=302)

        try:
            qr_url = extract_qr_url(tmp_path)
        except QRExtractionError as e:
            return RedirectResponse(f"/student/dashboard?error={str(e)}", status_code=302)

        try:
            official_bytes = fetch_official_pdf(qr_url)
        except OfficialFetchError as e:
            return RedirectResponse(f"/student/dashboard?error={e.message}", status_code=302)

        official = extract_certificate_data(official_bytes)
        uploaded = extract_certificate_data(tmp_path)

        checks = compare_certificates(uploaded, official)
        failed = next((c for c in checks if c.status == "FAIL"), None)

        if failed:
            rejection_reason = failed.reason

        # EMS name check — must match name given at registration time
        elif (official.student_name or "").strip().lower() != student["name"].strip().lower():
            rejection_reason = (
                f"Certificate name '{official.student_name}' does not match "
                f"your registered name '{student['name']}'."
            )

        # Course name triple check — uploaded PDF, official PDF, and course request must all match
        elif (
            (uploaded.course_name or "").strip().lower() !=
            (course_req["course_name"] or "").strip().lower()
            or
            (official.course_name or "").strip().lower() !=
            (course_req["course_name"] or "").strip().lower()
        ):
            rejection_reason = (
                f"Course name mismatch. Requested: '{course_req['course_name']}', "
                f"Uploaded certificate: '{uploaded.course_name}', "
                f"Official certificate: '{official.course_name}'."
            )

        # Duplicate certificate check
        elif is_cert_used(official.certificate_id):
            rejection_reason = "This certificate has already been used for credit transfer."

        else:
            cert_status = "VERIFIED"
            credit_status = "ELIGIBLE"
            mark_cert_used(official.certificate_id, student["roll"])

        certificate_id = official.certificate_id
        course_name = official.course_name
        weeks = official.weeks
        credits = calculate_credits(weeks)

    finally:
        os.unlink(tmp_path)

    saved = save_certificate(
        sid, request_id, certificate_id or "UNKNOWN",
        course_name, course_code, credits, weeks,
        cert_status, credit_status, rejection_reason
    )

    if not saved:
        return RedirectResponse("/student/dashboard?error=Certificate+already+submitted+for+this+course.", status_code=302)

    if cert_status == "VERIFIED":
        return RedirectResponse("/student/dashboard?success=Certificate+verified+successfully.", status_code=302)
    else:
        msg = (rejection_reason or "Verification failed.").replace(" ", "+")
        return RedirectResponse(f"/student/dashboard?error={msg}", status_code=302)
    
@router.post("/edit-profile")
def edit_profile(request: Request, semester: str = Form(...)):
    redir = require_student(request)
    if redir:
        return redir
    sid = request.session["user_id"]
    update_student_semester(sid, semester)
    return RedirectResponse("/student/dashboard?success=Semester+updated+successfully.", status_code=302)