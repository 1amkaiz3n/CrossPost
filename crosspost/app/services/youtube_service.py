import httpx
from typing import Optional

from app.utils.json_db import accounts_db
from app.oauth.google_oauth import refresh_google_token


def get_youtube_account() -> Optional[dict]:
    accounts = accounts_db.read()
    for acc in accounts:
        if acc.get("platform") == "youtube" and acc.get("connected"):
            return acc
    return None


async def upload_to_youtube(
    file_path: str,
    title: str,
    description: str,
    tags: list[str],
    visibility: str,
    thumbnail_path: Optional[str] = None,
) -> dict:
    account = get_youtube_account()
    if not account:
        return {"success": False, "error": "Akun YouTube tidak terhubung"}

    token_data = await refresh_google_token(account["refresh_token"])
    if not token_data:
        return {"success": False, "error": "Gagal refresh token YouTube"}

    access_token = token_data.get("access_token")
    base_url = "https://www.googleapis.com/upload/youtube/v3/videos"
    params = {
        "part": "snippet,status",
        "access_token": access_token,
        "uploadType": "resumable",
    }

    metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags if tags else [],
            "channelId": account.get("channel_id"),
        },
        "status": {
            "privacyStatus": visibility,
            "selfDeclaredMadeForKids": False,
        },
    }

    async with httpx.AsyncClient() as client:
        init_resp = await client.post(
            base_url,
            params=params,
            headers={"Content-Type": "application/json; charset=UTF-8"},
            json=metadata,
        )
        if init_resp.status_code not in (200, 201):
            return {"success": False, "error": f"YouTube init failed: {init_resp.text}"}

        upload_url = init_resp.headers.get("Location")
        if not upload_url:
            return {"success": False, "error": "No upload URL from YouTube"}

        with open(file_path, "rb") as f:
            file_data = f.read()

        upload_resp = await client.put(
            upload_url,
            headers={"Content-Type": "application/octet-stream"},
            content=file_data,
        )
        if upload_resp.status_code in (200, 201):
            video_id = upload_resp.json().get("id", "")
            if thumbnail_path:
                await upload_thumbnail(video_id, thumbnail_path, access_token)
            return {"success": True, "platform_id": video_id, "url": f"https://youtube.com/watch?v={video_id}"}
        else:
            return {"success": False, "error": f"YouTube upload failed: {upload_resp.text}"}


async def delete_from_youtube(video_id: str) -> dict:
    account = get_youtube_account()
    if not account:
        return {"success": False, "error": "Akun YouTube tidak terhubung"}

    token_data = await refresh_google_token(account["refresh_token"])
    if not token_data:
        return {"success": False, "error": "Gagal refresh token YouTube"}

    access_token = token_data.get("access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://www.googleapis.com/youtube/v3/videos",
            params={"id": video_id},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code in (200, 204):
            return {"success": True}
        if resp.status_code == 404:
            return {"success": True, "note": "Video sudah tidak ada di YouTube"}
        Logger.warning(f"YouTube delete error {resp.status_code}: {resp.text[:300]}")
        return {"success": False, "error": f"Gagal hapus dari YouTube ({resp.status_code})"}


async def upload_thumbnail(video_id: str, thumbnail_path: str, access_token: str) -> bool:
    async with httpx.AsyncClient() as client:
        with open(thumbnail_path, "rb") as f:
            resp = await client.post(
                f"https://www.googleapis.com/upload/youtube/v3/thumbnails/set",
                params={"videoId": video_id, "access_token": access_token},
                files={"media": f},
            )
            return resp.status_code in (200, 201)
