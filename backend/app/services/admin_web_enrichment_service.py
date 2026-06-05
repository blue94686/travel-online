import json

from app.core.database import get_db, row_to_dict, rows_to_list


CRAWLER_JOB_NAME = "scenic_crawler_enrichment"
TPT_MEDIA_JOB_NAME = "tpt_media_full"
LEGACY_TPT_MEDIA_JOB_NAME = "tpt_media_job"
METRIC_KEY_MAP = {
    "totalscenic": "totalScenic",
    "missingimages": "missingImages",
    "undertargetimages": "underTargetImages",
    "spotswith3images": "spotsWith3Images",
    "spotswith4images": "spotsWith4Images",
    "missingprofiles": "missingProfiles",
    "missingfood": "missingFood",
    "missingpois": "missingPois",
    "pendingprofilecandidates": "pendingProfileCandidates",
    "pendingfoodcandidates": "pendingFoodCandidates",
    "pendinghikingcandidates": "pendingHikingCandidates",
    "pendingnearbycandidates": "pendingNearbyCandidates",
    "lowriskprofilecandidates": "lowRiskProfileCandidates",
    "pendingimagecandidates": "pendingImageCandidates",
    "lowriskimagecandidates": "lowRiskImageCandidates",
}


def web_enrichment_overview() -> dict:
    with get_db() as db:
        scenic = row_to_dict(
            db.execute(
                """
                SELECT
                  COUNT(*) AS totalScenic,
                  SUM(CASE WHEN cover_image_url IS NULL OR cover_image_url='' THEN 1 ELSE 0 END) AS missingImages,
                  SUM(CASE WHEN (
                    SELECT COUNT(*)
                    FROM scenic_images
                    WHERE scenic_images.scenic_id=scenic_spots.id
                      AND status='approved'
                  ) < 4 THEN 1 ELSE 0 END) AS underTargetImages,
                  SUM(CASE WHEN (
                    SELECT COUNT(*)
                    FROM scenic_images
                    WHERE scenic_images.scenic_id=scenic_spots.id
                      AND status='approved'
                  ) >= 3 THEN 1 ELSE 0 END) AS spotsWith3Images,
                  SUM(CASE WHEN (
                    SELECT COUNT(*)
                    FROM scenic_images
                    WHERE scenic_images.scenic_id=scenic_spots.id
                      AND status='approved'
                  ) >= 4 THEN 1 ELSE 0 END) AS spotsWith4Images,
                  SUM(CASE WHEN summary IS NULL OR summary='' OR description IS NULL OR description='' THEN 1 ELSE 0 END) AS missingProfiles,
                  SUM(CASE WHEN nearby_food IS NULL OR nearby_food='' OR nearby_food='[]' THEN 1 ELSE 0 END) AS missingFood,
                  SUM(CASE WHEN nearby_pois IS NULL OR nearby_pois='' OR nearby_pois='[]' THEN 1 ELSE 0 END) AS missingPois
                FROM scenic_spots
                """
            ).fetchone()
        ) or {}
        profile = row_to_dict(
            db.execute(
                """
                SELECT
                  COUNT(*) AS pendingProfileCandidates,
                  SUM(CASE WHEN candidate_type='nearby_food' THEN 1 ELSE 0 END) AS pendingFoodCandidates,
                  SUM(CASE WHEN candidate_type='hiking_poi' THEN 1 ELSE 0 END) AS pendingHikingCandidates,
                  SUM(CASE WHEN candidate_type='nearby_poi' THEN 1 ELSE 0 END) AS pendingNearbyCandidates,
                  SUM(CASE WHEN risk_level='low' THEN 1 ELSE 0 END) AS lowRiskProfileCandidates
                FROM scenic_profile_candidates
                WHERE status='pending'
                """
            ).fetchone()
        ) or {}
        image = row_to_dict(
            db.execute(
                """
                SELECT
                  COUNT(*) AS pendingImageCandidates,
                  SUM(CASE WHEN risk_level='low' THEN 1 ELSE 0 END) AS lowRiskImageCandidates
                FROM scenic_image_candidates
                WHERE COALESCE(status, 'pending')='pending'
                  AND COALESCE(review_status, 'pending')='pending'
                """
            ).fetchone()
        ) or {}
        crawler = _sync_task(db, CRAWLER_JOB_NAME)
        tpt_media = _sync_task(db, TPT_MEDIA_JOB_NAME) or _sync_task(db, LEGACY_TPT_MEDIA_JOB_NAME)
        recent = rows_to_list(
            db.execute(
                """
                SELECT id,name,source,status,last_run_at,message
                FROM sync_tasks
                WHERE name IN (?, ?, ?, 'data_sync', 'quality_check')
                   OR source IN ('scenic_crawler', 'tpt_jingdian', 'enrichment')
                ORDER BY COALESCE(last_run_at, '') DESC, id DESC
                LIMIT 8
                """,
                (CRAWLER_JOB_NAME, TPT_MEDIA_JOB_NAME, LEGACY_TPT_MEDIA_JOB_NAME),
            ).fetchall()
        )

    overview = _zero_none(_canonical_metric_keys(scenic | profile | image))
    profile_low = int(overview.get("lowRiskProfileCandidates") or 0)
    image_low = int(overview.get("lowRiskImageCandidates") or 0)
    overview["lowRiskCandidates"] = profile_low + image_low
    overview["pendingCandidates"] = int(overview.get("pendingProfileCandidates") or 0) + int(overview.get("pendingImageCandidates") or 0)
    overview["crawlerJob"] = crawler
    overview["tptMediaJob"] = tpt_media
    overview["recentTasks"] = [_normalize_task(row) for row in recent]
    return overview


def web_enrichment_candidates(
    candidate_type: str = "all",
    risk: str = "all",
    status: str = "pending",
    province: str = "",
    city: str = "",
    limit: int = 50,
) -> dict:
    limit = max(1, min(int(limit or 50), 200))
    candidate_type = candidate_type or "all"
    risk = risk or "all"
    status = status or "pending"
    with get_db() as db:
        image_rows = []
        profile_rows = []
        if candidate_type in {"all", "image"}:
            image_rows = _image_candidates(db, risk, status, province, city, limit)
        if candidate_type in {"all", "profile", "food", "hiking", "nearby"}:
            profile_rows = _profile_candidates(db, candidate_type, risk, status, province, city, limit)
    items = image_rows + profile_rows
    items.sort(key=lambda item: (item.get("created_at") or "", float(item.get("confidence") or 0)), reverse=True)
    return {"items": items[:limit], "total": len(items[:limit])}


def _image_candidates(db, risk: str, status: str, province: str, city: str, limit: int) -> list[dict]:
    sql = """
      SELECT
        c.id, 'image' AS candidate_kind, 'image' AS candidate_type, c.scenic_id,
        s.name AS scenic_name, s.province, s.city, c.title,
        c.image_url AS preview, c.source_name, c.source_type, c.source_url,
        c.risk_level, c.confidence, COALESCE(c.status, c.review_status, 'pending') AS status,
        c.created_at
      FROM scenic_image_candidates c
      LEFT JOIN scenic_spots s ON s.id=c.scenic_id
      WHERE 1=1
    """
    params = []
    if status != "all":
        sql += " AND COALESCE(c.status, c.review_status, 'pending')=?"
        params.append(status)
    if risk != "all":
        sql += " AND c.risk_level=?"
        params.append(risk)
    if province:
        sql += " AND s.province=?"
        params.append(province)
    if city:
        sql += " AND s.city=?"
        params.append(city)
    sql += " ORDER BY c.confidence DESC, c.id DESC LIMIT ?"
    params.append(limit)
    return [_normalize_candidate(row_to_dict(row) or {}) for row in db.execute(sql, params).fetchall()]


def _profile_candidates(db, candidate_type: str, risk: str, status: str, province: str, city: str, limit: int) -> list[dict]:
    sql = """
      SELECT
        c.id, 'profile' AS candidate_kind, c.candidate_type, c.scenic_id,
        s.name AS scenic_name, s.province, s.city, c.title,
        c.content AS preview, c.source_name, c.source_type, c.source_url,
        c.risk_level, c.confidence, c.status, c.created_at
      FROM scenic_profile_candidates c
      LEFT JOIN scenic_spots s ON s.id=c.scenic_id
      WHERE 1=1
    """
    params = []
    if status != "all":
        sql += " AND c.status=?"
        params.append(status)
    if risk != "all":
        sql += " AND c.risk_level=?"
        params.append(risk)
    type_map = {
        "food": ("nearby_food",),
        "hiking": ("hiking_poi",),
        "nearby": ("nearby_poi", "hiking_poi"),
        "profile": ("summary", "description", "official_site", "opening_hours", "address"),
    }
    mapped_types = type_map.get(candidate_type)
    if mapped_types:
        placeholders = ",".join(["?"] * len(mapped_types))
        sql += f" AND c.candidate_type IN ({placeholders})"
        params.extend(mapped_types)
    if province:
        sql += " AND s.province=?"
        params.append(province)
    if city:
        sql += " AND s.city=?"
        params.append(city)
    sql += " ORDER BY c.confidence DESC, c.id DESC LIMIT ?"
    params.append(limit)
    return [_normalize_candidate(row_to_dict(row) or {}) for row in db.execute(sql, params).fetchall()]


def _normalize_candidate(row: dict) -> dict:
    preview = row.get("preview") or ""
    if isinstance(preview, list):
        preview = json.dumps(preview, ensure_ascii=False)
    if isinstance(preview, str) and preview.strip().startswith("["):
        try:
            parsed = json.loads(preview)
            if isinstance(parsed, list) and parsed:
                names = [str(item.get("name") or item.get("title") or item) for item in parsed[:3]]
                preview = "、".join(names)
        except json.JSONDecodeError:
            pass
    return {
        "id": row.get("id"),
        "candidate_kind": row.get("candidate_kind") or "",
        "candidate_type": row.get("candidate_type") or "",
        "scenic_id": row.get("scenic_id"),
        "scenic_name": row.get("scenic_name") or "",
        "province": row.get("province") or "",
        "city": row.get("city") or "",
        "title": row.get("title") or "",
        "preview": str(preview or "")[:260],
        "source_name": row.get("source_name") or "",
        "source_type": row.get("source_type") or "",
        "source_url": row.get("source_url") or "",
        "risk_level": row.get("risk_level") or "medium",
        "confidence": row.get("confidence") or 0,
        "status": row.get("status") or "pending",
        "created_at": row.get("created_at") or "",
    }


def _sync_task(db, name: str) -> dict:
    row = row_to_dict(db.execute("SELECT * FROM sync_tasks WHERE name=?", (name,)).fetchone()) or {}
    if not row:
        return {}
    return _normalize_task(row | {"name": name})


def _normalize_task(row: dict) -> dict:
    payload = row.get("message") or {}
    if isinstance(payload, str):
        try:
            payload = json.loads(payload or "{}")
        except json.JSONDecodeError:
            payload = {"text": payload}
    return {
        "id": row.get("id"),
        "name": row.get("name") or "",
        "source": row.get("source") or "",
        "status": row.get("status") or "idle",
        "last_run_at": row.get("last_run_at") or "",
        "payload": payload if isinstance(payload, dict) else {},
    }


def _zero_none(values: dict) -> dict:
    return {key: (0 if value is None else value) for key, value in values.items()}


def _canonical_metric_keys(values: dict) -> dict:
    return {METRIC_KEY_MAP.get(str(key).lower(), key): value for key, value in values.items()}
