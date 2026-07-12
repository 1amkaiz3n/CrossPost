import httpx
from urllib.parse import urlencode
from typing import Optional

import config


def get_meta_auth_url(state: str) -> str:
    params = {
        "client_id": config.META_APP_ID,
        "redirect_uri": config.META_REDIRECT_URI,
        "response_type": "code",
        "scope": "pages_show_list,pages_read_engagement,pages_manage_posts,instagram_basic,instagram_content_publish,instagram_manage_contents,instagram_manage_insights,public_profile,business_management",
        "state": state,
    }
    return f"https://www.facebook.com/v18.0/dialog/oauth?{urlencode(params)}"


async def exchange_meta_code(code: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "client_id": config.META_APP_ID,
                "client_secret": config.META_APP_SECRET,
                "redirect_uri": config.META_REDIRECT_URI,
                "code": code,
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return None


async def get_facebook_pages(access_token: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.facebook.com/v18.0/me/accounts",
            params={"access_token": access_token},
        )
        if resp.status_code == 200:
            data = resp.json().get("data", [])
            return [
                {
                    "id": page["id"],
                    "name": page["name"],
                    "access_token": page["access_token"],
                    "category": page.get("category", ""),
                    "picture": f"https://graph.facebook.com/v18.0/{page['id']}/picture",
                }
                for page in data
            ]
        return []


async def get_instagram_accounts(page_id: str, page_access_token: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/v18.0/{page_id}",
            params={
                "fields": "instagram_business_account{id,username,name,profile_picture_url}",
                "access_token": page_access_token,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            ig = data.get("instagram_business_account")
            if ig:
                return [
                    {
                        "id": ig["id"],
                        "username": ig.get("username", ""),
                        "name": ig.get("name", ""),
                        "profile_picture": ig.get("profile_picture_url", ""),
                    }
                ]
        return []


async def get_long_lived_token(access_token: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.facebook.com/v18.0/oauth/access_token",
            params={
                "grant_type": "fb_exchange_token",
                "client_id": config.META_APP_ID,
                "client_secret": config.META_APP_SECRET,
                "fb_exchange_token": access_token,
            },
        )
        if resp.status_code == 200:
            return resp.json().get("access_token")
        return None
