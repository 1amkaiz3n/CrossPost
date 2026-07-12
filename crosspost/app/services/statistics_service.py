import httpx

from app.utils.json_db import accounts_db, contents_db
from app.utils.logger import Logger
from app.oauth.google_oauth import refresh_google_token


async def fetch_youtube_stats(video_id: str) -> dict:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "youtube" and acc.get("connected"):
            account = acc
            break
    if not account:
        return {"views": 0, "likes": 0, "comments": 0}

    token_data = await refresh_google_token(account["refresh_token"])
    if not token_data:
        return {"views": 0, "likes": 0, "comments": 0}

    access_token = token_data.get("access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={
                "part": "statistics",
                "id": video_id,
                "access_token": access_token,
            },
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                stats = items[0].get("statistics", {})
                return {
                    "views": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "comments": int(stats.get("commentCount", 0)),
                }
            Logger.warning(f"YouTube stats: video {video_id} not found")
        else:
            Logger.warning(f"YouTube stats API error {resp.status_code}: {resp.text[:300]}")
    return {"views": 0, "likes": 0, "comments": 0}


async def fetch_facebook_stats(post_id: str) -> dict:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "facebook" and acc.get("connected"):
            account = acc
            break
    if not account:
        return {"views": 0, "likes": 0, "comments": 0}

    page_token = account.get("page_access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/v18.0/{post_id}",
            params={
                "fields": "likes.summary(true),comments.summary(true)",
                "access_token": page_token,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            likes = 0
            comments = 0
            if "likes" in data and "summary" in data["likes"]:
                likes = data["likes"]["summary"].get("total_count", 0)
            if "comments" in data and "summary" in data["comments"]:
                comments = data["comments"]["summary"].get("total_count", 0)
            return {"views": 0, "likes": likes, "comments": comments}
        Logger.warning(f"Facebook stats API error {resp.status_code}: {resp.text[:300]}")
    return {"views": 0, "likes": 0, "comments": 0}


async def fetch_instagram_stats(media_id: str) -> dict:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "instagram" and acc.get("connected"):
            account = acc
            break
    if not account:
        return {"views": 0, "likes": 0, "comments": 0}

    page_token = account.get("page_access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.facebook.com/v18.0/{media_id}",
            params={
                "fields": "like_count,comments_count",
                "access_token": page_token,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "views": 0,
                "likes": data.get("like_count", 0),
                "comments": data.get("comments_count", 0),
            }
        Logger.warning(f"Instagram stats API error {resp.status_code}: {resp.text[:300]}")
    return {"views": 0, "likes": 0, "comments": 0}


async def fetch_linkedin_stats(post_id: str) -> dict:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "linkedin" and acc.get("connected"):
            account = acc
            break
    if not account:
        return {"views": 0, "likes": 0, "comments": 0}

    access_token = account.get("access_token")

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Restli-Protocol-Version": "2.0.0",
        "Linkedin-Version": "202407",
    }

    share_urn = f"urn:li:share:{post_id}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.linkedin.com/v2/socialActions/{share_urn}",
            headers=headers,
        )
        if resp.status_code == 200:
            data = resp.json()
            likes_summary = data.get("likesSummary", {})
            comments_summary = data.get("commentsSummary", {})
            return {
                "views": 0,
                "likes": likes_summary.get("totalLikes", 0),
                "comments": comments_summary.get("totalComments", 0),
            }
        Logger.warning(f"LinkedIn stats API error {resp.status_code}: {resp.text[:300]}")
    return {"views": 0, "likes": 0, "comments": 0}


async def fetch_threads_stats(media_id: str) -> dict:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "threads" and acc.get("connected"):
            account = acc
            break
    if not account:
        return {"views": 0, "likes": 0, "comments": 0}

    access_token = account.get("access_token")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://graph.threads.net/v1.0/{media_id}",
            params={
                "fields": "like_count,comments_count",
                "access_token": access_token,
            },
        )
        if resp.status_code == 200:
            data = resp.json()
            return {
                "views": 0,
                "likes": data.get("like_count", 0),
                "comments": data.get("comments_count", 0),
            }
        Logger.warning(f"Threads stats API error {resp.status_code}: {resp.text[:300]}")
    return {"views": 0, "likes": 0, "comments": 0}


async def fetch_youtube_channel_stats() -> dict:
    account = None
    for acc in accounts_db.read():
        if acc.get("platform") == "youtube" and acc.get("connected"):
            account = acc
            break
    if not account:
        return {"subscribers": 0, "total_channel_views": 0, "total_videos": 0}

    token_data = await refresh_google_token(account["refresh_token"])
    if not token_data:
        return {"subscribers": 0, "total_channel_views": 0, "total_videos": 0}

    access_token = token_data.get("access_token")
    channel_id = account.get("channel_id", "")

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://www.googleapis.com/youtube/v3/channels",
            params={"part": "statistics", "id": channel_id},
            headers={"Authorization": f"Bearer {access_token}"},
        )
        if resp.status_code == 200:
            items = resp.json().get("items", [])
            if items:
                stats = items[0].get("statistics", {})
                return {
                    "subscribers": int(stats.get("subscriberCount", 0)),
                    "total_channel_views": int(stats.get("viewCount", 0)),
                    "total_videos": int(stats.get("videoCount", 0)),
                }
            Logger.warning(f"YouTube channel {channel_id} not found")
        else:
            Logger.warning(f"YouTube channel API error {resp.status_code}: {resp.text[:300]}")
    return {"subscribers": 0, "total_channel_views": 0, "total_videos": 0}


async def fetch_all_youtube_video_stats() -> list[dict]:
    import re

    contents = contents_db.read()
    valid_ids = []
    for c in contents:
        pid = c.get("platform_post_id") or ""
        if c.get("platform") == "youtube" and re.match(r"^[a-zA-Z0-9_-]{11}$", pid):
            valid_ids.append(pid)
    if not valid_ids:
        return []

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

    async def fetch_chunk(chunk_ids: list[str]) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://www.googleapis.com/youtube/v3/videos",
                params={"part": "statistics", "id": ",".join(chunk_ids)},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if resp.status_code == 200:
                items = resp.json().get("items", [])
                result = []
                for item in items:
                    stats = item.get("statistics", {})
                    result.append({
                        "platform_post_id": item["id"],
                        "views": int(stats.get("viewCount", 0)),
                        "likes": int(stats.get("likeCount", 0)),
                        "comments": int(stats.get("commentCount", 0)),
                    })
                return result
            Logger.warning(f"YouTube batch stats API error {resp.status_code}: {resp.text[:200]}")
            return []

    CHUNK_SIZE = 30
    all_results = []
    for i in range(0, len(valid_ids), CHUNK_SIZE):
        chunk = valid_ids[i:i + CHUNK_SIZE]
        results = await fetch_chunk(chunk)
        all_results.extend(results)

    return all_results


STATS_FUNCTIONS = {
    "youtube": fetch_youtube_stats,
    "facebook": fetch_facebook_stats,
    "instagram": fetch_instagram_stats,
    "linkedin": fetch_linkedin_stats,
    "threads": fetch_threads_stats,
}


async def fetch_platform_stats(platform: str, platform_post_id: str) -> dict:
    func = STATS_FUNCTIONS.get(platform)
    if not func:
        return {"views": 0, "likes": 0, "comments": 0}
    try:
        return await func(platform_post_id)
    except Exception as e:
        Logger.error(f"Failed to fetch {platform} stats for {platform_post_id}: {str(e)}")
        return {"views": 0, "likes": 0, "comments": 0}
