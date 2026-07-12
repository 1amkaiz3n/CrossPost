import asyncio
import httpx
import mimetypes
from pathlib import Path
from typing import Optional

import config
from app.utils.json_db import accounts_db
from app.utils.logger import Logger
from app.oauth.threads_oauth import exchange_to_long_lived_token


def get_threads_account() -> Optional[dict]:
    accounts = accounts_db.read()
    for acc in accounts:
        if acc.get("platform") == "threads" and acc.get("connected"):
            return acc
    return None


async def ensure_valid_token(account: dict) -> Optional[str]:
    access_token = account.get("access_token") or config.THREADS_ACCESS_TOKEN
    if not access_token:
        return None

    async with httpx.AsyncClient() as client:
        check = await client.get(
            "https://graph.threads.net/v1.0/me",
            params={"fields": "id", "access_token": access_token},
        )
        if check.status_code == 200:
            return access_token

    long_lived = await exchange_to_long_lived_token(access_token)
    if long_lived:
        accounts_db.update(
            lambda x: x.get("platform") == "threads",
            {"access_token": long_lived},
        )
        return long_lived

    fallback = config.THREADS_ACCESS_TOKEN
    if fallback and fallback != access_token:
        async with httpx.AsyncClient() as client:
            check = await client.get(
                "https://graph.threads.net/v1.0/me",
                params={"fields": "id", "access_token": fallback},
            )
            if check.status_code == 200:
                accounts_db.update(
                    lambda x: x.get("platform") == "threads",
                    {"access_token": fallback},
                )
                return fallback

    return None


async def delete_from_threads(media_id: str) -> dict:
    account = get_threads_account()
    if not account:
        return {"success": False, "error": "Akun Threads tidak terhubung"}

    access_token = account.get("access_token") or config.THREADS_ACCESS_TOKEN

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://graph.threads.net/v1.0/{media_id}",
            params={"access_token": access_token},
        )
        if resp.status_code in (200, 204):
            return {"success": True}
        if resp.status_code == 404:
            return {"success": True, "note": "Post sudah tidak ada di Threads"}
        Logger.warning(f"Threads delete error {resp.status_code}: {resp.text[:300]}")
        return {"success": False, "error": f"Gagal hapus dari Threads ({resp.status_code})"}


async def post_to_threads(file_path: str, title: str, description: str, **kwargs) -> dict:
    account = get_threads_account()
    if not account:
        return {"success": False, "error": "Akun Threads tidak terhubung"}

    threads_id = account.get("threads_user_id")
    if not threads_id:
        return {"success": False, "error": "Data akun Threads tidak lengkap"}

    access_token = await ensure_valid_token(account)
    if not access_token:
        return {"success": False, "error": "Token Threads tidak valid. Silahkan hubungkan ulang akun Threads."}

    text = f"{title}\n\n{description}" if description else title

    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")
    media_type = "VIDEO" if is_video else "IMAGE"

    async with httpx.AsyncClient(timeout=120.0) as client:
        if is_video:
            create_params = {
                "media_type": "VIDEO",
                "text": text,
                "access_token": access_token,
            }
        else:
            media_url = f"{config.APP_URL.rstrip('/')}/uploads/{Path(file_path).name}"
            create_params = {
                "media_type": "IMAGE",
                "image_url": media_url,
                "text": text,
                "access_token": access_token,
            }

        Logger.info(f"Threads create params: media_type={create_params.get('media_type')}, text_length={len(text)}")

        create_resp = await client.post(
            f"https://graph.threads.net/v1.0/{threads_id}/media",
            params=create_params,
        )
        Logger.info(f"Threads create response status={create_resp.status_code}, body={create_resp.text[:500]}")

        if not (200 <= create_resp.status_code < 300):
            if create_resp.status_code >= 500:
                Logger.warning(f"Threads create failed with 5xx, retrying as TEXT: {create_resp.text[:200]}")
                create_resp = await client.post(
                    f"https://graph.threads.net/v1.0/{threads_id}/media",
                    params={
                        "media_type": "TEXT",
                        "text": text,
                        "access_token": access_token,
                    },
                )
                Logger.info(f"Threads TEXT fallback response status={create_resp.status_code}, body={create_resp.text[:500]}")
                if 200 <= create_resp.status_code < 300:
                    media_container_id = create_resp.json().get("id")
                    if not media_container_id:
                        return {"success": False, "error": "No media container ID from Threads text fallback"}
                    publish_resp = await client.post(
                        f"https://graph.threads.net/v1.0/{threads_id}/media_publish",
                        params={"creation_id": media_container_id, "access_token": access_token},
                    )
                    if 200 <= publish_resp.status_code < 300:
                        data = publish_resp.json() if publish_resp.text else {}
                        Logger.info(f"Threads TEXT publish success: {data}")
                        return {"success": True, "platform_id": data.get("id", "")}
                    return {"success": False, "error": f"Threads TEXT publish failed ({publish_resp.status_code}): {publish_resp.text}"}
            body = create_resp.text or f"status {create_resp.status_code}"
            return {"success": False, "error": f"Threads create failed ({create_resp.status_code}): {body}"}

        media_container_id = create_resp.json().get("id")
        if not media_container_id:
            return {"success": False, "error": "No media container ID from Threads"}

        if is_video:
            upload_url_resp = await client.get(
                f"https://graph.threads.net/v1.0/{media_container_id}",
                params={
                    "fields": "upload_url",
                    "access_token": access_token,
                },
            )
            Logger.info(f"Threads upload URL response status={upload_url_resp.status_code}, body={upload_url_resp.text[:500]}")
            if upload_url_resp.status_code != 200:
                return {"success": False, "error": f"Threads upload URL failed ({upload_url_resp.status_code}): {upload_url_resp.text}"}
            upload_url = upload_url_resp.json().get("upload_url")
            if not upload_url:
                return {"success": False, "error": f"Threads upload URL missing: {upload_url_resp.text}"}
            with open(file_path, "rb") as f:
                file_upload = await client.post(upload_url, content=f.read())
            Logger.info(f"Threads file upload response status={file_upload.status_code}, body={file_upload.text[:500]}")
            if not (200 <= file_upload.status_code < 300):
                return {"success": False, "error": f"Threads file upload failed ({file_upload.status_code}): {file_upload.text}"}

            for _ in range(30):
                status_resp = await client.get(
                    f"https://graph.threads.net/v1.0/{media_container_id}",
                    params={
                        "fields": "status",
                        "access_token": access_token,
                    },
                )
                if status_resp.status_code != 200:
                    return {"success": False, "error": f"Threads status check failed ({status_resp.status_code}): {status_resp.text}"}
                status_data = status_resp.json()
                Logger.info(f"Threads status response={status_data}")
                status = status_data.get("status")
                if status in ("FINISHED", "PUBLISHED"):
                    break
                if status == "ERROR":
                    return {"success": False, "error": f"Threads media processing failed: {status_data}"}
                await asyncio.sleep(5)
            else:
                return {"success": False, "error": "Threads media processing timeout"}

        publish_resp = await client.post(
            f"https://graph.threads.net/v1.0/{threads_id}/media_publish",
            params={
                "creation_id": media_container_id,
                "access_token": access_token,
            },
        )
        Logger.info(f"Threads publish response status={publish_resp.status_code}, body={publish_resp.text[:500]}")
        if 200 <= publish_resp.status_code < 300:
            data = publish_resp.json() if publish_resp.text else {}
            return {"success": True, "platform_id": data.get("id", "")}
        body = publish_resp.text or f"status {publish_resp.status_code}"
        return {"success": False, "error": f"Threads publish failed ({publish_resp.status_code}): {body}"}
