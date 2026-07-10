from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from contextlib import asynccontextmanager
import os

from app.routers import users, publications, photos, accounts, admin
from app.database import close_pool, get_cursor


@asynccontextmanager
async def lifespan(_app: FastAPI):
    yield
    close_pool()

app = FastAPI(
    title="AcademiNet API",
    description="Red Social Universitaria — Motor de Alta Concurrencia",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Archivos estáticos
static_dir = os.path.join(os.path.dirname(__file__), "..", "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Templates Jinja2
templates = Jinja2Templates(
    directory=os.path.join(os.path.dirname(__file__), "templates")
)

# Routers API
app.include_router(users.router,        prefix="/api")
app.include_router(publications.router, prefix="/api")
app.include_router(photos.router,       prefix="/api")
app.include_router(accounts.router,     prefix="/api")
app.include_router(admin.router,        prefix="/api")


# ── Páginas HTML ──────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/usuarios-page", response_class=HTMLResponse)
async def page_usuarios(request: Request):
    return templates.TemplateResponse("usuarios.html", {"request": request})


@app.get("/publicaciones-page", response_class=HTMLResponse)
async def page_publicaciones(request: Request):
    return templates.TemplateResponse("publicaciones.html", {"request": request})


@app.get("/admin-page", response_class=HTMLResponse)
async def page_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})


@app.get("/fotografias-page", response_class=HTMLResponse)
async def page_fotografias(request: Request):
    return templates.TemplateResponse("fotografias.html", {"request": request})


@app.get("/health")
def health():
    """Comprueba aplicación y PostgreSQL; un fallo genera HTTP 500."""
    with get_cursor() as cur:
        cur.execute("SELECT 1 AS ok")
        database_ok = cur.fetchone()["ok"] == 1
    return {"status": "ok", "app": "AcademiNet", "database": database_ok}
