import asyncio
import uuid
from datetime import datetime
from typing import Optional

from app.utils.json_db import contents_db, uploads_db, accounts_db
from app.utils.logger import Logger
from app.services.statistics_service import STATS_FUNCTIONS, fetch_platform_stats, fetch_youtube_channel_stats
from app.services.content_fetcher import FETCH_FUNCTIONS


def get_all_contents() -> list[dict]:
    return contents_db.read()


def get_content_by_platform_id(platform: str, platform_post_id: str) -> Optional[dict]:
    for c in contents_db.read():
        if c.get("platform") == platform and c.get("platform_post_id") == platform_post_id:
            return c
    return None


def upsert_content(record: dict) -> None:
    existing = get_content_by_platform_id(record["platform"], record["platform_post_id"])
    if existing:
        contents_db.update(
            lambda x: x.get("id") == existing["id"],
            record,
        )
    else:
        contents_db.append(record)


def register_upload_content(
    platform: str,
    platform_post_id: str,
    title: str = "",
    description: str = "",
    url: str = "",
    thumbnail: str = "",
    media_type: str = "text",
    published_at: Optional[str] = None,
) -> None:
    now = datetime.now().isoformat()
    record = {
        "id": str(uuid.uuid4()),
        "platform": platform,
        "platform_post_id": platform_post_id,
        "title": title,
        "description": description,
        "url": url,
        "thumbnail": thumbnail,
        "media_type": media_type,
        "published_at": published_at or now,
        "views": 0,
        "likes": 0,
        "comments": 0,
        "last_synced_at": None,
    }
    upsert_content(record)
    Logger.info(f"Content registered: {platform}/{platform_post_id}")


def content_from_fetch_post(post: dict) -> dict:
    now = datetime.now().isoformat()
    return {
        "id": str(uuid.uuid4()),
        "platform": post["platform"],
        "platform_post_id": post["id"],
        "title": post.get("title", ""),
        "description": post.get("description", ""),
        "url": post.get("url", ""),
        "thumbnail": post.get("thumbnail", ""),
        "media_type": post.get("media_type", "text"),
        "published_at": post.get("created_at", now),
        "views": post.get("views", 0),
        "likes": post.get("likes", 0),
        "comments": post.get("comments", 0),
        "last_synced_at": now if post.get("views") is not None else None,
    }


async def import_posts_from_platform(platform: str) -> int:
    func = FETCH_FUNCTIONS.get(platform)
    if not func:
        return 0

    try:
        posts = await func()
    except Exception as e:
        Logger.error(f"Failed to fetch posts from {platform}: {str(e)}")
        return 0

    imported = 0
    for post in posts:
        existing = get_content_by_platform_id(platform, post["id"])
        if not existing:
            record = content_from_fetch_post(post)
            contents_db.append(record)
            imported += 1

    Logger.info(f"Imported {imported} new posts from {platform} (total {len(posts)} fetched)")
    return imported


async def import_all_posts(platform: Optional[str] = None) -> dict:
    result = {}
    platforms = [platform] if platform else list(FETCH_FUNCTIONS.keys())
    for p in platforms:
        count = await import_posts_from_platform(p)
        result[p] = count
    return result


async def sync_platform_stats(platform: str, platform_post_id: str) -> Optional[dict]:
    stats = await fetch_platform_stats(platform, platform_post_id)
    now = datetime.now().isoformat()
    return {
        "views": stats.get("views", 0),
        "likes": stats.get("likes", 0),
        "comments": stats.get("comments", 0),
        "last_synced_at": now,
    }


async def sync_stats_for_content(content: dict) -> None:
    platform = content["platform"]
    pid = content["platform_post_id"]
    stats = await sync_platform_stats(platform, pid)
    if stats:
        contents_db.update(
            lambda x: x.get("id") == content["id"],
            stats,
        )
        Logger.info(f"Synced {platform}/{pid}: {stats['views']} views, {stats['likes']} likes, {stats['comments']} comments")


async def sync_youtube_channel_stats() -> None:
    channel_stats = await fetch_youtube_channel_stats()
    if channel_stats.get("subscribers", 0) > 0:
        accounts_db.update(
            lambda a: a.get("platform") == "youtube" and a.get("connected"),
            {"subscribers": str(channel_stats["subscribers"])},
        )
        Logger.info(f"YouTube channel stats synced: {channel_stats['subscribers']} subscribers, {channel_stats['total_channel_views']} total views")
    else:
        Logger.warning("YouTube channel stats sync returned 0 subscribers, skipped update")


async def sync_all_stats(platform: Optional[str] = None, limit: int = 50) -> dict:
    contents = contents_db.read()
    stats_accounts = accounts_db.read()
    connected_platforms = {a["platform"] for a in stats_accounts if a.get("connected")}

    synced = 0
    errors = 0

    for content in contents:
        if platform and content["platform"] != platform:
            continue
        if content["platform"] not in connected_platforms:
            continue
        if limit and synced >= limit:
            break

        try:
            await sync_stats_for_content(content)
            synced += 1
        except Exception as e:
            Logger.error(f"Error syncing {content['platform']}/{content['platform_post_id']}: {str(e)}")
            errors += 1

    if not platform or platform == "youtube":
        await sync_youtube_channel_stats()

    Logger.info(f"Stats sync complete: {synced} synced, {errors} errors")
    return {"synced": synced, "errors": errors}


sync_in_progress = False


async def background_sync_loop(interval_seconds: int = 300):
    global sync_in_progress
    Logger.info(f"Background sync loop started (interval={interval_seconds}s)")

    while True:
        try:
            if sync_in_progress:
                Logger.info("Previous sync still running, skipping")
            else:
                sync_in_progress = True
                await sync_all_stats(limit=100)
                sync_in_progress = False
        except Exception as e:
            sync_in_progress = False
            Logger.error(f"Background sync error: {str(e)}")

        await asyncio.sleep(interval_seconds)
