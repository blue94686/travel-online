import json
import subprocess
import sys
import threading
import time
from datetime import datetime

from app.core.database import get_db, row_to_dict, rows_to_list
from app.services.amap_service import search_amap_pois
from app.services.audit_service import write_audit
from app.services.provider_config_service import get_secret
from app.services.scenic_external_enrichment_service import public_source_bundle_detailed, public_sources_blocked_seconds


JOB_NAME = "scenic_crawler_enrichment"
HIKING_TERMS = ("山", "峰", "岭", "峡", "谷", "森林", "步道", "栈道", "长城", "草原")
_lock = threading.Lock()
_process: subprocess.Popen | None = None
_stop_requested = False


def run_crawler_batch(
    limit: int = 10,
    province: str = "",
    city: str = "",
    only_missing: bool = True,
    include_public_sources: bool = True,
    include_pois: bool = True,
    include_paid_providers: bool = False,
    include_osm: bool = True,
    sleep_seconds: float = 0.8,
) -> dict:
    limit = max(1, min(int(limit or 10), 100))
    with get_db() as db:
        rows = _select_scenics(db, limit, province, city, only_missing)
        stats = {
            "read": len(rows),
            "searched": 0,
            "profileCandidates": 0,
            "imageCandidates": 0,
            "lowRiskCandidates": 0,
            "failures": [],
            "providerFailures": [],
            "done": len(rows) < limit,
        }
        for scenic in rows:
            try:
                result = _crawl_one(db, scenic, include_public_sources, include_pois, include_paid_providers, include_osm)
                stats["searched"] += 1
                stats["profileCandidates"] += result["profileCandidates"]
                stats["imageCandidates"] += result["imageCandidates"]
                stats["lowRiskCandidates"] += result["lowRiskCandidates"]
                stats["providerFailures"].extend(result.get("providerFailures") or [])
            except Exception as exc:
                stats["failures"].append({"scenic_id": scenic.get("id"), "name": scenic.get("name"), "message": str(exc)[:180]})
            if sleep_seconds:
                time.sleep(max(0, min(float(sleep_seconds), 3)))
    return stats


def start_crawler_job(
    batch_size: int = 5,
    max_total: int = 2528,
    province: str = "",
    city: str = "",
    only_missing: bool = True,
    include_public_sources: bool = True,
    include_pois: bool = True,
    include_paid_providers: bool = False,
    include_osm: bool = True,
    sleep_seconds: float = 1.5,
) -> dict:
    global _stop_requested
    with _lock:
        if _is_process_running():
            return crawler_status() | {"alreadyRunning": True}
        _stop_requested = False
        payload = {
            "batchSize": max(1, min(int(batch_size or 5), 50)),
            "maxTotal": max(1, min(int(max_total or 2528), 50000)),
            "province": province,
            "city": city,
            "onlyMissing": only_missing,
            "includePublicSources": include_public_sources,
            "includePois": include_pois,
            "includePaidProviders": include_paid_providers,
            "includeOsm": include_osm,
            "sleepSeconds": max(0.5, min(float(sleep_seconds), 5)),
            "startedAt": _now(),
            "read": 0,
            "searched": 0,
            "profileCandidates": 0,
            "imageCandidates": 0,
            "lowRiskCandidates": 0,
            "failures": [],
            "providerFailures": [],
            "lastBatch": {},
            "statsSnapshot": _crawler_stats(),
        }
        _write_task("running", payload)
        _start_worker_process(payload)
    return crawler_status()


def stop_crawler_job() -> dict:
    global _stop_requested
    _stop_requested = True
    status = crawler_status()
    if status.get("status") == "running":
        _write_task("stopping", status.get("payload") or {})
    return crawler_status()


def crawler_status() -> dict:
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
        "running": running,
        "stopRequested": _stop_requested,
        "lastRunAt": task.get("last_run_at") or "",
        "payload": payload,
        "stats": _crawler_stats(),
        "cooldownSeconds": public_sources_blocked_seconds(include_osm=True),
    }


def approve_low_risk_candidates(limit: int = 200) -> dict:
    limit = max(1, min(int(limit or 200), 1000))
    approved_images = 0
    approved_pois = 0
    skipped = 0
    with get_db() as db:
        image_rows = rows_to_list(
            db.execute(
                """
                SELECT * FROM scenic_image_candidates
                WHERE risk_level='low'
                  AND COALESCE(status, 'pending')='pending'
                  AND COALESCE(review_status, 'pending')='pending'
                ORDER BY confidence DESC, id ASC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        )
        for row in image_rows:
            if _approve_image(db, row):
                approved_images += 1
            else:
                skipped += 1

        remaining = max(0, limit - approved_images)
        poi_rows = rows_to_list(
            db.execute(
                """
                SELECT * FROM scenic_profile_candidates
                WHERE risk_level='low'
                  AND status='pending'
                  AND candidate_type IN ('nearby_food','hiking_poi','nearby_poi')
                ORDER BY confidence DESC, id ASC
                LIMIT ?
                """,
                (remaining,),
            ).fetchall()
        )
        for row in poi_rows:
            if _approve_poi(db, row):
                approved_pois += 1
            else:
                skipped += 1
    _safe_audit("爬虫补全审核", f"批量通过低风险候选：图片 {approved_images}，POI {approved_pois}，跳过 {skipped}")
    return {"approvedImages": approved_images, "approvedPois": approved_pois, "skipped": skipped}


def _run_job(payload: dict):
    global _stop_requested
    status = "completed"
    message = dict(payload or {})
    try:
        while int(message.get("read") or 0) < int(message.get("maxTotal") or 0) and not _stop_requested and not _task_stop_requested():
            cooldown = public_sources_blocked_seconds(include_osm=bool(message.get("includeOsm", True)))
            if cooldown and message.get("includePublicSources"):
                message["cooldownSeconds"] = cooldown
                message["cooldownReason"] = "public_sources_rate_limited"
                message["updatedAt"] = _now()
                _write_task("running", message)
                _sleep_or_stop(cooldown)
                continue
            result = run_crawler_batch(
                limit=min(int(message["batchSize"]), int(message["maxTotal"]) - int(message.get("read") or 0)),
                province=message.get("province") or "",
                city=message.get("city") or "",
                only_missing=bool(message.get("onlyMissing", True)),
                include_public_sources=bool(message.get("includePublicSources", True)),
                include_pois=bool(message.get("includePois", True)),
                include_paid_providers=bool(message.get("includePaidProviders", False)),
                include_osm=bool(message.get("includeOsm", True)),
                sleep_seconds=float(message.get("sleepSeconds") or 1.5),
            )
            message["read"] = int(message.get("read") or 0) + result.get("read", 0)
            message["searched"] = int(message.get("searched") or 0) + result.get("searched", 0)
            message["profileCandidates"] = int(message.get("profileCandidates") or 0) + result.get("profileCandidates", 0)
            message["imageCandidates"] = int(message.get("imageCandidates") or 0) + result.get("imageCandidates", 0)
            message["lowRiskCandidates"] = int(message.get("lowRiskCandidates") or 0) + result.get("lowRiskCandidates", 0)
            message["failures"] = (message.get("failures") or [])[-20:] + (result.get("failures") or [])[:20]
            message["providerFailures"] = (message.get("providerFailures") or [])[-20:] + (result.get("providerFailures") or [])[:20]
            message["lastBatch"] = result
            message["statsSnapshot"] = _crawler_stats()
            message["cooldownSeconds"] = 0
            message["cooldownReason"] = ""
            message["updatedAt"] = _now()
            _write_task("running", message)
            if result.get("read", 0) == 0 or result.get("done"):
                break
        if _stop_requested or _task_stop_requested():
            status = "stopped"
    except Exception as exc:
        status = "failed"
        message["error"] = str(exc)[:240]
        message["updatedAt"] = _now()
    finally:
        _write_task(status, message)


def _select_scenics(db, limit: int, province: str, city: str, only_missing: bool) -> list[dict]:
    sql = "SELECT * FROM scenic_spots WHERE 1=1"
    params = []
    if province:
        sql += " AND province=?"
        params.append(province)
    if city:
        sql += " AND city=?"
        params.append(city)
    if only_missing:
        sql += """
          AND (
            cover_image_url IS NULL OR cover_image_url='' OR
            summary IS NULL OR summary='' OR
            description IS NULL OR description='' OR
            nearby_food IS NULL OR nearby_food='' OR nearby_food='[]' OR
            nearby_pois IS NULL OR nearby_pois='' OR nearby_pois='[]' OR
            recommended_routes IS NULL OR recommended_routes='' OR recommended_routes='[]'
          )
        """
    sql += " ORDER BY CASE level WHEN '5A' THEN 0 WHEN '4A' THEN 1 ELSE 2 END, id ASC LIMIT ?"
    params.append(limit)
    return rows_to_list(db.execute(sql, params).fetchall())


def _crawl_one(db, scenic: dict, include_public_sources: bool, include_pois: bool, include_paid_providers: bool, include_osm: bool) -> dict:
    result = {"profileCandidates": 0, "imageCandidates": 0, "lowRiskCandidates": 0, "providerFailures": []}
    profile_candidates = []
    image_candidates = []
    if include_public_sources:
        public_profiles, public_images, provider_failures = public_source_bundle_detailed(scenic, include_osm=include_osm)
        profile_candidates.extend(public_profiles or [])
        image_candidates.extend(public_images or [])
        result["providerFailures"].extend(provider_failures or [])
    if include_pois:
        for poi in _collect_poi_candidates(scenic, include_paid_providers=include_paid_providers):
            profile_candidates.append(_profile_candidate_from_poi(scenic, poi))

    for candidate in profile_candidates:
        normalized = _normalize_profile_candidate(scenic, candidate)
        if _insert_profile_candidate(db, normalized):
            result["profileCandidates"] += 1
            if normalized.get("risk_level") == "low" and normalized.get("candidate_type") in {"nearby_food", "hiking_poi", "nearby_poi"}:
                result["lowRiskCandidates"] += 1
    for candidate in image_candidates:
        normalized = _normalize_image_candidate(scenic, candidate)
        if _insert_image_candidate(db, normalized):
            result["imageCandidates"] += 1
            if normalized.get("risk_level") == "low":
                result["lowRiskCandidates"] += 1
    return result


def _collect_poi_candidates(scenic: dict, include_food: bool = True, include_hiking: bool = True, include_paid_providers: bool = False) -> list[dict]:
    candidates = []
    if include_food and include_paid_providers and (get_secret("amap_web_service", "AMAP_WEB_SERVICE_KEY") or get_secret("amap", "AMAP_WEB_SERVICE_KEY")):
        result = search_amap_pois(f"{scenic.get('name') or ''} 美食", city=scenic.get("city") or "", limit=5, types="050000")
        for item in result.get("items") or []:
            candidates.append(_poi_from_amap(item, "nearby_food"))
    if include_hiking and _looks_hiking_scenic(scenic):
        name = scenic.get("name") or "景区"
        candidates.append(
            {
                "type": "hiking_poi",
                "name": f"{name}轻徒步/观景步道候选",
                "address": scenic.get("address") or scenic.get("district") or scenic.get("city") or "",
                "distance_text": "景区内或入口周边",
                "source_url": "https://www.openstreetmap.org/",
                "source_name": "OpenStreetMap",
                "source_type": "crawler_poi",
                "risk_level": "low",
                "confidence": 72,
            }
        )
    return candidates


def _poi_from_amap(item: dict, candidate_type: str) -> dict:
    return {
        "type": candidate_type,
        "name": item.get("name") or "",
        "address": item.get("address") or "",
        "latitude": item.get("latitude"),
        "longitude": item.get("longitude"),
        "source_url": item.get("map_url") or "",
        "source_name": "高德 POI",
        "source_type": "crawler_poi",
        "risk_level": "low" if item.get("name") else "medium",
        "confidence": 76 if item.get("name") else 55,
    }


def _profile_candidate_from_poi(scenic: dict, poi: dict) -> dict:
    item = {
        "name": poi.get("name") or "",
        "address": poi.get("address") or "",
        "distance_text": poi.get("distance_text") or "",
        "latitude": poi.get("latitude"),
        "longitude": poi.get("longitude"),
        "source": poi.get("source_name") or poi.get("source_type") or "crawler",
        "source_url": poi.get("source_url") or "",
    }
    item = {key: value for key, value in item.items() if value not in (None, "")}
    candidate_type = poi.get("type") or "nearby_poi"
    return {
        "scenic_id": scenic["id"],
        "candidate_type": candidate_type,
        "title": f"{scenic.get('name') or '景区'} {candidate_type} 候选",
        "content": json.dumps([item], ensure_ascii=False),
        "source_url": poi.get("source_url") or "",
        "source_name": poi.get("source_name") or "crawler",
        "source_type": poi.get("source_type") or "crawler_poi",
        "confidence": int(poi.get("confidence") or 60),
        "risk_level": poi.get("risk_level") or "medium",
        "raw_payload_json": json.dumps({"poi": poi}, ensure_ascii=False),
    }


def _normalize_profile_candidate(scenic: dict, candidate: dict) -> dict:
    return {
        "scenic_id": candidate.get("scenic_id") or scenic["id"],
        "candidate_type": candidate.get("candidate_type") or "summary",
        "title": candidate.get("title") or f"{scenic.get('name') or '景区'}资料候选",
        "content": candidate.get("content") or "",
        "source_url": candidate.get("source_url") or "",
        "source_name": candidate.get("source_name") or candidate.get("source_type") or "public_source",
        "source_type": candidate.get("source_type") or "public_source",
        "confidence": int(candidate.get("confidence") or 0),
        "risk_level": candidate.get("risk_level") or "medium",
        "raw_payload_json": candidate.get("raw_payload_json") or "{}",
        "diff_json": candidate.get("diff_json") or "{}",
    }


def _normalize_image_candidate(scenic: dict, candidate: dict) -> dict:
    confidence = float(candidate.get("confidence") or 0)
    license_text = candidate.get("license") or ""
    source_type = candidate.get("source_type") or candidate.get("provider") or "public_source"
    risk_level = candidate.get("risk_level") or ("low" if license_text or source_type in {"wikimedia_commons", "wikipedia"} else "medium")
    return {
        "scenic_id": candidate.get("scenic_id") or scenic["id"],
        "image_url": candidate.get("image_url") or candidate.get("content") or "",
        "thumbnail_url": candidate.get("thumbnail_url") or candidate.get("image_url") or "",
        "source_url": candidate.get("source_url") or "",
        "source_name": candidate.get("source_name") or source_type,
        "source_type": source_type,
        "license": license_text,
        "attribution": candidate.get("attribution") or "",
        "provider": candidate.get("provider") or source_type,
        "risk_level": risk_level,
        "status": "pending",
        "review_status": "pending",
        "title": candidate.get("title") or scenic.get("name") or "",
        "confidence": confidence,
        "quality_score": int(candidate.get("quality_score") or confidence),
        "raw_payload_json": candidate.get("raw_payload_json") or "{}",
    }


def _insert_profile_candidate(db, candidate: dict) -> bool:
    if not candidate.get("content") or not candidate.get("scenic_id"):
        return False
    try:
        cur = db.execute(
            """
            INSERT OR IGNORE INTO scenic_profile_candidates (
              scenic_id,candidate_type,title,content,source_url,source_name,source_type,
              confidence,risk_level,status,raw_payload_json,diff_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                candidate["scenic_id"],
                candidate["candidate_type"],
                candidate["title"],
                candidate["content"],
                candidate["source_url"],
                candidate["source_name"],
                candidate["source_type"],
                int(candidate["confidence"]),
                candidate["risk_level"],
                "pending",
                candidate.get("raw_payload_json") or "{}",
                candidate.get("diff_json") or "{}",
            ),
        )
        return bool(getattr(cur, "rowcount", 1))
    except Exception:
        return False


def _insert_image_candidate(db, candidate: dict) -> bool:
    if not candidate.get("image_url") or _image_exists(db, candidate["scenic_id"], candidate["image_url"]):
        return False
    db.execute(
        """
        INSERT INTO scenic_image_candidates
        (scenic_id,image_url,thumbnail_url,source_url,source_name,source_type,license,attribution,provider,risk_level,status,title,confidence,quality_score,availability_status,failure_count,review_status,raw_payload_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            candidate["scenic_id"],
            candidate["image_url"],
            candidate.get("thumbnail_url") or candidate["image_url"],
            candidate.get("source_url") or "",
            candidate.get("source_name") or "",
            candidate.get("source_type") or "",
            candidate.get("license") or "",
            candidate.get("attribution") or "",
            candidate.get("provider") or candidate.get("source_type") or "",
            candidate.get("risk_level") or "medium",
            "pending",
            candidate.get("title") or "",
            float(candidate.get("confidence") or 0),
            int(candidate.get("quality_score") or 0),
            "unchecked",
            0,
            "pending",
            candidate.get("raw_payload_json") or "{}",
        ),
    )
    return True


def _approve_image(db, candidate: dict) -> bool:
    if not candidate.get("image_url"):
        return False
    if not _approved_image_exists(db, candidate["scenic_id"], candidate["image_url"]):
        cover = db.execute(
            "SELECT id FROM scenic_images WHERE scenic_id=? AND status='approved' AND is_cover=1 LIMIT 1",
            (candidate["scenic_id"],),
        ).fetchone()
        db.execute(
            """
            INSERT OR IGNORE INTO scenic_images (
              scenic_id,url,thumbnail_url,status,is_cover,source,source_url,license,attribution,provider,quality_score,last_checked_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            """,
            (
                candidate["scenic_id"],
                candidate["image_url"],
                candidate.get("thumbnail_url") or candidate["image_url"],
                "approved",
                0 if cover else 1,
                candidate.get("source_name") or candidate.get("source_type") or "crawler",
                candidate.get("source_url") or "",
                candidate.get("license") or "",
                candidate.get("attribution") or "",
                candidate.get("provider") or candidate.get("source_type") or "",
                int(candidate.get("quality_score") or round(float(candidate.get("confidence") or 0))),
            ),
        )
        if not cover:
            db.execute(
                "UPDATE scenic_spots SET cover_image_url=CASE WHEN cover_image_url IS NULL OR cover_image_url='' THEN ? ELSE cover_image_url END, last_enriched_at=? WHERE id=?",
                (candidate["image_url"], _now(), candidate["scenic_id"]),
            )
    db.execute(
        """
        UPDATE scenic_image_candidates
        SET status='approved', review_status='approved', availability_status='accepted', last_checked_at=CURRENT_TIMESTAMP
        WHERE id=?
        """,
        (candidate["id"],),
    )
    return True


def _approve_poi(db, candidate: dict) -> bool:
    scenic = row_to_dict(db.execute("SELECT * FROM scenic_spots WHERE id=?", (candidate["scenic_id"],)).fetchone())
    if not scenic:
        return False
    items = _candidate_content_list(candidate.get("content"))
    if not items:
        return False
    if candidate["candidate_type"] == "nearby_food":
        merged = _merge_items(_json_list(scenic.get("nearby_food")), items)
        db.execute("UPDATE scenic_spots SET nearby_food=?, last_enriched_at=? WHERE id=?", (json.dumps(merged, ensure_ascii=False), _now(), candidate["scenic_id"]))
    else:
        merged = _merge_items(_json_list(scenic.get("nearby_pois")), items)
        routes = _merge_routes(_json_list(scenic.get("recommended_routes")), items)
        db.execute(
            "UPDATE scenic_spots SET nearby_pois=?, recommended_routes=?, last_enriched_at=? WHERE id=?",
            (json.dumps(merged, ensure_ascii=False), json.dumps(routes, ensure_ascii=False), _now(), candidate["scenic_id"]),
        )
    db.execute(
        "UPDATE scenic_profile_candidates SET status='merged', reviewed_at=CURRENT_TIMESTAMP, reviewed_by='admin' WHERE id=?",
        (candidate["id"],),
    )
    return True


def _crawler_stats() -> dict:
    with get_db() as db:
        scenic = db.execute(
            """
            SELECT
              COUNT(*) AS totalScenic,
              SUM(CASE WHEN cover_image_url IS NULL OR cover_image_url='' THEN 1 ELSE 0 END) AS missingImages,
              SUM(CASE WHEN summary IS NULL OR summary='' OR description IS NULL OR description='' THEN 1 ELSE 0 END) AS missingProfiles,
              SUM(CASE WHEN nearby_food IS NULL OR nearby_food='' OR nearby_food='[]' THEN 1 ELSE 0 END) AS missingFood,
              SUM(CASE WHEN nearby_pois IS NULL OR nearby_pois='' OR nearby_pois='[]' THEN 1 ELSE 0 END) AS missingPois
            FROM scenic_spots
            """
        ).fetchone()
        profiles = db.execute(
            """
            SELECT
              COUNT(*) AS pendingProfileCandidates,
              SUM(CASE WHEN risk_level='low' AND candidate_type IN ('nearby_food','hiking_poi','nearby_poi') THEN 1 ELSE 0 END) AS lowRiskProfileCandidates
            FROM scenic_profile_candidates
            WHERE status='pending'
            """
        ).fetchone()
        images = db.execute(
            """
            SELECT
              COUNT(*) AS pendingImageCandidates,
              SUM(CASE WHEN risk_level='low' THEN 1 ELSE 0 END) AS lowRiskImageCandidates
            FROM scenic_image_candidates
            WHERE COALESCE(status, 'pending')='pending'
              AND COALESCE(review_status, 'pending')='pending'
            """
        ).fetchone()
    scenic_stats = dict(scenic or {})
    profile_stats = dict(profiles or {})
    image_stats = dict(images or {})
    low_risk = int(profile_stats.get("lowRiskProfileCandidates") or 0) + int(image_stats.get("lowRiskImageCandidates") or 0)
    pending = int(profile_stats.get("pendingProfileCandidates") or 0) + int(image_stats.get("pendingImageCandidates") or 0)
    return scenic_stats | profile_stats | image_stats | {"lowRiskCandidates": low_risk, "pendingCandidates": pending}


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
                (JOB_NAME, "scenic_crawler", status, _now(), payload_json),
            )


def _start_worker_process(payload: dict):
    global _process
    args = [sys.executable, "-m", "app.scripts.scenic_crawler_worker", json.dumps(payload, ensure_ascii=False)]
    _process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)


def _is_process_running() -> bool:
    return bool(_process and _process.poll() is None)


def _parse_payload(value: str) -> dict:
    try:
        parsed = json.loads(value or "{}")
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def _task_stop_requested() -> bool:
    try:
        with get_db() as db:
            row = db.execute("SELECT status FROM sync_tasks WHERE name=?", (JOB_NAME,)).fetchone()
        return bool(row and row["status"] == "stopping")
    except Exception:
        return False


def _sleep_or_stop(seconds: int):
    for _ in range(max(1, min(int(seconds), 300))):
        if _stop_requested:
            break
        time.sleep(1)


def _json_list(value) -> list:
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (TypeError, json.JSONDecodeError):
        return []


def _candidate_content_list(value) -> list[dict]:
    parsed = _json_list(value)
    return [item for item in parsed if isinstance(item, dict) and item.get("name")]


def _merge_items(existing: list, incoming: list) -> list:
    merged = []
    seen = set()
    for item in [*(existing or []), *(incoming or [])]:
        if not isinstance(item, dict):
            continue
        key = (item.get("name") or "", item.get("source_url") or item.get("address") or "")
        if not key[0] or key in seen:
            continue
        seen.add(key)
        merged.append(item)
    return merged[:12]


def _merge_routes(existing: list, items: list[dict]) -> list:
    routes = [str(item) for item in existing or [] if str(item).strip()]
    for item in items:
        name = item.get("name") or ""
        if not name:
            continue
        route = f"{name} -> 景区核心游览点 -> 返回游客服务点"
        if route not in routes:
            routes.append(route)
    return routes[:8]


def _image_exists(db, scenic_id: int, image_url: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM scenic_image_candidates WHERE scenic_id=? AND image_url=? LIMIT 1",
        (scenic_id, image_url),
    ).fetchone()
    return bool(row)


def _approved_image_exists(db, scenic_id: int, image_url: str) -> bool:
    row = db.execute(
        "SELECT 1 FROM scenic_images WHERE scenic_id=? AND url=? LIMIT 1",
        (scenic_id, image_url),
    ).fetchone()
    return bool(row)


def _looks_hiking_scenic(scenic: dict) -> bool:
    text = " ".join(str(scenic.get(key) or "") for key in ("name", "tags", "summary", "description", "district", "city"))
    return any(term in text for term in HIKING_TERMS)


def _safe_audit(module: str, action: str):
    try:
        write_audit(module, action)
    except Exception:
        return


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
