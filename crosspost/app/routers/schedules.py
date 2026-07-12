import uuid
import os
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from app.utils.json_db import schedules_db
from app.utils.logger import Logger
from app.services.upload_manager import process_upload, create_upload_record

router = APIRouter(prefix="/api/schedules", tags=["schedules"])


@router.get("")
async def list_schedules(
    platform: str = Query(None),
    status: str = Query(None),
    search: str = Query(None),
    date_from: str = Query(None),
    date_to: str = Query(None),
):
    schedules = schedules_db.read()
    schedules.sort(key=lambda x: x.get("scheduled_at", ""), reverse=False)

    if platform:
        schedules = [s for s in schedules if platform in s.get("platforms", [])]
    if status:
        schedules = [s for s in schedules if s.get("status") == status]
    if search:
        q = search.lower()
        schedules = [
            s for s in schedules
            if q in (s.get("title", "") or "").lower()
            or q in (s.get("description", "") or "").lower()
        ]
    if date_from:
        schedules = [s for s in schedules if s.get("scheduled_at", "") >= date_from]
    if date_to:
        schedules = [s for s in schedules if s.get("scheduled_at", "") <= date_to]

    return JSONResponse(schedules)


@router.get("/{schedule_id}")
async def get_schedule(schedule_id: str):
    schedules = schedules_db.read()
    for s in schedules:
        if s["id"] == schedule_id:
            return JSONResponse(s)
    raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")


@router.put("/{schedule_id}")
async def update_schedule(schedule_id: str, data: dict):
    schedules = schedules_db.read()
    existing = next((s for s in schedules if s["id"] == schedule_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    updates = {}
    for field in ("title", "description", "tags", "visibility", "platforms", "scheduled_at", "timezone"):
        if field in data:
            updates[field] = data[field]

    if not updates:
        raise HTTPException(status_code=400, detail="Tidak ada data yang diupdate")

    schedules_db.update(lambda x: x["id"] == schedule_id, updates)
    Logger.info(f"Schedule {schedule_id} diupdate")
    return JSONResponse({"success": True, "message": "Jadwal berhasil diupdate"})


@router.post("/{schedule_id}/cancel")
async def cancel_schedule(schedule_id: str):
    schedules = schedules_db.read()
    existing = next((s for s in schedules if s["id"] == schedule_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    if existing.get("status") not in ("scheduled",):
        raise HTTPException(status_code=400, detail="Hanya jadwal dengan status 'scheduled' yang bisa dibatalkan")

    schedules_db.update(lambda x: x["id"] == schedule_id, {"status": "cancelled"})
    Logger.info(f"Schedule {schedule_id} dibatalkan")
    return JSONResponse({"success": True, "message": "Jadwal berhasil dibatalkan"})


@router.post("/{schedule_id}/duplicate")
async def duplicate_schedule(schedule_id: str):
    schedules = schedules_db.read()
    existing = next((s for s in schedules if s["id"] == schedule_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    new_id = str(uuid.uuid4())
    new_schedule = {**existing, "id": new_id, "created_at": datetime.now().isoformat(), "status": "scheduled"}
    schedules_db.append(new_schedule)
    Logger.info(f"Schedule {schedule_id} diduplikasi menjadi {new_id}")
    return JSONResponse({"success": True, "message": "Jadwal berhasil diduplikasi", "id": new_id})


@router.post("/{schedule_id}/retry")
async def retry_schedule(schedule_id: str):
    from app.services.scheduler_service import publish_scheduled

    schedules = schedules_db.read()
    existing = next((s for s in schedules if s["id"] == schedule_id), None)
    if not existing:
        raise HTTPException(status_code=404, detail="Schedule tidak ditemukan")

    if existing.get("status") != "failed":
        raise HTTPException(status_code=400, detail="Hanya jadwal gagal yang bisa di-retry")

    schedules_db.update(lambda x: x["id"] == schedule_id, {
        "status": "scheduled",
        "error": None,
        "results": {},
    })

    import asyncio
    asyncio.create_task(publish_scheduled(existing))
    Logger.info(f"Schedule {schedule_id} di-retry")
    return JSONResponse({"success": True, "message": "Retry jadwal dimulai"})


@router.delete("/{schedule_id}")
async def delete_schedule(schedule_id: str):
    schedules_db.delete(lambda x: x["id"] == schedule_id)
    Logger.info(f"Schedule {schedule_id} dihapus")
    return JSONResponse({"success": True, "message": "Jadwal berhasil dihapus"})
