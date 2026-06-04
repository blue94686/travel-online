import json
import sys
import time

from app.core.database import get_db
from app.services.scenic_external_enrichment_service import public_sources_blocked_seconds
from app.services.tpt_media_job_service import JOB_NAME, _now, _write_task
from app.services.tpt_profile_enrichment_service import enrich_tpt_media_batch, tpt_enrichment_stats


def main():
    payload = _load_payload()
    status = "completed"
    try:
        while payload["read"] < payload["maxTotal"] and not _should_stop():
            cooldown = _cooldown_seconds(payload)
            if cooldown:
                payload["cooldownSeconds"] = cooldown
                payload["cooldownReason"] = "public_sources_rate_limited"
                payload["updatedAt"] = _now()
                _write_task("running", payload)
                _sleep_or_stop(cooldown)
                continue
            payload["cooldownSeconds"] = 0
            payload["cooldownReason"] = ""
            result = enrich_tpt_media_batch(
                limit=1,
                offset=0 if payload["onlyMissing"] else payload["read"],
                province=payload["province"],
                a_level_only=payload["aLevelOnly"],
                only_missing=payload["onlyMissing"],
                sleep_seconds=payload["sleepSeconds"],
                include_public_sources=payload["includePublicSources"],
                use_amap=payload["useAmap"],
                include_osm=payload["includeOsm"],
            )
            payload["read"] += result.get("read", 0)
            payload["searched"] += result.get("searched", 0)
            payload["withImages"] += result.get("withImages", 0)
            payload["withProfiles"] += result.get("withProfiles", 0)
            payload["notFound"] += result.get("notFound", 0)
            payload["rateLimited"] = payload.get("rateLimited", 0) + result.get("rateLimited", 0)
            payload["sourceUnavailable"] = payload.get("sourceUnavailable", 0) + result.get("sourceUnavailable", 0)
            payload["failures"] = (payload.get("failures") or [])[-20:] + (result.get("failures") or [])[:20]
            payload["providerFailures"] = (payload.get("providerFailures") or [])[-20:] + (result.get("providerFailures") or [])[:20]
            payload["lastBatch"] = result
            if result.get("withImages", 0) or payload["read"] % 20 == 0:
                payload["statsSnapshot"] = tpt_enrichment_stats()
            payload["updatedAt"] = _now()
            _write_task("running", payload)
            if result.get("read", 0) == 0 or result.get("done"):
                break
            time.sleep(0.05)
        if _should_stop():
            status = "stopped"
    except Exception as exc:
        status = "failed"
        payload["error"] = str(exc)[:240]
        payload["updatedAt"] = _now()
    finally:
        _write_task(status, payload)


def _load_payload() -> dict:
    if len(sys.argv) < 2:
        raise SystemExit("missing payload")
    return json.loads(sys.argv[1])


def _should_stop() -> bool:
    with get_db() as db:
        row = db.execute("SELECT status FROM sync_tasks WHERE name=?", (JOB_NAME,)).fetchone()
    return bool(row and row["status"] in {"stopping", "stopped"})


def _cooldown_seconds(payload: dict) -> int:
    if not payload.get("includePublicSources") or payload.get("useAmap"):
        return 0
    return public_sources_blocked_seconds(include_osm=bool(payload.get("includeOsm")))


def _sleep_or_stop(seconds: int):
    for _ in range(max(1, min(int(seconds), 300))):
        if _should_stop():
            break
        time.sleep(1)


if __name__ == "__main__":
    main()
