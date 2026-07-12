import httpx
import mimetypes
from typing import Optional

from app.utils.json_db import accounts_db


def get_linkedin_account() -> Optional[dict]:
    accounts = accounts_db.read()
    for acc in accounts:
        if acc.get("platform") == "linkedin" and acc.get("connected"):
            return acc
    return None


async def delete_from_linkedin(post_id: str) -> dict:
    account = get_linkedin_account()
    if not account:
        return {"success": False, "error": "Akun LinkedIn tidak terhubung"}

    access_token = account.get("access_token")

    ugc_id = post_id
    if ":" in post_id:
        ugc_id = post_id.split(":")[-1]

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.delete(
            f"https://api.linkedin.com/v2/ugcPosts/{ugc_id}",
            headers=headers,
        )
        if resp.status_code in (200, 204):
            return {"success": True}
        if resp.status_code == 404:
            return {"success": True, "note": "Post sudah tidak ada di LinkedIn"}
        Logger.warning(f"LinkedIn delete error {resp.status_code}: {resp.text[:300]}")
        return {"success": False, "error": f"Gagal hapus dari LinkedIn ({resp.status_code})"}


async def upload_to_linkedin(file_path: str, title: str, description: str, **kwargs) -> dict:
    account = get_linkedin_account()
    if not account:
        return {"success": False, "error": "Akun LinkedIn tidak terhubung"}

    access_token = account.get("access_token")
    profile_id = account.get("profile_id")
    if not access_token or not profile_id:
        return {"success": False, "error": "Data akun LinkedIn tidak lengkap"}

    mime_type, _ = mimetypes.guess_type(file_path)
    is_video = mime_type and mime_type.startswith("video")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
    }

    async with httpx.AsyncClient() as client:
        if is_video:
            register_resp = await client.post(
                "https://api.linkedin.com/v2/assets",
                params={"action": "registerUpload"},
                headers=headers,
                json={
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-video"],
                        "owner": f"urn:li:person:{profile_id}",
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent",
                            }
                        ],
                    }
                },
            )
            if register_resp.status_code not in (200, 201):
                return {"success": False, "error": f"LinkedIn register upload failed: {register_resp.text}"}

            upload_data = register_resp.json()
            upload_url = upload_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_id = upload_data["value"]["asset"]

            with open(file_path, "rb") as f:
                file_resp = await client.put(upload_url, headers={"Authorization": f"Bearer {access_token}"}, content=f.read())
            if file_resp.status_code not in (200, 201):
                return {"success": False, "error": "LinkedIn file upload failed"}

            share_resp = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json={
                    "author": f"urn:li:person:{profile_id}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": f"{title}\n\n{description}"},
                            "shareMediaCategory": "VIDEO",
                            "media": [
                                {
                                    "status": "READY",
                                    "description": {"text": description},
                                    "media": asset_id,
                                    "title": {"text": title},
                                }
                            ],
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                },
            )
            if share_resp.status_code in (200, 201):
                return {"success": True, "platform_id": share_resp.json().get("id", "")}
            return {"success": False, "error": f"LinkedIn share failed: {share_resp.text}"}

        else:
            register_resp = await client.post(
                "https://api.linkedin.com/v2/assets",
                params={"action": "registerUpload"},
                headers=headers,
                json={
                    "registerUploadRequest": {
                        "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                        "owner": f"urn:li:person:{profile_id}",
                        "serviceRelationships": [
                            {
                                "relationshipType": "OWNER",
                                "identifier": "urn:li:userGeneratedContent",
                            }
                        ],
                    }
                },
            )
            if register_resp.status_code not in (200, 201):
                return {"success": False, "error": f"LinkedIn register upload failed: {register_resp.text}"}

            upload_data = register_resp.json()
            upload_url = upload_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
            asset_id = upload_data["value"]["asset"]

            with open(file_path, "rb") as f:
                file_resp = await client.put(upload_url, headers={"Authorization": f"Bearer {access_token}"}, content=f.read())
            if file_resp.status_code not in (200, 201):
                return {"success": False, "error": "LinkedIn file upload failed"}

            share_resp = await client.post(
                "https://api.linkedin.com/v2/ugcPosts",
                headers=headers,
                json={
                    "author": f"urn:li:person:{profile_id}",
                    "lifecycleState": "PUBLISHED",
                    "specificContent": {
                        "com.linkedin.ugc.ShareContent": {
                            "shareCommentary": {"text": f"{title}\n\n{description}"},
                            "shareMediaCategory": "IMAGE",
                            "media": [
                                {
                                    "status": "READY",
                                    "description": {"text": description},
                                    "media": asset_id,
                                    "title": {"text": title},
                                }
                            ],
                        }
                    },
                    "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
                },
            )
            if share_resp.status_code in (200, 201):
                return {"success": True, "platform_id": share_resp.json().get("id", "")}
            return {"success": False, "error": f"LinkedIn share failed: {share_resp.text}"}
