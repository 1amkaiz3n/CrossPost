import httpx
from urllib.parse import urlencode
from typing import Optional

import config


def get_google_auth_url(state: str) -> str:
    params = {
        "client_id": config.YOUTUBE_CLIENT_ID,
        "redirect_uri": config.YOUTUBE_REDIRECT_URI,
        "response_type": "code",
        "scope": "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.readonly",
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


async def exchange_google_code(code: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": config.YOUTUBE_CLIENT_ID,
                "client_secret": config.YOUTUBE_CLIENT_SECRET,
                "redirect_uri": config.YOUTUBE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return None


async def get_youtube_channels(access_token: str) -> list[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={
                "part": "snippet,statistics",
                "mine": "true",
                "access_token": access_token,
            },
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            return [
                {
                    "id": ch["id"],
                    "title": ch["snippet"]["title"],
                    "thumbnail": ch["snippet"]["thumbnails"]["default"]["url"],
                    "subscribers": ch["statistics"].get("subscriberCount", "0"),
                }
                for ch in items
            ]
        return []


async def refresh_google_token(refresh_token: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": config.YOUTUBE_CLIENT_ID,
                "client_secret": config.YOUTUBE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return None
