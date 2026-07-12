import httpx
from typing import Optional

import config
from app.utils.json_db import accounts_db, contents_db
from app.utils.logger import Logger
from app.oauth.google_oauth import refresh_google_token
from app.oauth.threads_oauth import exchange_to_long_lived_token


async def fetch_youtube_posts() -> list[dict]:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "youtube" and acc.get("connected"):
            account = acc
            break
    if not account:
        return []

    token_data = await refresh_google_token(account["refresh_token"])
    if not token_data:
        return []

    access_token = token_data.get("access_token")
    channel_id = account.get("channel_id", "")
    upload_playlist_id = "UU" + channel_id.removeprefix("UC")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/playlistItems",
            params={
                "part": "snippet,contentDetails",
                "playlistId": upload_playlist_id,
                "maxResults": 50,
                "access_token": access_token,
            },
        )
        if resp.status_code != 200:
            Logger.warning(f"YouTube API error {resp.status_code}: {resp.text[:500]}")
            return []

        items = resp.json().get("items", [])
        Logger.info(f"YouTube API returned {len(items)} items")
        posts = []
        for item in items:
            snippet = item.get("snippet", {})
            resource_id = item.get("contentDetails", {}).get("videoId", "")
            posts.append({
                "id": resource_id or item.get("id", ""),
                "platform": "youtube",
                "title": snippet.get("title", ""),
                "description": snippet.get("description", ""),
                "url": f"https://youtube.com/watch?v={resource_id}",
                "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", snippet.get("thumbnails", {}).get("default", {}).get("url", "")),
                "created_at": snippet.get("publishedAt", ""),
                "media_type": "video",
            })
        return posts


async def fetch_facebook_posts() -> list[dict]:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "facebook" and acc.get("connected"):
            account = acc
            break
    if not account:
        return []

    page_id = account.get("page_id")
    page_token = account.get("page_access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/v18.0/{page_id}/posts",
            params={
                "fields": "id,message,created_time,full_picture,permalink_url,attachments{media_type,media,url}",
                "access_token": page_token,
                "limit": 50,
            },
        )
        if resp.status_code != 200:
            return []

        items = resp.json().get("data", [])
        posts = []
        for item in items:
            attachments = item.get("attachments", {}).get("data", [])
            media_type = "text"
            thumbnail = item.get("full_picture", "")
            for att in attachments:
                if att.get("media_type") == "video":
                    media_type = "video"
                elif att.get("media_type") in ("photo", "animated_share"):
                    media_type = "image"
                if not thumbnail:
                    media = att.get("media", {})
                    thumbnail = media.get("image", {}).get("src", "")

            message = item.get("message", "")
            posts.append({
                "id": item.get("id", ""),
                "platform": "facebook",
                "title": message.split("\n")[0][:100] if message else "",
                "description": message,
                "url": item.get("permalink_url", ""),
                "thumbnail": thumbnail,
                "created_at": item.get("created_time", ""),
                "media_type": media_type,
            })
        return posts


async def fetch_instagram_posts() -> list[dict]:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "instagram" and acc.get("connected"):
            account = acc
            break
    if not account:
        return []

    ig_id = account.get("instagram_account_id")
    page_token = account.get("page_access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/v18.0/{ig_id}/media",
            params={
                "fields": "id,caption,media_type,media_url,permalink,timestamp,thumbnail_url",
                "access_token": page_token,
                "limit": 50,
            },
        )
        if resp.status_code != 200:
            return []

        items = resp.json().get("data", [])
        posts = []
        for item in items:
            mt = item.get("media_type", "")
            media_type = "image"
            if mt == "VIDEO":
                media_type = "video"
            elif mt == "CAROUSEL":
                media_type = "carousel"

            caption = item.get("caption", "")
            posts.append({
                "id": item.get("id", ""),
                "platform": "instagram",
                "title": caption.split("\n")[0][:100] if caption else "",
                "description": caption,
                "url": item.get("permalink", ""),
                "thumbnail": item.get("thumbnail_url", item.get("media_url", "")),
                "created_at": item.get("timestamp", ""),
                "media_type": media_type,
            })
        return posts


async def fetch_linkedin_posts() -> list[dict]:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "linkedin" and acc.get("connected"):
            account = acc
            break
    if not account:
        Logger.warning("LinkedIn content fetch skipped: akun LinkedIn belum terhubung")
        return []

    access_token = account.get("access_token")
    profile_id = account.get("profile_id")
    if not access_token or not profile_id:
        Logger.warning("LinkedIn content fetch skipped: access token atau profile ID kosong")
        return []

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": "202407",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.linkedin.com/rest/posts?author=urn%3Ali%3Aperson%3A{profile_id}&q=author&count=50&sortBy=CREATED",

            headers=headers,
        )

        if resp.status_code != 200:
            Logger.warning(f"LinkedIn Posts API error {resp.status_code}: {resp.text[:500]}")
            return []

        items = resp.json().get("elements", [])
        Logger.info(f"LinkedIn Posts API returned {len(items)} items")

        posts = []
        for item in items:
            text = ""
            media_type = "text"
            thumbnail = ""
            created = item.get("createdAt", "") or item.get("firstPublishedAt", "")

            if "commentary" in item:
                commentary = item.get("commentary", "")
                text = commentary if isinstance(commentary, str) else commentary.get("text", "")

                for att in item.get("content", {}).get("media", []):
                    media_type = "image"
                    thumbnail = att.get("originalUrl", "") or (att.get("thumbnails", [{}])[0].get("url", "") if att.get("thumbnails") else "")

            pid = item.get("id", "")
            if ":" in pid:
                pid = pid.split(":")[-1]

            commentary_text = text
            posts.append({
                "id": pid,
                "platform": "linkedin",
                "title": commentary_text.split("\n")[0][:100] if commentary_text else "",
                "description": commentary_text,
                "url": f"https://linkedin.com/feed/update/{item.get('id', pid)}",
                "thumbnail": thumbnail,
                "created_at": str(created) if created else "",
                "media_type": media_type,
            })
        return posts


async def fetch_threads_posts() -> list[dict]:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "threads" and acc.get("connected"):
            account = acc
            break
    if not account:
        Logger.warning("Threads content fetch skipped: akun Threads belum terhubung")
        return []

    threads_id = account.get("threads_user_id")
    if not threads_id:
        Logger.warning("Threads content fetch skipped: Threads user ID kosong")
        return []

    access_token = account.get("access_token") or config.THREADS_ACCESS_TOKEN
    if not access_token:
        Logger.warning("Threads content fetch skipped: access token kosong")
        return []

    async with httpx.AsyncClient() as client:
        check = await client.get(
            "https://graph.threads.net/v1.0/me",
            params={"fields": "id", "access_token": access_token},
        )
        if check.status_code != 200:
            long_lived = await exchange_to_long_lived_token(access_token)
            if long_lived:
                access_token = long_lived
                accounts_db.update(
                    lambda x: x.get("platform") == "threads",
                    {"access_token": long_lived},
                )
            else:
                fallback = config.THREADS_ACCESS_TOKEN
                if fallback and fallback != access_token:
                    check2 = await client.get(
                        "https://graph.threads.net/v1.0/me",
                        params={"fields": "id", "access_token": fallback},
                    )
                    if check2.status_code == 200:
                        access_token = fallback
                        accounts_db.update(
                            lambda x: x.get("platform") == "threads",
                            {"access_token": fallback},
                        )
                    else:
                        Logger.warning("Threads token tidak valid dan gagal refresh. Silahkan hubungkan ulang akun Threads.")
                        return []
                else:
                    Logger.warning("Threads token tidak valid dan tidak ada fallback. Silahkan hubungkan ulang akun Threads.")
                    return []

        resp = await client.get(
            f"https://graph.threads.net/v1.0/{threads_id}/threads",
            params={
                "fields": "id,text,media_type,media_url,permalink,timestamp,attachment_url",
                "access_token": access_token,
                "limit": 50,
            },
        )
        if resp.status_code != 200:
            Logger.warning(f"Threads API error {resp.status_code}: {resp.text[:500]}")
            return []

        items = resp.json().get("data", [])
        Logger.info(f"Threads API returned {len(items)} items")
        posts = []
        for item in items:
            mt = item.get("media_type", "TEXT")
            media_type = "text"
            if mt in ("IMAGE", "CAROUSEL"):
                media_type = "image"
            elif mt == "VIDEO":
                media_type = "video"

            text = item.get("text", "")
            posts.append({
                "id": item.get("id", ""),
                "platform": "threads",
                "title": text.split("\n")[0][:100] if text else "",
                "description": text,
                "url": item.get("permalink", ""),
                "thumbnail": item.get("media_url", ""),
                "created_at": item.get("timestamp", ""),
                "media_type": media_type,
            })
        return posts


FETCH_FUNCTIONS = {
    "youtube": fetch_youtube_posts,
    "facebook": fetch_facebook_posts,
    "instagram": fetch_instagram_posts,
    "linkedin": fetch_linkedin_posts,
    "threads": fetch_threads_posts,
}


async def _fetch_all_posts(platform: str = None) -> list[dict]:
    all_posts = []
    platforms = [platform] if platform else list(FETCH_FUNCTIONS.keys())

    for p in platforms:
        func = FETCH_FUNCTIONS.get(p)
        if func:
            try:
                posts = await func()
                Logger.info(f"Fetched {len(posts)} posts from {p}")
                all_posts.extend(posts)
            except Exception as e:
                Logger.error(f"Failed to fetch posts from {p}: {str(e)}")

    all_posts.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return all_posts
