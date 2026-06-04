from datetime import datetime, timezone
from typing import Any


def ok(data: Any = None, message: str = "") -> dict:
    return {
        "success": True,
        "data": data if data is not None else {},
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def fail(message: str, data: Any = None) -> dict:
    return {
        "success": False,
        "data": data if data is not None else {},
        "message": message,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
