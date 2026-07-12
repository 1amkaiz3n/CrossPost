import httpx
from urllib.parse import urlencode
from typing import Optional

import config


CLIENT_ID = config.THREADS_CLIENT_ID 
CLIENT_SECRET = config.THREADS_CLIENT_SECRET 


def get_threads_auth_url(state: str) -> str:
    params = {
        "client_id": CLIENT_ID,
        "redirect_uri": config.THREADS_REDIRECT_URI,
        "response_type": "code",
        "scope": "threads_basic,threads_content_publish,threads_manage_replies,threads_read_replies",
        "state": state,
    }
    return f"https://www.threads.net/oauth/authorize?{urlencode(params)}"


async def exchange_threads_code(code: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://graph.threads.net/oauth/access_token",
            data={
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "redirect_uri": config.THREADS_REDIRECT_URI,
                "code": code,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return None


async def exchange_to_long_lived_token(short_lived_token: str) -> Optional[str]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.threads.net/access_token",
            params={
                "grant_type": "th_exchange_token",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "access_token": short_lived_token,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            return data.get("access_token")
        return None


async def get_threads_user_profile(access_token: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://graph.threads.net/v1.0/me",
            params={
                "fields": "id,username,name",
                "access_token": access_token,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "id": data.get("id", ""),
                "username": data.get("username", ""),
                "name": data.get("name", ""),
                "picture": "",
            }
        return None
