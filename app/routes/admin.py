from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import hash_password, verify_password, login_user, logout_user, require_admin
from app.database import (
    get_admin_by_username, create_faculty,
    get_all_students_full, get_all_faculty,
    mark_credits_processed, delete_faculty_by_id,
    reset_user_password, get_student_by_roll,
    get_faculty_by_empid,
)
from app.constants import SCHOOLS_DEPARTMENTS, SEMESTERS

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("admin/login.html", {
        "request": request, "error": None,
    })


@router.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    admin = get_admin_by_username(username.strip())
    if not admin or not verify_password(password, admin["password"]):
        return templates.TemplateResponse("admin/login.html", {
            "request": request, "error": "Invalid credentials.",
        })
    login_user(request, "admin", admin["id"], admin["username"])
    return RedirectResponse("/admin/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/admin/login", status_code=302)


@router.get("/dashboard")
def dashboard(request: Request):
    redir = require_admin(request)
    if redir:
        return redir

    school = request.query_params.get("school") or None
    department = request.query_params.get("department") or None
    semester = request.query_params.get("semester") or None

    students = get_all_students_full(school, department, semester)
    faculty_list = get_all_faculty()

    return templates.TemplateResponse("admin/dashboard.html", {
        "request": request,
        "students": students,
        "faculty_list": faculty_list,
        "schools": SCHOOLS_DEPARTMENTS,
        "semesters": SEMESTERS,
        "filter_school": school or "",
        "filter_dept": department or "",
        "filter_sem": semester or "",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    })


@router.post("/create-faculty")
def create_faculty_account(
    request: Request,
    name: str = Form(...),
    emp_id: str = Form(...),
    school: str = Form(...),
    department: str = Form(...),
    password: str = Form(...),
):
    redir = require_admin(request)
    if redir:
        return redir
    ok, err = create_faculty(name.strip(), emp_id.strip(), school, department, hash_password(password))
    if not ok:
        return RedirectResponse(f"/admin/dashboard?error={err}", status_code=302)
    return RedirectResponse("/admin/dashboard?success=Faculty+account+created.", status_code=302)


@router.post("/mark-processed/{cert_id}")
def mark_processed(request: Request, cert_id: int):
    redir = require_admin(request)
    if redir:
        return redir
    mark_credits_processed(cert_id)
    return RedirectResponse("/admin/dashboard?success=Credits+marked+as+processed.", status_code=302)

@router.post("/delete-faculty/{faculty_id}")
def delete_faculty(request: Request, faculty_id: int):
    redir = require_admin(request)
    if redir:
        return redir
    from app.database import delete_faculty_by_id
    delete_faculty_by_id(faculty_id)
    return RedirectResponse("/admin/dashboard?success=Faculty+account+deleted.", status_code=302)

@router.post("/reset-password")
def reset_password(
    request: Request,
    user_type: str = Form(...),
    identifier: str = Form(...),
    new_password: str = Form(...),
):
    redir = require_admin(request)
    if redir:
        return redir

    if user_type == "student":
        user = get_student_by_roll(identifier.strip())
    else:
        user = get_faculty_by_empid(identifier.strip())

    if not user:
        return RedirectResponse("/admin/dashboard?error=User+not+found.", status_code=302)

    reset_user_password(user_type, user["id"], hash_password(new_password))
    return RedirectResponse("/admin/dashboard?success=Password+reset+successfully.", status_code=302)

@router.post("/change-own-password")
def change_own_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
):
    redir = require_admin(request)
    if redir:
        return redir
    from app.database import get_admin_by_username
    from app.auth import verify_password
    admin = get_admin_by_username(request.session["user_name"])
    if not admin or not verify_password(current_password, admin["password"]):
        return RedirectResponse("/admin/dashboard?error=Current+password+is+incorrect.", status_code=302)
    from app.database import reset_user_password
    reset_user_password("admin", admin["id"], hash_password(new_password))
    return RedirectResponse("/admin/dashboard?success=Password+changed+successfully.", status_code=302)
