import os
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

load_dotenv()
load_dotenv(BASE_DIR.parent / ".env")
DATABASE_DIR = BASE_DIR / "database"
UPLOAD_DIR = BASE_DIR / "uploads"

DATABASE_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

APP_URL = os.getenv("APP_URL", "http://localhost:8000")

YOUTUBE_CLIENT_ID = os.getenv("YOUTUBE_CLIENT_ID", "")
YOUTUBE_CLIENT_SECRET = os.getenv("YOUTUBE_CLIENT_SECRET", "")
YOUTUBE_REDIRECT_URI = os.getenv("YOUTUBE_REDIRECT_URI", f"{APP_URL}/auth/youtube/callback")

META_APP_ID = os.getenv("META_APP_ID", "")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
META_REDIRECT_URI = os.getenv("META_REDIRECT_URI", f"{APP_URL}/auth/meta/callback")

LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
LINKEDIN_ACCESS_TOKEN = os.getenv("LINKEDIN_ACCESS_TOKEN", "")
LINKEDIN_REDIRECT_URI = os.getenv("LINKEDIN_REDIRECT_URI", f"{APP_URL}/auth/linkedin/callback")

THREADS_CLIENT_ID = os.getenv("THREADS_CLIENT_ID") or os.getenv("THREADS_APP_ID", "")
THREADS_CLIENT_SECRET = os.getenv("THREADS_CLIENT_SECRET") or os.getenv("THREADS_APP_SECRET", "")
THREADS_ACCESS_TOKEN = os.getenv("THREADS_ACCESS_TOKEN", "")
THREADS_REDIRECT_URI = os.getenv("THREADS_REDIRECT_URI", f"{APP_URL}/auth/threads/callback")

SECRET_KEY = os.getenv("SECRET_KEY", "crosspost-secret-key-change-in-production")
