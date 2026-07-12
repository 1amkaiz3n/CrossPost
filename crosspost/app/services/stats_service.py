from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from app.utils.json_db import contents_db, uploads_db, accounts_db


PLATFORM_LABELS = {
    "youtube": "YouTube",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "linkedin": "LinkedIn",
    "threads": "Threads",
}


def get_aggregate_stats() -> dict:
    contents = contents_db.read()
    total_views = 0
    total_likes = 0
    total_comments = 0
    total_subscribers = 0
    total_followers = 0
    platform_posts = defaultdict(int)

    for c in contents:
        total_views += c.get("views", 0) or 0
        total_likes += c.get("likes", 0) or 0
        total_comments += c.get("comments", 0) or 0
        platform_posts[c["platform"]] += 1

    connected_accounts = [a for a in accounts_db.read() if a.get("connected")]
    for acc in connected_accounts:
        subs = acc.get("subscribers", 0)
        if subs:
            total_subscribers += int(subs)
        followers = acc.get("followers", 0)
        if followers:
            total_followers += int(followers)

    total_engagement = total_likes + total_comments
    total_posts = len(contents)

    uploads = uploads_db.read()
    total_uploads = len(uploads)
    successful_uploads = sum(1 for u in uploads if u.get("status") == "completed")
    failed_uploads = sum(1 for u in uploads if u.get("status") == "partial")

    total_accounts = len(connected_accounts)

    return {
        "total_posts": total_posts,
        "total_views": total_views,
        "total_likes": total_likes,
        "total_comments": total_comments,
        "total_subscribers": total_subscribers,
        "total_followers": total_followers,
        "total_engagement": total_engagement,
        "total_uploads": total_uploads,
        "successful_uploads": successful_uploads,
        "failed_uploads": failed_uploads,
        "total_accounts": total_accounts,
        "platform_posts": dict(platform_posts),
        "platform_accounts": {a["platform"]: 1 for a in connected_accounts},
    }


def get_platform_breakdown() -> list[dict]:
    contents = contents_db.read()
    accounts = accounts_db.read()

    platform_data = defaultdict(lambda: {
        "posts": 0,
        "views": 0,
        "likes": 0,
        "comments": 0,
        "engagement": 0,
        "total_engagement": 0,
        "subscribers": 0,
        "followers": 0,
    })

    for acc in accounts:
        p = acc["platform"]
        if acc.get("connected"):
            subs = acc.get("subscribers", 0)
            if subs:
                platform_data[p]["subscribers"] = int(subs)
            followers = acc.get("followers", 0)
            if followers:
                platform_data[p]["followers"] = int(followers)

    for c in contents:
        p = c["platform"]
        platform_data[p]["posts"] += 1
        platform_data[p]["views"] += c.get("views", 0) or 0
        platform_data[p]["likes"] += c.get("likes", 0) or 0
        platform_data[p]["comments"] += c.get("comments", 0) or 0

    result = []
    for platform, data in platform_data.items():
        data["total_engagement"] = data["likes"] + data["comments"]
        data["platform"] = platform
        data["label"] = PLATFORM_LABELS.get(platform, platform.title())
        result.append(data)

    result.sort(key=lambda x: x["posts"], reverse=True)
    return result


def get_time_series(days: int = 30) -> dict:
    contents = contents_db.read()
    now = datetime.now()
    start_date = now - timedelta(days=days)

    daily = defaultdict(lambda: {"views": 0, "likes": 0, "comments": 0, "posts": 0})
    platform_daily = defaultdict(lambda: defaultdict(lambda: {"views": 0, "likes": 0, "comments": 0}))

    for c in contents:
        published = c.get("published_at")
        if not published:
            continue
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00")).replace(tzinfo=None)
        except (ValueError, TypeError):
            continue
        if dt < start_date:
            continue

        day_key = dt.strftime("%Y-%m-%d")
        daily[day_key]["views"] += c.get("views", 0) or 0
        daily[day_key]["likes"] += c.get("likes", 0) or 0
        daily[day_key]["comments"] += c.get("comments", 0) or 0
        daily[day_key]["posts"] += 1

        platform_daily[c["platform"]][day_key]["views"] += c.get("views", 0) or 0
        platform_daily[c["platform"]][day_key]["likes"] += c.get("likes", 0) or 0
        platform_daily[c["platform"]][day_key]["comments"] += c.get("comments", 0) or 0

    date_range = []
    cursor = start_date
    while cursor <= now:
        date_range.append(cursor.strftime("%Y-%m-%d"))
        cursor += timedelta(days=1)

    series = []
    for day in date_range:
        d = daily.get(day, {"views": 0, "likes": 0, "comments": 0, "posts": 0})
        d["date"] = day
        series.append(d)

    platform_series = {}
    for platform in PLATFORM_LABELS:
        ps = []
        for day in date_range:
            d = platform_daily[platform].get(day, {"views": 0, "likes": 0, "comments": 0})
            d["date"] = day
            ps.append(d)
        platform_series[platform] = ps

    return {
        "days": days,
        "date_range": date_range,
        "aggregate": series,
        "per_platform": platform_series,
    }


def get_best_time_to_post() -> dict:
    contents = contents_db.read()
    hour_stats = defaultdict(lambda: {
        "posts": 0, "views": 0, "likes": 0, "comments": 0, "engagement": 0
    })
    day_stats = defaultdict(lambda: {
        "posts": 0, "views": 0, "likes": 0, "comments": 0, "engagement": 0
    })
    hour_day_stats = defaultdict(lambda: {
        "posts": 0, "views": 0, "likes": 0, "comments": 0, "engagement": 0
    })

    for c in contents:
        published = c.get("published_at")
        if not published:
            continue
        try:
            dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        hour = dt.hour
        day_name = dt.strftime("%A")
        hour_day_key = f"{day_name}-{hour}"

        views = c.get("views", 0) or 0
        likes = c.get("likes", 0) or 0
        comments = c.get("comments", 0) or 0
        engagement = likes + comments

        hour_stats[hour]["posts"] += 1
        hour_stats[hour]["views"] += views
        hour_stats[hour]["likes"] += likes
        hour_stats[hour]["comments"] += comments
        hour_stats[hour]["engagement"] += engagement

        day_stats[day_name]["posts"] += 1
        day_stats[day_name]["views"] += views
        day_stats[day_name]["likes"] += likes
        day_stats[day_name]["comments"] += comments
        day_stats[day_name]["engagement"] += engagement

        hour_day_stats[hour_day_key]["posts"] += 1
        hour_day_stats[hour_day_key]["views"] += views
        hour_day_stats[hour_day_key]["likes"] += likes
        hour_day_stats[hour_day_key]["comments"] += comments
        hour_day_stats[hour_day_key]["engagement"] += engagement

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    days_label = {
        "Monday": "Senin", "Tuesday": "Selasa", "Wednesday": "Rabu",
        "Thursday": "Kamis", "Friday": "Jumat", "Saturday": "Sabtu", "Sunday": "Minggu",
    }

    def avg_engagement(stats: dict) -> float:
        if stats["posts"] == 0:
            return 0
        return stats["engagement"] / stats["posts"]

    best_hour = max(hour_stats.keys(), key=lambda h: avg_engagement(hour_stats[h]))
    best_day = max(day_stats.keys(), key=lambda d: avg_engagement(day_stats[d]))

    hour_ranking = sorted(
        [{"hour": h, "avg_engagement": round(avg_engagement(hour_stats[h]), 1), "posts": hour_stats[h]["posts"]}
         for h in range(24) if hour_stats[h]["posts"] > 0],
        key=lambda x: x["avg_engagement"], reverse=True,
    )
    day_ranking = sorted(
        [{"day": d, "day_label": days_label.get(d, d), "avg_engagement": round(avg_engagement(day_stats[d]), 1), "posts": day_stats[d]["posts"]}
         for d in days_order if day_stats[d]["posts"] > 0],
        key=lambda x: x["avg_engagement"], reverse=True,
    )

    heatmap = []
    for d in days_order:
        for h in range(24):
            key = f"{d}-{h}"
            s = hour_day_stats[key]
            heatmap.append({
                "day": d,
                "day_label": days_label.get(d, d),
                "hour": h,
                "posts": s["posts"],
                "engagement": s["engagement"],
                "avg_engagement": round(avg_engagement(s), 1) if s["posts"] > 0 else 0,
            })

    return {
        "best_hour": {
            "hour": best_hour,
            "label": f"{best_hour:02d}:00",
            "avg_engagement": round(avg_engagement(hour_stats[best_hour]), 1),
            "total_engagement": hour_stats[best_hour]["engagement"],
        },
        "best_day": {
            "day": best_day,
            "label": days_label.get(best_day, best_day),
            "avg_engagement": round(avg_engagement(day_stats[best_day]), 1),
            "total_engagement": day_stats[best_day]["engagement"],
        },
        "hour_ranking": hour_ranking[:5],
        "day_ranking": day_ranking,
        "heatmap": heatmap,
    }
