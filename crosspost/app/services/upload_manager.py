import os
import asyncio
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.utils.json_db import uploads_db, schedules_db
from app.utils.logger import Logger
from app.services.youtube_service import upload_to_youtube, delete_from_youtube
from app.services.facebook_service import upload_to_facebook, delete_from_facebook
from app.services.instagram_service import upload_to_instagram, delete_from_instagram
from app.services.linkedin_service import upload_to_linkedin, delete_from_linkedin
from app.services.threads_service import post_to_threads, delete_from_threads
from app.services.sync_service import register_upload_content


PLATFORM_FUNCTIONS = {
    "youtube": upload_to_youtube,
    "facebook": upload_to_facebook,
    "instagram": upload_to_instagram,
    "linkedin": upload_to_linkedin,
    "threads": post_to_threads,
}

DELETE_FUNCTIONS = {
    "youtube": delete_from_youtube,
    "facebook": delete_from_facebook,
    "instagram": delete_from_instagram,
    "linkedin": delete_from_linkedin,
    "threads": delete_from_threads,
}


async def process_upload(
    upload_id: str,
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    visibility: str,
    platforms: list[str],
    thumbnail_path: Optional[str] = None,
    schedule_mode: bool = False,
) -> None:
    results = {}
    for platform in platforms:
        uploads_db.update(
            lambda x: x["id"] == upload_id,
            {
                "statuses": {**results, platform: {"status": "uploading", "progress": 0}},
            },
        )

        Logger.info(f"Upload ke {platform} dimulai untuk {title}")

        try:
            func = PLATFORM_FUNCTIONS.get(platform)
            if not func:
                results[platform] = {"status": "error", "error": f"Platform {platform} tidak dikenal"}
                continue

            uploads_db.update(
                lambda x: x["id"] == upload_id,
                {
                    "statuses": {**results, platform: {"status": "uploading", "progress": 50}},
                },
            )

            uploads_db.update(
                lambda x: x["id"] == upload_id,
                {
                    "statuses": {**results, platform: {"status": "uploading", "progress": 75}},
                },
            )

            result = await func(file_path=file_path, title=title, description=description, tags=tags, visibility=visibility, thumbnail_path=thumbnail_path)

            if result.get("success"):
                results[platform] = {
                    "status": "success",
                    "progress": 100,
                    "platform_id": result.get("platform_id"),
                    "url": result.get("url"),
                }
                pid = result.get("platform_id")
                if pid:
                    import mimetypes
                    mime_type, _ = mimetypes.guess_type(file_path)
                    is_video = mime_type and mime_type.startswith("video")
                    register_upload_content(
                        platform=platform,
                        platform_post_id=pid,
                        title=title,
                        description=description,
                        url=result.get("url", ""),
                        thumbnail=thumbnail_path or "",
                        media_type="video" if is_video else "image",
                        published_at=datetime.now().isoformat(),
                    )
                Logger.success(f"Upload ke {platform} berhasil untuk {title}")
            else:
                results[platform] = {
                    "status": "error",
                    "progress": 0,
                    "error": result.get("error", "Unknown error"),
                }
                Logger.error(f"Upload ke {platform} gagal: {result.get('error')}")

        except Exception as e:
            results[platform] = {
                "status": "error",
                "progress": 0,
                "error": str(e),
            }
            Logger.error(f"Upload ke {platform} error: {str(e)}")

        uploads_db.update(
            lambda x: x["id"] == upload_id,
            {
                "statuses": results,
            },
        )

    all_success = all(r.get("status") == "success" for r in results.values())
    uploads_db.update(
        lambda x: x["id"] == upload_id,
        {
            "statuses": results,
            "status": "completed" if all_success else "partial",
            "completed_at": datetime.now().isoformat(),
        },
    )

    if all_success:
        Logger.success(f"Upload {title} selesai ke semua platform")
    else:
        Logger.warning(f"Upload {title} selesai dengan beberapa error")

    if schedule_mode:
        schedules_db.update(
            lambda x: x["id"] == upload_id,
            {
                "status": "published" if all_success else "failed",
                "results": results,
                "error": None if all_success else "Beberapa platform gagal",
                "published_at": datetime.now().isoformat(),
            },
        )

    cleanup_uploaded_files(file_path, thumbnail_path)


def cleanup_uploaded_files(file_path: Optional[str], thumbnail_path: Optional[str]) -> None:
    for path in [file_path, thumbnail_path]:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                Logger.info(f"File sementara dihapus: {path}")
            except OSError as e:
                Logger.warning(f"Gagal hapus file sementara {path}: {e}")


def create_upload_record(
    filename: str,
    title: str,
    description: str,
    tags: list[str],
    visibility: str,
    platforms: list[str],
    file_size: int,
) -> dict:
    upload_id = str(uuid.uuid4())
    record = {
        "id": upload_id,
        "filename": filename,
        "title": title,
        "description": description,
        "tags": tags,
        "visibility": visibility,
        "platforms": platforms,
        "file_size": file_size,
        "status": "pending",
        "statuses": {p: {"status": "pending", "progress": 0} for p in platforms},
        "created_at": datetime.now().isoformat(),
        "completed_at": None,
    }
    uploads_db.append(record)
    Logger.info(f"Upload baru dibuat: {title}")
    return record
