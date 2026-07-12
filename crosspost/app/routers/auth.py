import uuid
import asyncio
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, JSONResponse

from app.oauth.google_oauth import get_google_auth_url, exchange_google_code, get_youtube_channels
from app.oauth.meta_oauth import get_meta_auth_url, exchange_meta_code, get_facebook_pages, get_instagram_accounts
from app.oauth.linkedin_oauth import get_linkedin_auth_url, exchange_linkedin_code, get_linkedin_profile
from app.oauth.threads_oauth import get_threads_auth_url, exchange_threads_code, exchange_to_long_lived_token, get_threads_user_profile
from app.utils.json_db import accounts_db
from app.utils.logger import Logger
from app.services.sync_service import import_posts_from_platform

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/youtube")
async def auth_youtube(request: Request):
    state = str(uuid.uuid4())
    request.app.state.oauth_states[state] = "youtube"
    url = get_google_auth_url(state)
    return RedirectResponse(url)


@router.get("/youtube/callback")
async def youtube_callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        Logger.error(f"YouTube OAuth error: {error}")
        return RedirectResponse("/accounts?error=youtube_auth_failed")

    expected_state = request.app.state.oauth_states.pop(state, None)
    if expected_state != "youtube":
        return RedirectResponse("/accounts?error=invalid_state")

    Logger.info(f"Menukar code Google (panjang: {len(code) if code else 0})")
    token_data = await exchange_google_code(code)
    if not token_data:
        Logger.error("Gagal menukar code Google dengan token")
        return RedirectResponse("/accounts?error=token_exchange_failed")

    Logger.info(f"Token Google berhasil didapat: access_token={'ada' if token_data.get('access_token') else 'tidak ada'}, refresh_token={'ada' if token_data.get('refresh_token') else 'tidak ada'}")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    channels = await get_youtube_channels(access_token)
    if not channels:
        return RedirectResponse("/accounts?error=no_channel")

    channel = channels[0]

    accounts_db.append({
        "platform": "youtube",
        "connected": True,
        "channel_id": channel["id"],
        "channel_name": channel["title"],
        "thumbnail": channel.get("thumbnail", ""),
        "subscribers": channel.get("subscribers", "0"),
        "access_token": access_token,
        "refresh_token": refresh_token,
        "connected_at": __import__("datetime").datetime.now().isoformat(),
    })

    Logger.success("Akun YouTube berhasil dihubungkan")
    asyncio.create_task(import_posts_from_platform("youtube"))
    return RedirectResponse("/accounts?success=youtube_connected")


@router.get("/meta")
async def auth_meta(request: Request):
    state = str(uuid.uuid4())
    request.app.state.oauth_states[state] = "meta"
    url = get_meta_auth_url(state)
    return RedirectResponse(url)


@router.get("/meta/callback")
async def meta_callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        Logger.error(f"Meta OAuth error: {error}")
        return RedirectResponse("/accounts?error=meta_auth_failed")

    expected_state = request.app.state.oauth_states.pop(state, None)
    if expected_state != "meta":
        return RedirectResponse("/accounts?error=invalid_state")

    token_data = await exchange_meta_code(code)
    if not token_data:
        return RedirectResponse("/accounts?error=token_exchange_failed")

    access_token = token_data.get("access_token")

    pages = await get_facebook_pages(access_token)
    if not pages:
        return RedirectResponse("/accounts?error=no_pages")

    page = pages[0]
    page_token = page["access_token"]
    page_id = page["id"]

    accounts_db.append({
        "platform": "facebook",
        "connected": True,
        "page_id": page_id,
        "page_name": page["name"],
        "page_access_token": page_token,
        "page_picture": page.get("picture", ""),
        "connected_at": __import__("datetime").datetime.now().isoformat(),
    })

    ig_accounts = await get_instagram_accounts(page_id, page_token)
    if ig_accounts:
        ig = ig_accounts[0]
        accounts_db.append({
            "platform": "instagram",
            "connected": True,
            "instagram_account_id": ig["id"],
            "instagram_username": ig.get("username", ""),
            "instagram_name": ig.get("name", ""),
            "instagram_picture": ig.get("profile_picture", ""),
            "page_access_token": page_token,
            "connected_at": __import__("datetime").datetime.now().isoformat(),
        })
        Logger.success("Akun Instagram berhasil dihubungkan")
        asyncio.create_task(import_posts_from_platform("instagram"))

    Logger.success("Akun Facebook berhasil dihubungkan")
    asyncio.create_task(import_posts_from_platform("facebook"))
    return RedirectResponse("/accounts?success=meta_connected")


@router.get("/linkedin")
async def auth_linkedin(request: Request):
    state = str(uuid.uuid4())
    request.app.state.oauth_states[state] = "linkedin"
    url = get_linkedin_auth_url(state)
    return RedirectResponse(url)


@router.get("/linkedin/callback")
async def linkedin_callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        Logger.error(f"LinkedIn OAuth error: {error}")
        return RedirectResponse("/accounts?error=linkedin_auth_failed")

    expected_state = request.app.state.oauth_states.pop(state, None)
    if expected_state != "linkedin":
        return RedirectResponse("/accounts?error=invalid_state")

    token_data = await exchange_linkedin_code(code)
    if not token_data:
        return RedirectResponse("/accounts?error=token_exchange_failed")

    access_token = token_data.get("access_token")

    profile = await get_linkedin_profile(access_token)
    if not profile:
        return RedirectResponse("/accounts?error=no_profile")

    accounts_db.append({
        "platform": "linkedin",
        "connected": True,
        "profile_id": profile["sub"],
        "profile_name": profile.get("name", ""),
        "profile_email": profile.get("email", ""),
        "profile_picture": profile.get("picture", ""),
        "access_token": access_token,
        "connected_at": __import__("datetime").datetime.now().isoformat(),
    })

    Logger.success("Akun LinkedIn berhasil dihubungkan")
    asyncio.create_task(import_posts_from_platform("linkedin"))
    return RedirectResponse("/accounts?success=linkedin_connected")


@router.get("/threads")
async def auth_threads(request: Request):
    state = str(uuid.uuid4())
    request.app.state.oauth_states[state] = "threads"
    url = get_threads_auth_url(state)
    return RedirectResponse(url)


@router.get("/threads/callback")
async def threads_callback(request: Request, code: str = None, state: str = None, error: str = None):
    if error:
        Logger.error(f"Threads OAuth error: {error}")
        return RedirectResponse("/accounts?error=threads_auth_failed")

    expected_state = request.app.state.oauth_states.pop(state, None)
    if expected_state != "threads":
        return RedirectResponse("/accounts?error=invalid_state")

    token_data = await exchange_threads_code(code)
    if not token_data:
        return RedirectResponse("/accounts?error=token_exchange_failed")

    short_lived_token = token_data.get("access_token")
    user_id = token_data.get("user_id", "")

    long_lived_token = await exchange_to_long_lived_token(short_lived_token)
    access_token = long_lived_token or short_lived_token

    profile = await get_threads_user_profile(access_token)
    if not profile:
        return RedirectResponse("/accounts?error=no_profile")

    accounts_db.append({
        "platform": "threads",
        "connected": True,
        "threads_user_id": profile["id"],
        "threads_username": profile.get("username", ""),
        "threads_name": profile.get("name", ""),
        "threads_picture": profile.get("picture", ""),
        "access_token": access_token,
        "connected_at": __import__("datetime").datetime.now().isoformat(),
    })

    Logger.success("Akun Threads berhasil dihubungkan")
    asyncio.create_task(import_posts_from_platform("threads"))
    return RedirectResponse("/accounts?success=threads_connected")


@router.post("/disconnect/{platform}")
async def disconnect_account(platform: str):
    removed = accounts_db.delete(lambda x: x.get("platform") == platform)
    Logger.info(f"Akun {platform} diputuskan")
    return JSONResponse({"success": True, "message": f"Akun {platform} berhasil diputuskan"})
