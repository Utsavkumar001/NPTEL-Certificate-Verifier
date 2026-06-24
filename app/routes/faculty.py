from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import verify_password, login_user, logout_user, require_faculty
from app.database import (
    get_faculty_by_empid, get_faculty_by_id,
    get_faculty_department_students, update_request_status,
    set_requests_open,
)
from app.constants import SEMESTERS

router = APIRouter(prefix="/faculty")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))


@router.get("/login")
def login_page(request: Request):
    return templates.TemplateResponse("faculty/login.html", {
        "request": request, "error": None,
    })


@router.post("/login")
def login_submit(request: Request, emp_id: str = Form(...), password: str = Form(...)):
    faculty = get_faculty_by_empid(emp_id.strip())
    if not faculty or not verify_password(password, faculty["password"]):
        return templates.TemplateResponse("faculty/login.html", {
            "request": request, "error": "Invalid Employee ID or password.",
        })
    login_user(request, "faculty", faculty["id"], faculty["name"])
    return RedirectResponse("/faculty/dashboard", status_code=302)


@router.get("/logout")
def logout(request: Request):
    logout_user(request)
    return RedirectResponse("/faculty/login", status_code=302)


@router.get("/dashboard")
def dashboard(request: Request):
    redir = require_faculty(request)
    if redir:
        return redir
    faculty = get_faculty_by_id(request.session["user_id"])
    semester = request.query_params.get("semester") or None
    students = get_faculty_department_students(faculty["department"], semester)
    return templates.TemplateResponse("faculty/dashboard.html", {
        "request": request,
        "faculty": faculty,
        "students": students,
        "semesters": SEMESTERS,
        "filter_sem": semester or "",
        "success": request.query_params.get("success"),
        "error": request.query_params.get("error"),
    })


@router.post("/toggle-requests")
def toggle_requests(request: Request):
    redir = require_faculty(request)
    if redir:
        return redir
    faculty = get_faculty_by_id(request.session["user_id"])
    new_val = 0 if faculty["requests_open"] else 1
    set_requests_open(faculty["id"], new_val)
    msg = "Course+requests+opened." if new_val else "Course+requests+closed."
    return RedirectResponse(f"/faculty/dashboard?success={msg}", status_code=302)


@router.post("/approve/{request_id}")
def approve(request: Request, request_id: int):
    redir = require_faculty(request)
    if redir:
        return redir
    fid = request.session["user_id"]
    update_request_status(request_id, "approved", fid)
    return RedirectResponse("/faculty/dashboard?success=Course+request+approved.", status_code=302)


@router.post("/reject/{request_id}")
def reject(request: Request, request_id: int, remarks: str = Form("")):
    redir = require_faculty(request)
    if redir:
        return redir
    fid = request.session["user_id"]
    update_request_status(request_id, "rejected", fid, remarks)
    return RedirectResponse("/faculty/dashboard?success=Course+request+rejected.", status_code=302)

@router.post("/allow-reupload/{request_id}")
def allow_reupload(request: Request, request_id: int):
    redir = require_faculty(request)
    if redir:
        return redir
    from app.database import delete_certificate_by_request
    delete_certificate_by_request(request_id)
    return RedirectResponse("/faculty/dashboard?success=Re-upload+allowed+for+student.", status_code=302)