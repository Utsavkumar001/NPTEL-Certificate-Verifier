import os
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.database import init_db
from app.routes import student, faculty, admin

BASE = Path(__file__).parent

app = FastAPI(title="NPTEL Credit Transfer System")
app.add_middleware(
    SessionMiddleware,
    secret_key=os.environ.get("SECRET_KEY", "nptel-pilot-secret-key-2026")
)

app.mount("/static", StaticFiles(directory=str(BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE / "templates"))

app.include_router(student.router)
app.include_router(faculty.router)
app.include_router(admin.router)


@app.on_event("startup")
def startup():
    init_db()


@app.get("/")
def root(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="landing.html"
    )


@app.get("/health")
def health():
    return {"status": "ok"}


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"message": "Something went wrong. Please try again."},
        status_code=500,
    )


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={"message": "Page not found."},
        status_code=404,
    )