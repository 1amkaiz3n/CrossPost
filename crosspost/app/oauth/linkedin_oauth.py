import httpx
from urllib.parse import urlencode
from typing import Optional

import config


def get_linkedin_auth_url(state: str) -> str:
    params = {
        "client_id": config.LINKEDIN_CLIENT_ID,
        "redirect_uri": config.LINKEDIN_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email w_member_social",
        "state": state,
    }
    return f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}"


async def exchange_linkedin_code(code: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "code": code,
                "client_id": config.LINKEDIN_CLIENT_ID,
                "client_secret": config.LINKEDIN_CLIENT_SECRET,
                "redirect_uri": config.LINKEDIN_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        if resp.status_code == 200:
            return resp.json()
        return None


async def get_linkedin_profile(access_token: str) -> Optional[dict]:
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "sub": data.get("sub", ""),
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "picture": data.get("picture", ""),
            }
        return None
