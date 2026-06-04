import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "scenic_online.sqlite3"
DEFAULT_POSTGRES_DATABASE_URL = "postgresql://scenic:scenic@localhost:5432/scenic_online"
REQUESTED_DATABASE_BACKEND = os.environ.get("SCENIC_DATABASE_BACKEND", "").strip().lower()
DATABASE_URL = "" if REQUESTED_DATABASE_BACKEND == "sqlite" else os.environ.get("DATABASE_URL", DEFAULT_POSTGRES_DATABASE_URL)
DATABASE_BACKEND = "postgresql" if DATABASE_URL.startswith(("postgresql://", "postgres://")) else "sqlite"
TPT_JINGDIAN_SQL_PATH = Path(os.environ.get("TPT_JINGDIAN_SQL_PATH", DATA_DIR / "tpt_data_jingdian.sql"))
AMAP_WEB_SERVICE_KEY = os.environ.get("AMAP_WEB_SERVICE_KEY", "")
AMAP_JS_API_KEY = os.environ.get("AMAP_JS_API_KEY", "")
AMAP_JS_SECURITY_CODE = os.environ.get("AMAP_JS_SECURITY_CODE", "")
MAPBOX_TOKEN = os.environ.get("MAPBOX_TOKEN", "")
QWEATHER_KEY = os.environ.get("QWEATHER_KEY", "")
AMAP_WEATHER_KEY = os.environ.get("AMAP_WEATHER_KEY", "")
AMAP_WEB_SERVICE_ENDPOINT = "https://restapi.amap.com/v3"

APP_NAME = "Scenic Online"
API_PREFIX = "/api"

# Production settings
DEBUG = os.environ.get("DEBUG", "False").lower() in ("true", "1", "t")
DEFAULT_LOCAL_CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost",
    "http://127.0.0.1",
]
CORS_ORIGINS = [origin.strip() for origin in os.environ.get("CORS_ORIGINS", "").split(",") if origin.strip()] or DEFAULT_LOCAL_CORS_ORIGINS
