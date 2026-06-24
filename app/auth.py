from passlib.context import CryptContext
from starlette.requests import Request
from fastapi.responses import RedirectResponse

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_ctx.verify(plain, hashed)


def get_session(request: Request) -> dict:
    return request.session


def login_user(request: Request, user_type: str, user_id: int, user_name: str):
    request.session["user_type"] = user_type
    request.session["user_id"] = user_id
    request.session["user_name"] = user_name


def logout_user(request: Request):
    request.session.clear()


def require_student(request: Request):
    if request.session.get("user_type") != "student":
        return RedirectResponse("/student/login", status_code=302)
    return None


def require_faculty(request: Request):
    if request.session.get("user_type") != "faculty":
        return RedirectResponse("/faculty/login", status_code=302)
    return None


def require_admin(request: Request):
    if request.session.get("user_type") != "admin":
        return RedirectResponse("/admin/login", status_code=302)
    return None
