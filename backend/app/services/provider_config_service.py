import json
import os

from app.core.database import get_db, row_to_dict


def mask_key(value: str = ""):
    value = value or ""
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def get_provider_config(provider: str):
    with get_db() as db:
        row = db.execute("SELECT * FROM api_configs WHERE provider=?", (provider,)).fetchone()
    item = row_to_dict(row) if row else {}
    settings = item.get("settings_json") or {}
    if isinstance(settings, str):
        try:
            settings = json.loads(settings)
        except json.JSONDecodeError:
            settings = {}
    return item | {"settings": settings}


def get_secret(provider: str, env_name: str = ""):
    env_value = os.environ.get(env_name or "", "")
    if env_value:
        return env_value
    config = get_provider_config(provider)
    if config.get("enabled") and config.get("api_key_secret"):
        return config.get("api_key_secret")
    masked = config.get("api_key_masked") or ""
    if config.get("enabled") and masked and "*" not in masked:
        return masked
    return ""


def log_api(provider: str, endpoint: str, status_code: int, latency_ms: int, result: str):
    with get_db() as db:
        db.execute(
            "INSERT INTO api_logs (provider,endpoint,status_code,latency_ms,result) VALUES (?,?,?,?,?)",
            (provider, endpoint, status_code, latency_ms, result[:200]),
        )
