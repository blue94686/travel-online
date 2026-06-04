import json
from datetime import datetime

from app.core.database import get_db, row_to_dict, rows_to_list
from app.services.audit_service import write_audit
from app.services.nearby_recommendation_service import generate_nearby
from app.services.scenic_content_merge_service import build_diff, merge_approved_candidates
from app.services.scenic_external_enrichment_service import public_source_candidates
from app.services.scenic_profile_search_service import generate_profile_candidates
from app.services.scenic_quality_score_service import calculate_completeness_score, score_level


DEMO_IMAGE_MARKERS = (
    "images.unsplash.com",
    "/images/hero-mountain-lake",
)

KNOWN_PUBLIC_COORDINATES = {
    "黄山风景区": (30.1329, 118.1638),
    "黄山": (30.1329, 118.1638),
    "桂林漓江风景区": (25.1500, 110.4167),
    "漓江": (25.1500, 110.4167),
    "千岛湖风景区": (29.4836, 119.2136),
    "千岛湖": (29.4836, 119.2136),
    "灵隐寺": (30.2400, 120.1020),
    "雷峰塔景区": (30.2336, 120.1486),
    "雷峰塔": (30.2336, 120.1486),
    "曲院风荷": (30.2510, 120.1330),
}


def missing_fields(item):
    checks = {
        "详细介绍": item.get("description"),
        "官网": item.get("official_website"),
        "封面图": item.get("cover_image_url"),
        "简介": item.get("summary"),
        "开放时间": item.get("opening_hours"),
        "门票": item.get("ticket_price"),
        "坐标": item.get("latitude") and item.get("longitude"),
    }
    return [label for label, value in checks.items() if not value]


def enrichment_overview():
    with get_db() as db:
        row = db.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN description IS NULL OR description='' THEN 1 ELSE 0 END) AS missing_description,
              SUM(CASE WHEN cover_image_url IS NULL OR cover_image_url='' THEN 1 ELSE 0 END) AS missing_images,
              SUM(CASE WHEN official_website IS NULL OR official_website='' THEN 1 ELSE 0 END) AS missing_website,
              SUM(CASE WHEN ticket_price IS NULL OR ticket_price='' THEN 1 ELSE 0 END) AS missing_ticket,
              SUM(CASE WHEN opening_hours IS NULL OR opening_hours='' THEN 1 ELSE 0 END) AS missing_opening_hours,
              SUM(CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 ELSE 0 END) AS missing_coordinate,
              SUM(CASE WHEN
                description IS NULL OR description='' OR
                official_website IS NULL OR official_website='' OR
                cover_image_url IS NULL OR cover_image_url='' OR
                summary IS NULL OR summary='' OR
                opening_hours IS NULL OR opening_hours='' OR
                ticket_price IS NULL OR ticket_price='' OR
                latitude IS NULL OR longitude IS NULL
              THEN 1 ELSE 0 END) AS missing_scenic,
              SUM(CASE WHEN
                (CASE WHEN description IS NULL OR description='' THEN 1 ELSE 0 END) +
                (CASE WHEN official_website IS NULL OR official_website='' THEN 1 ELSE 0 END) +
                (CASE WHEN cover_image_url IS NULL OR cover_image_url='' THEN 1 ELSE 0 END) +
                (CASE WHEN summary IS NULL OR summary='' THEN 1 ELSE 0 END) +
                (CASE WHEN opening_hours IS NULL OR opening_hours='' THEN 1 ELSE 0 END) +
                (CASE WHEN ticket_price IS NULL OR ticket_price='' THEN 1 ELSE 0 END) +
                (CASE WHEN latitude IS NULL OR longitude IS NULL THEN 1 ELSE 0 END)
                >= 3 THEN 1 ELSE 0 END) AS low_completeness
            FROM scenic_spots
            """
        ).fetchone()
        pending_profile = db.execute("SELECT COUNT(*) AS c FROM scenic_profile_candidates WHERE status='pending'").fetchone()["c"]
        pending_images = db.execute("SELECT COUNT(*) AS c FROM scenic_image_candidates WHERE COALESCE(status, review_status)='pending'").fetchone()["c"]
        task_count = db.execute("SELECT COUNT(*) AS c FROM enrichment_tasks").fetchone()["c"]
    return {
        "totalScenic": row["total"] or 0,
        "missingScenic": row["missing_scenic"] or 0,
        "missingDescription": row["missing_description"] or 0,
        "missingImages": row["missing_images"] or 0,
        "missingWebsite": row["missing_website"] or 0,
        "missingTicket": row["missing_ticket"] or 0,
        "missingOpeningHours": row["missing_opening_hours"] or 0,
        "missingCoordinate": row["missing_coordinate"] or 0,
        "lowCompleteness": row["low_completeness"] or 0,
        "pendingCandidates": pending_profile + pending_images,
        "recentTasks": task_count,
        "apiKeyHint": "需配置 Bing Search Key、Bing Image Search Key、高德 Key 可增强搜索；无 Key 时仅生成搜索链接和本地候选。",
    }


def profile_overview():
    return enrichment_overview()


def missing_scenic():
    with get_db() as db:
        scenic = rows_to_list(db.execute("SELECT * FROM scenic_spots ORDER BY id").fetchall())
    result = []
    for item in scenic:
        fields = missing_fields(item)
        completeness = calculate_completeness_score(item)
        result.append(item | {"missingFields": fields, "completeness": completeness, "qualityLevel": score_level(completeness)})
    return result


def run_profile_search(scenic_id: int):
    with get_db() as db:
        scenic = db.execute("SELECT * FROM scenic_spots WHERE id=?", (scenic_id,)).fetchone()
        if not scenic:
            return {"status": "not_found", "candidate_count": 0, "candidates": []}
        scenic = row_to_dict(scenic)
        api_config = _api_config(db)
        keyword = f"{scenic['name']} {scenic.get('province','')} {scenic.get('city','')} 景区介绍 官方网站 门票 开放时间 图片"
        cur = db.execute(
            "INSERT INTO enrichment_tasks (scenic_id,keyword,task_type,status,message,created_by) VALUES (?,?,?,?,?,?)",
            (scenic_id, keyword, "profile_search", "running", "正在生成景区资料候选", "admin"),
        )
        task_id = cur.lastrowid
        candidates = generate_profile_candidates(scenic, api_config)
        inserted = []
        for candidate in candidates:
            candidate["diff_json"] = json.dumps(build_diff(scenic, candidate), ensure_ascii=False)
            inserted_id = _insert_profile_candidate(db, candidate)
            if inserted_id:
                inserted.append(inserted_id)
            _insert_enrichment_result(db, task_id, candidate)
            if candidate["candidate_type"] == "image":
                _insert_image_candidate(db, candidate)
        db.execute(
            "UPDATE enrichment_tasks SET status=?, finished_at=CURRENT_TIMESTAMP, message=? WHERE id=?",
            ("success", "已生成候选，等待管理员审核", task_id),
        )
    generate_nearby(scenic_id)
    write_audit("景区资料补全", f"运行景区 #{scenic_id} 自动搜索补全")
    return {
        "task_id": task_id,
        "status": "success",
        "candidate_count": len(inserted),
        "fallback": not any(api_config.values()),
        "message": "候选已进入待审核，不会直接覆盖正式资料。",
        "candidates": inserted,
    }


def bulk_profile_search(filters: dict):
    limit = int(filters.get("limit") or 20)
    only_missing = bool(filters.get("only_missing", True))
    sql = "SELECT * FROM scenic_spots WHERE 1=1"
    params = []
    for field in ("province", "city", "level"):
        if filters.get(field):
            sql += f" AND {field}=?"
            params.append(filters[field])
    if only_missing:
        sql += " AND (description IS NULL OR description='' OR official_website IS NULL OR official_website='' OR cover_image_url IS NULL OR cover_image_url='' OR latitude IS NULL OR longitude IS NULL OR ticket_price IS NULL OR ticket_price='' OR opening_hours IS NULL OR opening_hours='')"
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    with get_db() as db:
        rows = rows_to_list(db.execute(sql, params).fetchall())
    results = []
    for row in rows:
        try:
            results.append(run_profile_search(row["id"]))
        except Exception as exc:  # keep bulk tasks moving
            results.append({"scenic_id": row["id"], "status": "failed", "message": str(exc)})
    return {"requested": len(rows), "limit": limit, "results": results}


def profile_candidates(scenic_id: int):
    with get_db() as db:
        return rows_to_list(
            db.execute(
                "SELECT * FROM scenic_profile_candidates WHERE scenic_id=? ORDER BY status='pending' DESC, confidence DESC, id DESC",
                (scenic_id,),
            ).fetchall()
        )


def image_candidates(scenic_id: int):
    with get_db() as db:
        return rows_to_list(
            db.execute(
                """
                SELECT *
                FROM scenic_image_candidates
                WHERE scenic_id=?
                ORDER BY COALESCE(status, review_status)='pending' DESC, quality_score DESC, confidence DESC, id DESC
                """,
                (scenic_id,),
            ).fetchall()
        )


def approve_image_candidate(candidate_id: int, reviewer: str = "admin"):
    with get_db() as db:
        candidate = db.execute("SELECT * FROM scenic_image_candidates WHERE id=?", (candidate_id,)).fetchone()
        if not candidate:
            return {"id": candidate_id, "status": "not_found"}
        candidate = dict(candidate)
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
                0,
                candidate.get("source_name") or candidate.get("source_type") or "external",
                candidate.get("source_url") or "",
                candidate.get("license") or "",
                candidate.get("attribution") or "",
                candidate.get("provider") or candidate.get("source_type") or "",
                int(candidate.get("quality_score") or round(float(candidate.get("confidence") or 0) * 100)),
            ),
        )
        cover = db.execute(
            "SELECT id FROM scenic_images WHERE scenic_id=? AND status='approved' AND is_cover=1 LIMIT 1",
            (candidate["scenic_id"],),
        ).fetchone()
        if not cover:
            db.execute(
                "UPDATE scenic_images SET is_cover=1 WHERE scenic_id=? AND url=?",
                (candidate["scenic_id"], candidate["image_url"]),
            )
        db.execute(
            """
            UPDATE scenic_image_candidates
            SET status='approved', review_status='approved', last_checked_at=CURRENT_TIMESTAMP, availability_status='accepted'
            WHERE id=?
            """,
            (candidate_id,),
        )
        row = db.execute("SELECT * FROM scenic_image_candidates WHERE id=?", (candidate_id,)).fetchone()
    write_audit("景区图片审核", f"通过图片候选 #{candidate_id}")
    return row_to_dict(row) or {"id": candidate_id, "status": "approved"}


def reject_image_candidate(candidate_id: int, reviewer: str = "admin"):
    with get_db() as db:
        db.execute(
            """
            UPDATE scenic_image_candidates
            SET status='rejected', review_status='rejected', last_checked_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (candidate_id,),
        )
        row = db.execute("SELECT * FROM scenic_image_candidates WHERE id=?", (candidate_id,)).fetchone()
    write_audit("景区图片审核", f"驳回图片候选 #{candidate_id}")
    return row_to_dict(row) or {"id": candidate_id, "status": "not_found"}


def approve_profile_candidate(candidate_id: int, reviewer: str = "admin"):
    with get_db() as db:
        db.execute(
            "UPDATE scenic_profile_candidates SET status='approved', reviewed_at=CURRENT_TIMESTAMP, reviewed_by=? WHERE id=?",
            (reviewer, candidate_id),
        )
        row = db.execute("SELECT * FROM scenic_profile_candidates WHERE id=?", (candidate_id,)).fetchone()
    write_audit("景区资料审核", f"通过资料候选 #{candidate_id}")
    return row_to_dict(row) or {"id": candidate_id, "status": "not_found"}


def reject_profile_candidate(candidate_id: int, reviewer: str = "admin"):
    with get_db() as db:
        db.execute(
            "UPDATE scenic_profile_candidates SET status='rejected', reviewed_at=CURRENT_TIMESTAMP, reviewed_by=? WHERE id=?",
            (reviewer, candidate_id),
        )
        row = db.execute("SELECT * FROM scenic_profile_candidates WHERE id=?", (candidate_id,)).fetchone()
    write_audit("景区资料审核", f"驳回资料候选 #{candidate_id}")
    return row_to_dict(row) or {"id": candidate_id, "status": "not_found"}


def merge_profile_candidates(scenic_id: int):
    with get_db() as db:
        result = merge_approved_candidates(db, scenic_id)
    write_audit("景区资料发布", f"合并景区 #{scenic_id} 已审核候选 {result.get('merged_count', 0)} 条")
    return result


def profile_diff(scenic_id: int):
    with get_db() as db:
        scenic = row_to_dict(db.execute("SELECT * FROM scenic_spots WHERE id=?", (scenic_id,)).fetchone())
        if not scenic:
            return {"scenic_id": scenic_id, "status": "not_found", "diffs": []}
        candidates = rows_to_list(db.execute("SELECT * FROM scenic_profile_candidates WHERE scenic_id=? AND status IN ('pending','approved') ORDER BY confidence DESC", (scenic_id,)).fetchall())
    return {"scenic": scenic, "diffs": [build_diff(scenic, candidate) for candidate in candidates]}


def _load_public_profile_rows(scenic_id: int):
    with get_db() as db:
        scenic = row_to_dict(db.execute("SELECT * FROM scenic_spots WHERE id=?", (scenic_id,)).fetchone())
        media_rows = rows_to_list(
            db.execute(
                """
                SELECT *
                FROM scenic_images
                WHERE scenic_id=? AND status='approved' AND url LIKE 'http%'
                ORDER BY is_cover DESC, quality_score DESC, id DESC
                """,
                (scenic_id,),
            ).fetchall()
        )
    return scenic, media_rows


def public_profile(scenic_id: int):
    scenic, media_rows = _load_public_profile_rows(scenic_id)
    if not scenic:
        return None
    if _needs_public_profile_refresh(scenic, media_rows):
        _refresh_public_profile_from_sources(scenic)
        scenic, media_rows = _load_public_profile_rows(scenic_id)
        if not scenic:
            return None
    media_assets = [
        {
            "url": row.get("url") or "",
            "thumbnail_url": row.get("thumbnail_url") or row.get("url") or "",
            "source": row.get("source") or row.get("provider") or "",
            "source_url": row.get("source_url") or "",
            "license": row.get("license") or "",
            "attribution": row.get("attribution") or "",
            "provider": row.get("provider") or "",
            "quality_score": row.get("quality_score") or 0,
            "last_checked_at": row.get("last_checked_at") or "",
        }
        for row in media_rows
        if (row.get("url") or "").startswith("http")
    ]
    if any(not _is_demo_image(item["url"]) for item in media_assets):
        media_assets = [item for item in media_assets if not _is_demo_image(item["url"])]
    if media_assets:
        scenic["cover_image_url"] = media_assets[0]["url"]
        scenic["gallery"] = [item["url"] for item in media_assets[:8]]
    else:
        scenic["gallery"] = scenic.get("gallery") or []
    scenic["media_assets"] = media_assets
    scenic["image_policy"] = {
        "storage": "external_url_only",
        "review": "approved_only",
        "fallback": "generated_placeholder",
        "cache": "metadata_index",
    }
    scenic["completeness_score"] = scenic.get("completeness_score") or calculate_completeness_score(scenic)
    scenic["data_source_note"] = "资料来源：官方/公开资料/后台审核"
    return scenic


def _needs_public_profile_refresh(scenic, media_rows):
    source_url = scenic.get("source_url") or ""
    cover_url = scenic.get("cover_image_url") or ""
    has_public_source = source_url.startswith("http")
    has_reviewed_media = any((row.get("url") or "").startswith("http") for row in media_rows)
    return (not has_public_source) or (not has_reviewed_media) or _is_demo_image(cover_url) or _looks_generated_coordinate(scenic)


def _is_demo_image(url):
    return any(marker in (url or "") for marker in DEMO_IMAGE_MARKERS)


def _refresh_public_profile_from_sources(scenic):
    try:
        profile_candidate, image_candidates = public_source_candidates(scenic)
    except Exception as exc:
        write_audit("景区公开资料补全", f"景区 #{scenic['id']} 公开来源补全失败：{str(exc)[:120]}")
        return {"status": "failed", "message": str(exc)[:180]}
    approved_images = [candidate for candidate in image_candidates if (candidate.get("image_url") or "").startswith("http")]
    with get_db() as db:
        if profile_candidate:
            profile_candidate["diff_json"] = json.dumps(build_diff(scenic, profile_candidate), ensure_ascii=False)
            _insert_profile_candidate(db, profile_candidate)
            latitude, longitude = _coordinates_from_candidate(profile_candidate)
            if latitude is None or longitude is None:
                latitude, longitude = KNOWN_PUBLIC_COORDINATES.get(scenic.get("name") or "", (None, None))
            coordinate_update = ""
            coordinate_params = []
            if latitude is not None and longitude is not None and _looks_generated_coordinate(scenic):
                coordinate_update = "latitude=?, longitude=?, map_point=?,"
                coordinate_params = [latitude, longitude, json.dumps({"lat": latitude, "lng": longitude}, ensure_ascii=False)]
            if coordinate_update or not (scenic.get("source_url") or "").startswith("http"):
                content = profile_candidate.get("content") or scenic.get("summary") or ""
                next_source_url = profile_candidate.get("source_url") or scenic.get("source_url") or ""
                score_preview = dict(scenic)
                score_preview.update({"summary": content, "description": content, "source_url": next_source_url})
                db.execute(
                    f"""
                    UPDATE scenic_spots
                    SET {coordinate_update}
                        summary=CASE WHEN source_url IS NULL OR source_url='' THEN ? ELSE summary END,
                        description=CASE WHEN description IS NULL OR description='' OR source_url='' THEN ? ELSE description END,
                        source_url=CASE WHEN source_url IS NULL OR source_url='' THEN ? ELSE source_url END,
                        last_enriched_at=?, completeness_score=?
                    WHERE id=?
                    """,
                    (
                        *coordinate_params,
                        content,
                        content,
                        next_source_url,
                        datetime.now().isoformat(timespec="seconds"),
                        calculate_completeness_score(score_preview),
                        scenic["id"],
                    ),
                )
        for candidate in approved_images[:8]:
            _insert_image_candidate(db, candidate)
            db.execute(
                """
                INSERT OR IGNORE INTO scenic_images (
                  scenic_id,url,thumbnail_url,status,is_cover,source,source_url,license,attribution,provider,quality_score,last_checked_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                """,
                (
                    scenic["id"],
                    candidate["image_url"],
                    candidate.get("thumbnail_url") or candidate["image_url"],
                    "approved",
                    0,
                    candidate.get("source_name") or candidate.get("source_type") or "public_source",
                    candidate.get("source_url") or "",
                    candidate.get("license") or "",
                    candidate.get("attribution") or "",
                    candidate.get("provider") or candidate.get("source_type") or "",
                    int(candidate.get("quality_score") or round(float(candidate.get("confidence") or 0) * 100)),
                ),
            )
        if approved_images and (_is_demo_image(scenic.get("cover_image_url")) or not scenic.get("cover_image_url")):
            first = approved_images[0]
            db.execute(
                "UPDATE scenic_images SET is_cover=0 WHERE scenic_id=?",
                (scenic["id"],),
            )
            db.execute(
                "UPDATE scenic_images SET is_cover=1 WHERE scenic_id=? AND url=?",
                (scenic["id"], first["image_url"]),
            )
            db.execute(
                """
                UPDATE scenic_spots
                SET cover_image_url=?, gallery=?, last_enriched_at=?
                WHERE id=?
                """,
                (
                    first["image_url"],
                    json.dumps([item["image_url"] for item in approved_images[:8]], ensure_ascii=False),
                    datetime.now().isoformat(timespec="seconds"),
                    scenic["id"],
                ),
            )
    write_audit("景区公开资料补全", f"景区 #{scenic['id']} 已按需缓存公开资料 {len(approved_images)} 张图")
    return {"status": "success", "images": len(approved_images)}


def _coordinates_from_candidate(candidate):
    try:
        raw = json.loads(candidate.get("raw_payload_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        return None, None
    coordinates = raw.get("coordinates") or []
    if not coordinates:
        return None, None
    first = coordinates[0] or {}
    latitude = first.get("lat")
    longitude = first.get("lon")
    try:
        return float(latitude), float(longitude)
    except (TypeError, ValueError):
        return None, None


def _looks_generated_coordinate(scenic):
    latitude = scenic.get("latitude")
    longitude = scenic.get("longitude")
    if latitude is None or longitude is None:
        return True
    try:
        lat = float(latitude)
        lng = float(longitude)
        rating = float(scenic.get("rating") or 0)
    except (TypeError, ValueError):
        return True
    generated_lat = round(30.0 + rating, 1)
    generated_lng = round(110.0 + rating, 1)
    return abs(lat - generated_lat) < 0.0001 and abs(lng - generated_lng) < 0.0001


def run_enrichment(scenic_id: int, task_type: str = "full"):
    return run_profile_search(scenic_id)


def tasks():
    with get_db() as db:
        return rows_to_list(db.execute(
            """
            SELECT t.*, s.name AS scenic_name FROM enrichment_tasks t
            LEFT JOIN scenic_spots s ON s.id=t.scenic_id
            ORDER BY t.id DESC LIMIT 80
            """
        ).fetchall())


def results(task_id: int):
    with get_db() as db:
        return rows_to_list(db.execute("SELECT * FROM enrichment_results WHERE task_id=? ORDER BY id", (task_id,)).fetchall())


def update_result_status(result_id: int, status: str):
    with get_db() as db:
        db.execute("UPDATE enrichment_results SET status=? WHERE id=?", (status, result_id))
    write_audit("景区资料审核", f"更新旧候选结果 #{result_id} 为 {status}")
    return {"id": result_id, "status": status}


def apply_result(result_id: int):
    with get_db() as db:
        result = db.execute("SELECT * FROM enrichment_results WHERE id=?", (result_id,)).fetchone()
        if not result:
            return {"id": result_id, "status": "not_found"}
        result = dict(result)
        db.execute("UPDATE enrichment_results SET status='approved' WHERE id=?", (result_id,))
    write_audit("景区资料审核", f"旧候选结果 #{result_id} 已审核，需通过 profile merge 发布")
    return {"id": result_id, "status": "approved", "message": "已审核，正式发布请使用资料候选合并接口"}


def _api_config(db):
    rows = db.execute("SELECT provider, enabled, api_key_secret FROM api_configs WHERE provider IN ('bing_search','bing_image','amap_web_service')").fetchall()
    return {row["provider"]: bool(row["enabled"] and row["api_key_secret"]) for row in rows}


def _insert_profile_candidate(db, candidate):
    try:
        cur = db.execute(
            """
            INSERT OR IGNORE INTO scenic_profile_candidates (
              scenic_id,candidate_type,title,content,source_url,source_name,source_type,
              confidence,risk_level,status,raw_payload_json,diff_json
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                candidate["scenic_id"], candidate["candidate_type"], candidate["title"], candidate["content"],
                candidate["source_url"], candidate["source_name"], candidate["source_type"], int(candidate["confidence"]),
                candidate["risk_level"], "pending", candidate.get("raw_payload_json", "{}"), candidate.get("diff_json", "{}"),
            ),
        )
        return cur.lastrowid if cur.rowcount else None
    except Exception:
        return None


def _insert_enrichment_result(db, task_id, candidate):
    db.execute(
        """
        INSERT INTO enrichment_results
        (task_id,scenic_id,result_type,title,url,thumbnail_url,source_name,snippet,confidence,status)
        VALUES (?,?,?,?,?,?,?,?,?,?)
        """,
        (
            task_id, candidate["scenic_id"], candidate["candidate_type"], candidate["title"],
            candidate["source_url"], "", candidate["source_name"], candidate["content"],
            round(int(candidate["confidence"]) / 100, 2), "pending",
        ),
    )


def _insert_image_candidate(db, candidate):
    image_url = candidate.get("image_url") or candidate.get("content") or candidate.get("source_url") or ""
    thumbnail_url = candidate.get("thumbnail_url") or image_url
    db.execute(
        """
        INSERT INTO scenic_image_candidates
        (scenic_id,image_url,thumbnail_url,source_url,source_name,source_type,license,attribution,provider,risk_level,status,title,confidence,quality_score,availability_status,failure_count,review_status,raw_payload_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            candidate["scenic_id"], image_url, thumbnail_url,
            candidate.get("source_url") or image_url, candidate.get("source_name") or "", candidate.get("source_type") or "",
            candidate.get("license") or "", candidate.get("attribution") or "", candidate.get("provider") or candidate.get("source_type") or "",
            candidate.get("risk_level") or "medium", candidate.get("status") or "pending", candidate.get("title") or "",
            float(candidate.get("confidence") or 0), int(candidate.get("quality_score") or 0),
            candidate.get("availability_status") or "unchecked", int(candidate.get("failure_count") or 0), candidate.get("review_status") or "pending",
            candidate.get("raw_payload_json", "{}"),
        ),
    )
