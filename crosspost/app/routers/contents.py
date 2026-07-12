from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import JSONResponse

from app.utils.json_db import uploads_db, contents_db
from app.utils.logger import Logger
from app.services.sync_service import import_all_posts, sync_all_stats, get_all_contents
from app.services.content_fetcher import _fetch_all_posts as fetch_all_posts_from_api
from app.services.upload_manager import DELETE_FUNCTIONS

router = APIRouter(prefix="/api/contents", tags=["contents"])


@router.get("")
async def list_contents(platform: str = None):
    contents = get_all_contents()
    contents.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    if platform:
        contents = [c for c in contents if c.get("platform") == platform]

    return JSONResponse(contents)


@router.get("/fetch")
async def get_platform_posts(platform: str = None):
    contents = get_all_contents()
    contents.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    if platform:
        contents = [c for c in contents if c.get("platform") == platform]

    return JSONResponse(contents)


@router.post("/import")
async def import_posts(platform: str = None):
    result = await import_all_posts(platform)
    Logger.info(f"Import posts result: {result}")
    return JSONResponse({"success": True, "imported": result})


@router.post("/sync")
async def sync_stats(platform: str = None):
    import_result = await import_all_posts(platform)
    sync_result = await sync_all_stats(platform, limit=100)
    Logger.info(f"Import result: {import_result}, Sync result: {sync_result}")
    return JSONResponse({
        "success": True,
        "imported": import_result,
        "synced": sync_result["synced"],
        "errors": sync_result["errors"],
    })


@router.get("/live")
async def live_fetch(platform: str = None):
    posts = await fetch_all_posts_from_api(platform)
    return JSONResponse(posts)


@router.put("/{content_id}")
async def update_content(content_id: str, data: dict):
    title = data.get("title")
    description = data.get("description")

    if not title and not description:
        raise HTTPException(status_code=400, detail="Tidak ada data yang diupdate")

    updates = {}
    if title:
        updates["title"] = title
    if description is not None:
        updates["description"] = description

    updated = contents_db.update(lambda x: x.get("id") == content_id, updates)
    Logger.info(f"Content {content_id} diupdate")
    return JSONResponse({"success": True, "message": "Konten berhasil diupdate"})


@router.delete("/{content_id}")
async def delete_content(content_id: str):
    contents = contents_db.read()
    item = next((c for c in contents if c.get("id") == content_id), None)

    if not item:
        raise HTTPException(status_code=404, detail="Konten tidak ditemukan")

    platform = item.get("platform")
    platform_post_id = item.get("platform_post_id")
    errors = []

    if platform and platform_post_id and platform in DELETE_FUNCTIONS:
        func = DELETE_FUNCTIONS[platform]
        try:
            result = await func(platform_post_id)
            if not result.get("success"):
                errors.append(result.get("error", f"Gagal hapus dari {platform}"))
        except Exception as e:
            errors.append(f"Error hapus dari {platform}: {str(e)}")

    contents_db.delete(lambda x: x.get("id") == content_id)
    Logger.info(f"Content {content_id} dihapus dari platform & database")

    if errors:
        return JSONResponse({"success": True, "warning": "; ".join(errors), "message": "Konten dihapus dari database, tapi beberapa platform gagal"})
    return JSONResponse({"success": True, "message": "Konten berhasil dihapus dari semua platform"})
