import json
import subprocess
import sys
import threading
import time
from datetime import datetime

from app.core.database import get_db, row_to_dict
from app.services.scenic_external_enrichment_service import public_sources_blocked_seconds
from app.services.tpt_profile_enrichment_service import enrich_tpt_media_batch, tpt_enrichment_stats


JOB_NAME = "tpt_media_full"
_lock = threading.Lock()
_process: subprocess.Popen | None = None
_stop_requested = False


def start_tpt_media_job(
    batch_size: int = 3,
    max_total: int = 3978,
    province: str = "",
    a_level_only: bool = True,
    only_missing: bool = True,
    sleep_seconds: float = 2.0,
    include_public_sources: bool = True,
    use_amap: bool = False,
    include_osm: bool = False,
) -> dict:
    global _stop_requested
    with _lock:
        if _is_process_running():
            return status_tpt_media_job() | {"alreadyRunning": True}
        _stop_requested = False
        current_stats = tpt_enrichment_stats()
        source_total = int(current_stats.get("a_level_total") or current_stats.get("total") or 3978)
        payload = {
            "batchSize": max(1, min(int(batch_size or 3), 50)),
            "maxTotal": max(1, min(int(max_total or source_total), source_total)),
            "province": province,
            "aLevelOnly": a_level_only,
            "onlyMissing": only_missing,
            "sleepSeconds": max(0.5, min(float(sleep_seconds), 5)),
            "includePublicSources": include_public_sources,
            "useAmap": use_amap,
            "includeOsm": include_osm,
            "startedAt": _now(),
            "read": 0,
            "searched": 0,
            "withImages": 0,
            "withProfiles": 0,
            "notFound": 0,
            "rateLimited": 0,
            "sourceUnavailable": 0,
            "failures": [],
            "providerFailures": [],
            "lastBatch": {},
            "statsSnapshot": current_stats,
        }
        _write_task("running", payload)
        _start_worker_process(payload)
    return status_tpt_media_job()


def stop_tpt_media_job() -> dict:
    global _stop_requested
    _stop_requested = True
    status = status_tpt_media_job()
    if status.get("status") == "running":
        _write_task("stopping", status.get("payload") or {})
    return status_tpt_media_job()


def status_tpt_media_job() -> dict:
    with get_db() as db:
        row = db.execute("SELECT * FROM sync_tasks WHERE name=?", (JOB_NAME,)).fetchone()
    task = row_to_dict(row) if row else {}
    payload = _parse_payload(task.get("message") if task else "")
    running = _is_process_running()
    raw_status = task.get("status") or "idle"
    effective_status = raw_status
    if raw_status in {"running", "stopping"} and not running:
        effective_status = "stopped" if raw_status == "stopping" else "idle"
    return {
        "name": JOB_NAME,
        "status": effective_status,
        "rawStatus": raw_status,
        "lastRunAt": task.get("last_run_at") or "",
        "payload": payload,
        "stats": payload.get("statsSnapshot") or {},
        "running": running,
        "stopRequested": _stop_requested,
    }


def _start_worker_process(payload: dict):
    global _process
    args = [sys.executable, "-m", "app.scripts.tpt_media_worker", json.dumps(payload, ensure_ascii=False)]
    _process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)


def _is_process_running() -> bool:
    return bool(_process and _process.poll() is None)


def _run_job(payload: dict):
    global _stop_requested
    status = "completed"
    message = payload
    try:
        while message["read"] < message["maxTotal"] and not _stop_requested:
            cooldown = _cooldown_seconds(message)
            if cooldown:
                message["cooldownSeconds"] = cooldown
                message["cooldownReason"] = "public_sources_rate_limited"
                message["updatedAt"] = _now()
                _write_task("running", message)
                _sleep_or_stop(cooldown)
                continue
            message["cooldownSeconds"] = 0
            message["cooldownReason"] = ""
            result = enrich_tpt_media_batch(
                limit=min(message["batchSize"], message["maxTotal"] - message["read"]),
                offset=0 if message["onlyMissing"] else message["read"],
                province=message["province"],
                a_level_only=message["aLevelOnly"],
                only_missing=message["onlyMissing"],
                sleep_seconds=message["sleepSeconds"],
                include_public_sources=message["includePublicSources"],
                use_amap=message["useAmap"],
                include_osm=message["includeOsm"],
            )
            message["read"] += result.get("read", 0)
            message["searched"] += result.get("searched", 0)
            message["withImages"] += result.get("withImages", 0)
            message["withProfiles"] += result.get("withProfiles", 0)
            message["notFound"] += result.get("notFound", 0)
            message["rateLimited"] = message.get("rateLimited", 0) + result.get("rateLimited", 0)
            message["sourceUnavailable"] = message.get("sourceUnavailable", 0) + result.get("sourceUnavailable", 0)
            message["failures"] = (message.get("failures") or [])[-20:] + (result.get("failures") or [])[:20]
            message["providerFailures"] = (message.get("providerFailures") or [])[-20:] + (result.get("providerFailures") or [])[:20]
            message["lastBatch"] = result
            if result.get("withImages", 0) or message["read"] % 20 == 0:
                message["statsSnapshot"] = tpt_enrichment_stats()
            message["updatedAt"] = _now()
            _write_task("running", message)
            if result.get("read", 0) == 0 or result.get("done"):
                break
            time.sleep(0.05)
        if _stop_requested:
            status = "stopped"
    except Exception as exc:
        status = "failed"
        message["error"] = str(exc)[:240]
        message["updatedAt"] = _now()
    finally:
        _write_task(status, message)


def _write_task(status: str, payload: dict):
    payload_json = json.dumps(payload, ensure_ascii=False)
    with get_db() as db:
        exists = db.execute("SELECT id FROM sync_tasks WHERE name=?", (JOB_NAME,)).fetchone()
        if exists:
            db.execute(
                "UPDATE sync_tasks SET status=?, last_run_at=?, message=? WHERE name=?",
                (status, _now(), payload_json, JOB_NAME),
            )
        else:
            db.execute(
                "INSERT INTO sync_tasks (name, source, status, last_run_at, message) VALUES (?,?,?,?,?)",
                (JOB_NAME, "tpt_jingdian", status, _now(), payload_json),
            )


def _parse_payload(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _cooldown_seconds(payload: dict) -> int:
    if not payload.get("includePublicSources") or payload.get("useAmap"):
        return 0
    return public_sources_blocked_seconds(include_osm=bool(payload.get("includeOsm")))


def _sleep_or_stop(seconds: int):
    for _ in range(max(1, min(int(seconds), 300))):
        if _stop_requested:
            break
        time.sleep(1)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
