import asyncio
import httpx
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import config
from app.utils.json_db import accounts_db
from app.utils.logger import Logger


def get_instagram_account() -> Optional[dict]:
    accounts = accounts_db.read()
    for acc in accounts:
        if acc.get("platform") == "instagram" and acc.get("connected"):
            return acc
    return None


def _check_app_url() -> Optional[str]:
    app_url = config.APP_URL.rstrip("/")
    parsed = urlparse(app_url)
    host = parsed.hostname or ""
    if host in ("localhost", "127.0.0.1", "0.0.0.0"):
        return (
            f"APP_URL masih '{app_url}'. Instagram tidak bisa mengakses localhost. "
            f"Set APP_URL ke domain publik (atau pakai tunnel seperti ngrok) di file .env"
        )
    return None


async def delete_from_instagram(media_id: str) -> dict:
    account = get_instagram_account()
    if not account:
        return {"success": False, "error": "Akun Instagram tidak terhubung"}

    page_token = account.get("page_access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://graph.facebook.com/v18.0/{media_id}",
            params={"access_token": page_token},
        )
        if resp.status_code in (200, 204):
            return {"success": True}
        if resp.status_code == 404:
            return {"success": True, "note": "Post sudah tidak ada di Instagram"}
        Logger.warning(f"Instagram delete error {resp.status_code}: {resp.text[:300]}")
        return {"success": False, "error": f"Gagal hapus dari Instagram ({resp.status_code})"}


async def upload_to_instagram(file_path: str, title: str, description: str, **kwargs) -> dict:
    account = get_instagram_account()
    if not account:
        return {"success": False, "error": "Akun Instagram tidak terhubung"}

    url_warn = _check_app_url()
    if url_warn:
        return {"success": False, "error": url_warn}

    ig_id = account.get("instagram_account_id")
    page_token = account.get("page_access_token")
    if not ig_id or not page_token:
        return {"success": False, "error": "Data akun Instagram tidak lengkap"}

    import mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")

    media_url = f"{config.APP_URL.rstrip('/')}/uploads/{Path(file_path).name}"
    Logger.info(f"Instagram upload media_url={media_url}, is_video={is_video}, mime_type={mime_type}")

    async with httpx.AsyncClient(timeout=120.0) as client:
        if is_video:
            url = f"https://graph.facebook.com/v18.0/{ig_id}/media"
            params = {
                "media_type": "REELS",
                "video_url": media_url,
                "caption": f"{title}\n\n{description}",
                "access_token": page_token,
            }
            create_resp = await client.post(url, params=params)
            Logger.info(f"Instagram create response status={create_resp.status_code}, body={create_resp.text[:500]}")

            if create_resp.status_code not in (200, 201):
                err = f"Instagram media create failed ({create_resp.status_code}): {create_resp.text[:300]}"
                return {"success": False, "error": err}

            container_id = create_resp.json().get("id")
            if not container_id:
                return {"success": False, "error": "No container ID from Instagram"}

            for _ in range(30):
                status_resp = await client.get(
                    f"https://graph.facebook.com/v18.0/{container_id}",
                    params={
                        "fields": "status_code,status",
                        "access_token": page_token,
                    },
                )
                if status_resp.status_code != 200:
                    return {"success": False, "error": f"Instagram status check failed ({status_resp.status_code}): {status_resp.text[:300]}"}
                status_data = status_resp.json()
                Logger.info(f"Instagram status response={status_data}")
                status = status_data.get("status_code") or status_data.get("status")
                if status in ("FINISHED", "PUBLISHED"):
                    break
                if status == "ERROR":
                    err_detail = status_data.get("status", "")
                    hint = ""
                    if "2207077" in err_detail:
                        hint = " Kemungkinan: (1) Video tidak bisa diakses Instagram — pastikan APP_URL adalah URL publik, (2) Format video tidak didukung untuk Reels (pakai MP4 H.264, rasio 9:16, max 60 detik)"
                    return {"success": False, "error": f"Instagram video processing failed: {err_detail}.{hint}"}
                await asyncio.sleep(5)
            else:
                return {"success": False, "error": "Instagram video processing timeout"}

            publish_resp = await client.post(
                f"https://graph.facebook.com/v18.0/{ig_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": page_token,
                },
            )
            Logger.info(f"Instagram publish response status={publish_resp.status_code}, body={publish_resp.text[:500]}")
            if 200 <= publish_resp.status_code < 300:
                data = publish_resp.json() if publish_resp.text else {}
                return {"success": True, "platform_id": data.get("id", "")}
            return {"success": False, "error": f"Instagram publish failed ({publish_resp.status_code}): {publish_resp.text[:300]}"}

        else:
            upload_resp = await client.post(
                f"https://graph.facebook.com/v18.0/{ig_id}/media",
                params={
                    "image_url": media_url,
                    "caption": f"{title}\n\n{description}",
                    "access_token": page_token,
                },
            )
            Logger.info(f"Instagram image create response status={upload_resp.status_code}, body={upload_resp.text[:500]}")
            if upload_resp.status_code not in (200, 201):
                return {"success": False, "error": f"Instagram image create failed: {upload_resp.text[:300]}"}

            container_id = upload_resp.json().get("id")
            if not container_id:
                return {"success": False, "error": f"No container ID from Instagram image create: {upload_resp.text[:300]}"}
            publish_resp = await client.post(
                f"https://graph.facebook.com/v18.0/{ig_id}/media_publish",
                params={
                    "creation_id": container_id,
                    "access_token": page_token,
                },
            )
            Logger.info(f"Instagram image publish response status={publish_resp.status_code}, body={publish_resp.text[:500]}")
            if 200 <= publish_resp.status_code < 300:
                data = publish_resp.json() if publish_resp.text else {}
                return {"success": True, "platform_id": data.get("id", "")}
            return {"success": False, "error": f"Instagram publish failed ({publish_resp.status_code}): {publish_resp.text[:300]}"}
