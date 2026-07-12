import shutil
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
from app.utils.json_db import settings_db
from app.utils.logger import Logger
from config import DATABASE_DIR

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
async def get_settings():
    settings = settings_db.read()
    if not settings:
        settings = {
            "theme": "dark",
            "upload_folder": "uploads",
        }
        settings_db.write(settings)
    return JSONResponse(settings)


@router.post("")
async def update_settings(request: Request):
    data = await request.json()
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Format pengaturan tidak valid")
    current = settings_db.read()
    if not isinstance(current, dict):
        current = {}
    current.update(data)
    settings_db.write(current)
    Logger.info("Pengaturan diperbarui")
    return JSONResponse({"success": True, "message": "Pengaturan berhasil disimpan"})


@router.get("/backup")
async def backup_json():
    backup_name = f"backup-crosspost.zip"
    shutil.make_archive(
        str(DATABASE_DIR.parent / "backup-crosspost"),
        "zip",
        DATABASE_DIR,
    )
    return FileResponse(
        str(DATABASE_DIR.parent / "backup-crosspost.zip"),
        media_type="application/zip",
        filename=backup_name,
    )
