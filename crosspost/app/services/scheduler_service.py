import asyncio
from datetime import datetime
from typing import Optional

from app.utils.json_db import schedules_db
from app.utils.logger import Logger
from app.services.upload_manager import process_upload


async def run_scheduler(interval: int = 30):
    Logger.info("Scheduler started, checking every %d seconds", interval)
    while True:
        try:
            await check_and_publish()
        except Exception as e:
            Logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(interval)


async def check_and_publish():
    now = datetime.now().isoformat()
    schedules = schedules_db.read()

    for s in schedules:
        if s.get("status") != "scheduled":
            continue
        scheduled_at = s.get("scheduled_at", "")
        if scheduled_at and scheduled_at <= now:
            await publish_scheduled(s)


async def publish_scheduled(schedule: dict) -> None:
    schedule_id = schedule["id"]
    Logger.info(f"Publishing scheduled post: {schedule.get('title', '')} ({schedule_id})")

    schedules_db.update(
        lambda x: x["id"] == schedule_id,
        {"status": "publishing"},
    )

    try:
        await process_upload(
            upload_id=schedule_id,
            file_path=schedule["file_path"],
            title=schedule["title"],
            description=schedule.get("description", ""),
            tags=schedule.get("tags", []),
            visibility=schedule.get("visibility", "public"),
            platforms=schedule.get("platforms", []),
            thumbnail_path=schedule.get("thumbnail_path"),
            schedule_mode=True,
        )
    except Exception as e:
        Logger.error(f"Scheduled publish failed for {schedule_id}: {e}")
        schedules_db.update(
            lambda x: x["id"] == schedule_id,
            {
                "status": "failed",
                "error": str(e),
                "published_at": datetime.now().isoformat(),
            },
        )
