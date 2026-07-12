import os
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from app.utils.json_db import uploads_db, schedules_db
from app.utils.logger import Logger
from app.utils.validator import ALLOWED_IMAGE_EXTENSIONS, validate_file
from app.services.upload_manager import create_upload_record, process_upload
from config import UPLOAD_DIR

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str = Form(""),
    tags: str = Form(""),
    visibility: str = Form("public"),
    platforms: str = Form(""),
    thumbnail: UploadFile = File(None),
    scheduled_at: str = Form(""),
):
    file_size = 0
    file_path = None
    thumbnail_path = None

    is_valid, error_msg = validate_file(file.filename, 0)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    ext = Path(file.filename).suffix.lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    file_path = str(UPLOAD_DIR / unique_name)

    content = await file.read()
    file_size = len(content)

    is_valid, error_msg = validate_file(file.filename, file_size)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    with open(file_path, "wb") as f:
        f.write(content)

    if thumbnail and thumbnail.filename:
        thumb_content = await thumbnail.read()
        is_valid, error_msg = validate_file(thumbnail.filename, len(thumb_content), ALLOWED_IMAGE_EXTENSIONS)
        if not is_valid:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
            raise HTTPException(status_code=400, detail=error_msg)
        thumb_ext = Path(thumbnail.filename).suffix.lower()
        thumb_name = f"{uuid.uuid4()}_thumb{thumb_ext}"
        thumbnail_path = str(UPLOAD_DIR / thumb_name)
        with open(thumbnail_path, "wb") as f:
            f.write(thumb_content)

    platform_list = [p.strip().lower() for p in platforms.split(",") if p.strip()]

    tag_list = [t.strip() for t in tags.split(",") if t.strip()]

    from app.utils.json_db import settings_db
    settings = settings_db.read()
    if isinstance(settings, dict):
        desc_template = settings.get("description_template", "")
        if desc_template and description:
            description = f"{description}\n\n{desc_template}"
        elif desc_template and not description:
            description = desc_template

    record = create_upload_record(
        filename=file.filename,
        title=title,
        description=description,
        tags=tag_list,
        visibility=visibility,
        platforms=platform_list,
        file_size=file_size,
    )

    if scheduled_at:
        schedule_id = record["id"]
        schedule_record = {
            "id": schedule_id,
            "file_path": file_path,
            "thumbnail_path": thumbnail_path,
            "filename": file.filename,
            "title": title,
            "description": description,
            "tags": tag_list,
            "visibility": visibility,
            "platforms": platform_list,
            "scheduled_at": scheduled_at,
            "timezone": "UTC",
            "status": "scheduled",
            "results": {},
            "error": None,
            "created_at": datetime.now().isoformat(),
            "published_at": None,
        }
        schedules_db.append(schedule_record)
        uploads_db.update(
            lambda x: x["id"] == record["id"],
            {"status": "scheduled", "scheduled_at": scheduled_at},
        )
        Logger.info(f"Jadwal dibuat: {title} pada {scheduled_at}")
        return JSONResponse({
            "success": True,
            "upload_id": record["id"],
            "message": f"Konten akan dipublikasikan pada {scheduled_at}",
            "scheduled": True,
        })

    asyncio.create_task(
        process_upload(
            upload_id=record["id"],
            file_path=file_path,
            title=title,
            description=description,
            tags=tag_list,
            visibility=visibility,
            platforms=platform_list,
            thumbnail_path=thumbnail_path,
        )
    )

    return JSONResponse({
        "success": True,
        "upload_id": record["id"],
        "message": "Upload sedang diproses",
    })


@router.get("")
async def get_uploads():
    uploads = uploads_db.read()
    uploads.reverse()
    return JSONResponse(uploads)


@router.get("/{upload_id}")
async def get_upload(upload_id: str):
    uploads = uploads_db.read()
    for item in uploads:
        if item["id"] == upload_id:
            return JSONResponse(item)
    raise HTTPException(status_code=404, detail="Upload tidak ditemukan")


@router.delete("/{upload_id}")
async def delete_upload(upload_id: str):
    removed = uploads_db.delete(lambda x: x.get("id") == upload_id)
    schedules_db.delete(lambda x: x.get("id") == upload_id)
    Logger.info(f"Upload {upload_id} dihapus")
    return JSONResponse({"success": True, "message": "Upload berhasil dihapus"})
