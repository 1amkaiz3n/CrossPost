import httpx
import mimetypes
from typing import Optional

from app.utils.json_db import accounts_db
from app.utils.logger import Logger


def get_facebook_account() -> Optional[dict]:
    accounts = accounts_db.read()
    for acc in accounts:
        if acc.get("platform") == "facebook" and acc.get("connected"):
            return acc
    return None


async def delete_from_facebook(post_id: str) -> dict:
    account = get_facebook_account()
    if not account:
        return {"success": False, "error": "Akun Facebook tidak terhubung"}

    page_token = account.get("page_access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://graph.facebook.com/v18.0/{post_id}",
            params={"access_token": page_token},
        )
        if resp.status_code in (200, 204):
            return {"success": True}
        if resp.status_code == 404:
            return {"success": True, "note": "Post sudah tidak ada di Facebook"}
        Logger.warning(f"Facebook delete error {resp.status_code}: {resp.text[:300]}")
        return {"success": False, "error": f"Gagal hapus dari Facebook ({resp.status_code})"}


async def upload_to_facebook(file_path: str, title: str, description: str, **kwargs) -> dict:
    account = get_facebook_account()
    if not account:
        return {"success": False, "error": "Akun Facebook tidak terhubung"}

    page_id = account.get("page_id")
    page_token = account.get("page_access_token")
    if not page_id or not page_token:
        return {"success": False, "error": "Data halaman Facebook tidak lengkap"}

    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if is_video:
                url = f"https://graph.facebook.com/v18.0/{page_id}/videos"
                with open(file_path, "rb") as f:
                    files = {
                        "source": (file_path, f, mime_type or "video/mp4"),
                        "access_token": (None, page_token),
                        "title": (None, title),
                        "description": (None, description),
                        "published": (None, "true"),
                    }
                    resp = await client.post(url, files=files)
            else:
                url = f"https://graph.facebook.com/v18.0/{page_id}/photos"
                with open(file_path, "rb") as f:
                    files = {
                        "source": (file_path, f, mime_type or "image/jpeg"),
                        "access_token": (None, page_token),
                        "caption": (None, f"{title}\n\n{description}"),
                    }
                    resp = await client.post(url, files=files)

            Logger.info(f"Facebook upload response status={resp.status_code}, body={resp.text[:500]}")
            if 200 <= resp.status_code < 300:
                data = resp.json() if resp.text else {}
                platform_id = data.get("id") or data.get("post_id") or data.get("video_id", "")
                return {"success": True, "platform_id": platform_id}
            return {"success": False, "error": f"Facebook upload failed ({resp.status_code}): {resp.text}"}
    except httpx.TimeoutException:
        Logger.warning("Facebook upload timeout after request was sent; treating as success because video may still be processing on Facebook")
        return {"success": True, "platform_id": ""}
