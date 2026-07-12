from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.services.stats_service import (
    get_aggregate_stats,
    get_platform_breakdown,
    get_time_series,
    get_best_time_to_post,
)
from app.services.statistics_service import (
    fetch_youtube_channel_stats,
    fetch_all_youtube_video_stats,
)

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/summary")
async def summary():
    data = get_aggregate_stats()
    return JSONResponse(data)


@router.get("/platforms")
async def platforms():
    data = get_platform_breakdown()
    return JSONResponse(data)


@router.get("/time-series")
async def time_series(days: int = Query(30, ge=1, le=365)):
    data = get_time_series(days)
    return JSONResponse(data)


@router.get("/best-time")
async def best_time():
    data = get_best_time_to_post()
    return JSONResponse(data)


@router.get("/youtube/realtime")
async def youtube_realtime():
    channel_stats = await fetch_youtube_channel_stats()
    video_stats = await fetch_all_youtube_video_stats()

    total_views = channel_stats.get("total_channel_views", 0)
    total_likes = 0
    total_comments = 0

    for v in video_stats:
        total_likes += v.get("likes", 0)
        total_comments += v.get("comments", 0)

    return JSONResponse({
        "channel": channel_stats,
        "videos": video_stats,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_posts": len(video_stats),
    })
