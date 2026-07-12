from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import asyncio
from contextlib import asynccontextmanager
from app.utils.logger import Logger

from app.routers import auth, accounts, upload, settings, contents, stats, schedules
from app.utils.json_db import settings_db
from app.services.sync_service import import_all_posts
from app.services.scheduler_service import run_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    Logger.info("CrossPost starting up...")
    asyncio.create_task(import_all_posts())
    asyncio.create_task(run_scheduler())
    yield
    Logger.info("CrossPost shutting down...")


app = FastAPI(title="CrossPost", description="Self-hosted Social Media Publisher", lifespan=lifespan)

app.state.oauth_states = {}

app.mount("/static", StaticFiles(directory=Path(__file__).parent / "app" / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=Path(__file__).parent / "uploads"), name="uploads")
templates = Jinja2Templates(directory=Path(__file__).parent / "app" / "templates")

app.include_router(auth.router)
app.include_router(accounts.router)
app.include_router(upload.router)
app.include_router(settings.router)
app.include_router(contents.router)
app.include_router(stats.router)
app.include_router(schedules.router)


@app.get("/")
async def root():
    html_path = Path(__file__).parent / "app" / "templates" / "landing.html"
    with open(html_path, "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content, status_code=200)


@app.get("/dashboard")
async def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", {"active": "dashboard"})


@app.get("/analytics")
async def analytics_page(request: Request):
    return templates.TemplateResponse(request, "analytics.html", {"active": "analytics"})


@app.get("/accounts")
async def accounts_page(request: Request):
    return templates.TemplateResponse(request, "accounts.html", {"active": "accounts"})


@app.get("/upload")
async def upload_page(request: Request):
    return templates.TemplateResponse(request, "upload.html", {"active": "upload"})


@app.get("/history")
async def history_page(request: Request):
    return templates.TemplateResponse(request, "history.html", {"active": "history"})


@app.get("/scheduled")
async def scheduled_page(request: Request):
    return templates.TemplateResponse(request, "scheduled.html", {"active": "scheduled"})


@app.get("/settings")
async def settings_page(request: Request):
    return templates.TemplateResponse(request, "settings.html", {"active": "settings"})


@app.get("/contents")
async def contents_page(request: Request):
    return templates.TemplateResponse(request, "contents.html", {"active": "contents"})


def get_theme():
    s = settings_db.read()
    if isinstance(s, dict):
        return s.get("theme", "dark")
    return "dark"


@app.get("/privacy")
async def privacy_page(request: Request):
    return templates.TemplateResponse(request, "privacy.html", {"active": ""})


@app.get("/favicon.ico")
async def favicon():
    return RedirectResponse(url="/static/favicon.svg")


@app.get("/api/theme")
async def theme_api():
    return {"theme": get_theme()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
