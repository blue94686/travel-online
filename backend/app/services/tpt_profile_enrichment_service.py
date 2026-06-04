import json
import time
from datetime import datetime

from app.core.database import get_db, rows_to_list
from app.services.provider_config_service import get_secret
from app.services.scenic_external_enrichment_service import _amap_candidates, public_source_bundle_detailed
from app.services.tpt_jingdian_importer import ensure_tpt_jingdian_schema


GENERIC_DESC_MARKERS = (
    "后续人工资料补全",
    "可用于景区检索、主题推荐、路线规划",
    "根据景点名称、原始分类和坐标信息",
)

NATURE_TERMS = ("山", "湖", "河", "江", "海", "岛", "湿地", "森林", "峡", "谷", "瀑", "草原", "风景", "自然", "观景")
CULTURE_TERMS = ("寺", "庙", "观", "宫", "殿", "塔", "陵", "祠", "故居", "遗址", "纪念", "博物馆", "古城", "古镇", "教堂")
PARK_TERMS = ("公园", "广场", "动物园", "植物园", "水族馆", "乐园")
LEISURE_TERMS = ("温泉", "度假", "街区", "农庄", "乡村", "民俗", "商业街")
HIKING_TERMS = ("山", "峰", "岭", "峡", "谷", "森林", "步道", "栈道", "长城", "草原")
PHOTO_TERMS = ("山", "湖", "海", "古城", "古镇", "塔", "桥", "花", "瀑", "观景", "世界遗产", "5A", "4A")


def enrich_tpt_profiles_batch(limit: int = 5000, offset: int = 0, province: str = "", a_level_only: bool = True, force: bool = False) -> dict:
    limit = max(1, min(int(limit or 5000), 50000))
    offset = max(0, int(offset or 0))
    where, params = _tpt_where(province=province, a_level_only=a_level_only)

    with get_db() as db:
        ensure_tpt_jingdian_schema(db)
        total = db.execute(f"SELECT COUNT(*) AS c FROM tpt_jingdian {where}", params).fetchone()["c"]
        rows = rows_to_list(
            db.execute(
                f"SELECT * FROM tpt_jingdian {where} ORDER BY source_id ASC LIMIT ? OFFSET ?",
                params + [limit, offset],
            ).fetchall()
        )
        updated = 0
        for scenic in rows:
            patch = _build_tpt_profile_patch(scenic, force=force)
            if not patch:
                continue
            db.execute(
                f"UPDATE tpt_jingdian SET {', '.join(f'{key}=?' for key in patch)} WHERE source_id=?",
                list(patch.values()) + [scenic["source_id"]],
            )
            updated += 1

    return {
        "total": total,
        "read": len(rows),
        "updated": updated,
        "offset": offset,
        "next_offset": offset + len(rows),
        "done": offset + len(rows) >= total,
        "province": province,
        "aLevelOnly": a_level_only,
        "force": force,
    }


def enrich_tpt_profiles_all(batch_size: int = 10000, province: str = "", a_level_only: bool = True, force: bool = False) -> dict:
    offset = 0
    total_read = 0
    total_updated = 0
    last = {}
    while True:
        result = enrich_tpt_profiles_batch(
            limit=batch_size,
            offset=offset,
            province=province,
            a_level_only=a_level_only,
            force=force,
        )
        last = result
        total_read += result["read"]
        total_updated += result["updated"]
        if result["done"] or result["read"] == 0:
            break
        offset = result["next_offset"]
    return {
        "total": last.get("total", 0),
        "read": total_read,
        "updated": total_updated,
        "province": province,
        "aLevelOnly": a_level_only,
        "force": force,
    }


def enrich_tpt_media_batch(
    limit: int = 50,
    offset: int = 0,
    province: str = "",
    a_level_only: bool = True,
    only_missing: bool = True,
    sleep_seconds: float = 0.25,
    include_public_sources: bool = True,
    use_amap: bool = False,
    include_osm: bool = False,
) -> dict:
    limit = max(1, min(int(limit or 50), 200))
    offset = max(0, int(offset or 0))
    where, params = _tpt_where(province=province, a_level_only=a_level_only)
    if only_missing:
        where += " AND (cover_image_url IS NULL OR cover_image_url='') AND COALESCE(image_status, 'missing') IN ('', 'missing', 'rate_limited', 'error', 'source_unavailable', 'not_found')"

    with get_db() as db:
        ensure_tpt_jingdian_schema(db)
        total = db.execute(f"SELECT COUNT(*) AS c FROM tpt_jingdian {where}", params).fetchone()["c"]
        rows = rows_to_list(
            db.execute(
                f"""
                SELECT * FROM tpt_jingdian {where}
                ORDER BY
                  CASE official_level WHEN '5A' THEN 0 WHEN '4A' THEN 1 ELSE 2 END,
                  CASE COALESCE(image_status, 'missing')
                    WHEN 'rate_limited' THEN 0
                    WHEN 'error' THEN 1
                    WHEN 'source_unavailable' THEN 2
                    WHEN 'missing' THEN 3
                    WHEN '' THEN 3
                    ELSE 4
                  END,
                  quality_score DESC,
                  source_id ASC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()
        )
        stats = {
            "total": total,
            "read": len(rows),
            "searched": 0,
            "withImages": 0,
            "withProfiles": 0,
            "notFound": 0,
            "rateLimited": 0,
            "sourceUnavailable": 0,
            "failures": [],
            "providerFailures": [],
            "offset": offset,
            "next_offset": offset + len(rows),
            "done": offset + len(rows) >= total,
            "province": province,
            "aLevelOnly": a_level_only,
            "useAmap": use_amap,
            "includeOsm": include_osm,
        }
        for scenic in rows:
            scenic_for_source = _as_public_scenic(scenic)
            try:
                profile_candidate = None
                image_candidates = []
                provider_failures = []
                amap_key = get_secret("amap_web_service", "AMAP_WEB_SERVICE_KEY") or get_secret("amap", "AMAP_WEB_SERVICE_KEY")
                if use_amap and amap_key:
                    amap_profiles, amap_images = _amap_candidates(scenic_for_source, amap_key)
                    image_candidates.extend(amap_images)
                    amap_patch = _patch_from_amap_profiles(scenic, amap_profiles)
                    if amap_patch:
                        db.execute(
                            f"UPDATE tpt_jingdian SET {', '.join(f'{key}=?' for key in amap_patch)} WHERE source_id=?",
                            list(amap_patch.values()) + [scenic["source_id"]],
                        )

                if include_public_sources:
                    public_profiles, public_images, provider_failures = public_source_bundle_detailed(scenic_for_source, include_osm=include_osm)
                    if provider_failures:
                        stats["providerFailures"].extend(provider_failures[:4])
                    if public_profiles:
                        profile_candidate = public_profiles[0]
                        public_patch = _patch_from_public_profiles(scenic, public_profiles)
                        if public_patch:
                            db.execute(
                                f"UPDATE tpt_jingdian SET {', '.join(f'{key}=?' for key in public_patch)} WHERE source_id=?",
                                list(public_patch.values()) + [scenic["source_id"]],
                            )
                    image_candidates.extend(public_images)
                stats["searched"] += 1
                patch = {"media_checked_at": _now()}
                if profile_candidate and profile_candidate.get("content"):
                    patch.update(_profile_patch_from_candidate(scenic, profile_candidate))
                    stats["withProfiles"] += 1
                if image_candidates:
                    patch.update(_image_patch_from_candidates(image_candidates))
                    stats["withImages"] += 1
                elif _has_rate_limited_provider(provider_failures if include_public_sources else []):
                    patch["image_status"] = "rate_limited"
                    stats["rateLimited"] += 1
                elif _has_provider_failures(provider_failures if include_public_sources else []):
                    patch["image_status"] = "source_unavailable"
                    stats["sourceUnavailable"] += 1
                else:
                    patch["image_status"] = "not_found"
                    stats["notFound"] += 1
                db.execute(
                    f"UPDATE tpt_jingdian SET {', '.join(f'{key}=?' for key in patch)} WHERE source_id=?",
                    list(patch.values()) + [scenic["source_id"]],
                )
                if hasattr(db, "commit"):
                    db.commit()
            except Exception as exc:
                message = str(exc)[:180]
                status = "rate_limited" if "429" in message or "Too Many Requests" in message else "error"
                stats["failures"].append({"source_id": scenic["source_id"], "name": scenic["name"], "message": message})
                if hasattr(db, "rollback"):
                    db.rollback()
                db.execute(
                    "UPDATE tpt_jingdian SET image_status=?, media_checked_at=? WHERE source_id=?",
                    (status, _now(), scenic["source_id"]),
                )
                if hasattr(db, "commit"):
                    db.commit()
            if sleep_seconds:
                time.sleep(max(0, min(float(sleep_seconds), 2)))
    return stats


def enrich_tpt_media_all(
    batch_size: int = 50,
    max_total: int = 500,
    province: str = "",
    a_level_only: bool = True,
    only_missing: bool = True,
    sleep_seconds: float = 1.0,
    include_public_sources: bool = True,
    use_amap: bool = False,
    include_osm: bool = False,
) -> dict:
    batch_size = max(1, min(int(batch_size or 50), 200))
    max_total = max(1, min(int(max_total or 500), 10000))
    offset = 0
    total = {
        "read": 0,
        "searched": 0,
        "withImages": 0,
        "withProfiles": 0,
        "notFound": 0,
        "rateLimited": 0,
        "sourceUnavailable": 0,
        "failures": [],
        "providerFailures": [],
    }
    batches = []
    while total["read"] < max_total:
        result = enrich_tpt_media_batch(
            limit=min(batch_size, max_total - total["read"]),
            offset=offset,
            province=province,
            a_level_only=a_level_only,
            only_missing=only_missing,
            sleep_seconds=sleep_seconds,
            include_public_sources=include_public_sources,
            use_amap=use_amap,
            include_osm=include_osm,
        )
        batches.append(result)
        for key in ("read", "searched", "withImages", "withProfiles", "notFound", "rateLimited", "sourceUnavailable"):
            total[key] += result[key]
        total["failures"].extend(result["failures"])
        total["providerFailures"].extend(result.get("providerFailures") or [])
        offset = 0 if only_missing else result["next_offset"]
        if result["done"] or result["read"] == 0:
            break
    return total | {"batchSize": batch_size, "maxTotal": max_total, "province": province, "aLevelOnly": a_level_only, "useAmap": use_amap, "includeOsm": include_osm, "batches": batches}


def tpt_enrichment_stats() -> dict:
    with get_db() as db:
        ensure_tpt_jingdian_schema(db)
        row = db.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN official_level IN ('4A','5A') THEN 1 ELSE 0 END) AS a_level_total,
              SUM(CASE WHEN official_level='5A' THEN 1 ELSE 0 END) AS level_5a,
              SUM(CASE WHEN official_level='4A' THEN 1 ELSE 0 END) AS level_4a,
              SUM(CASE WHEN cover_image_url IS NOT NULL AND cover_image_url<>'' THEN 1 ELSE 0 END) AS with_cover,
              SUM(CASE WHEN cover_image_url IS NULL OR cover_image_url='' THEN 1 ELSE 0 END) AS missing_cover,
              SUM(CASE WHEN official_level IN ('4A','5A') AND cover_image_url IS NOT NULL AND cover_image_url<>'' THEN 1 ELSE 0 END) AS a_level_with_cover,
              SUM(CASE WHEN official_level IN ('4A','5A') AND (cover_image_url IS NULL OR cover_image_url='') THEN 1 ELSE 0 END) AS a_level_missing_cover,
              SUM(CASE WHEN official_level IN ('4A','5A') AND description NOT LIKE '%后续人工资料补全%' THEN 1 ELSE 0 END) AS a_level_clean_description,
              SUM(CASE WHEN profile_source IN ('维基百科','维基导游') THEN 1 ELSE 0 END) AS public_profile,
              SUM(CASE WHEN city IN ('1102地区','3102地区','1202地区') OR district IN ('1102地区','3102地区','1202地区') OR summary LIKE '%1102地区%' OR summary LIKE '%3102地区%' OR summary LIKE '%1202地区%' OR description LIKE '%1102地区%' OR description LIKE '%3102地区%' OR description LIKE '%1202地区%' THEN 1 ELSE 0 END) AS dirty_region_labels,
              SUM(CASE WHEN image_status='not_found' THEN 1 ELSE 0 END) AS image_not_found,
              SUM(CASE WHEN image_status='rate_limited' THEN 1 ELSE 0 END) AS image_rate_limited,
              SUM(CASE WHEN image_status='source_unavailable' THEN 1 ELSE 0 END) AS image_source_unavailable,
              SUM(CASE WHEN image_status='error' THEN 1 ELSE 0 END) AS image_error
            FROM tpt_jingdian
            """
        ).fetchone()
    return dict(row)


def _tpt_where(province: str = "", a_level_only: bool = True):
    where = "WHERE 1=1"
    params: list = []
    if province:
        where += " AND province=?"
        params.append(province)
    if a_level_only:
        where += " AND official_level IN ('4A','5A')"
    return where, params


def _build_tpt_profile_patch(scenic: dict, force: bool = False) -> dict:
    current_description = scenic.get("description") or ""
    current_summary = scenic.get("summary") or ""
    if not force and current_summary and current_description and not _is_generic_description(current_description):
        return {}

    name = scenic.get("name") or "该景区"
    province = scenic.get("province") or ""
    city = scenic.get("city") or ""
    district = scenic.get("district") or ""
    area = _join_area(province, city, district)
    address = scenic.get("address") or scenic.get("web_address") or ""
    category = _category(scenic)
    level = scenic.get("official_level") or scenic.get("main_category") or "景区"
    experience = _experience(scenic)
    tags = _tags(scenic, category, level)
    duration = _duration(scenic)
    best_season = _best_season(scenic)
    photo = "适合摄影取景" if _has_any(scenic, PHOTO_TERMS) else "适合记录主入口、核心景观和周边街区"
    hiking = "可按体力选择轻徒步、观景步道或外围慢行路线" if _has_any(scenic, HIKING_TERMS) else "适合短暂停留、城市漫步或周边联游"

    summary = f"{name}位于{area or '所在地'}，属于{level}目的地，核心特色偏向{category}，适合{experience}。"
    description_parts = [
        f"{name}位于{area or city or province or '当地'}{f'，地址为{address}' if address else ''}。",
        f"站内根据全国景点源表、行政区划、A 级标识、分类标签和坐标信息整理为{category}类旅游目的地。",
        f"游览上建议预留{duration}，重点关注主入口、核心游览区、游客服务点和周边交通换乘。",
        f"{hiking}；{photo}。",
        "出发前请以景区官方公告或现场公示核对开放时间、门票预约、临时闭园、天气和交通管制信息。",
    ]
    patch = {
        "summary": summary,
        "description": "".join(description_parts),
        "tags": ";".join(tags),
        "best_season": best_season,
        "audience": experience,
        "recommended_duration": duration,
        "route_idea": f"{name}主入口 -> 核心景观区 -> 周边服务点 -> 同城相邻景点联游",
        "quality_score": max(int(scenic.get("quality_score") or 0), 72 if level in ("4A", "5A") else 62),
        "profile_source": "local_rule_v2",
        "profile_source_url": scenic.get("level_source_url") or "",
        "profile_updated_at": _now(),
    }
    return patch


def _profile_patch_from_candidate(scenic: dict, candidate: dict) -> dict:
    content = (candidate.get("content") or "").strip()
    if len(content) < 24:
        return {}
    patch = {
        "profile_source": candidate.get("source_name") or candidate.get("source_type") or "public_source",
        "profile_source_url": candidate.get("source_url") or "",
        "profile_updated_at": _now(),
    }
    if _is_generic_description(scenic.get("description") or "") or len(content) > len(scenic.get("summary") or ""):
        patch["summary"] = content[:220]
        patch["description"] = content
    return patch


def _patch_from_amap_profiles(scenic: dict, candidates: list[dict]) -> dict:
    patch = {}
    raw_poi = None
    for candidate in candidates:
        raw_payload = candidate.get("raw_payload_json") or {}
        if isinstance(raw_payload, str):
            try:
                raw_payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                raw_payload = {}
        raw_poi = (raw_payload if isinstance(raw_payload, dict) else {}).get("poi") or raw_poi
        candidate_type = candidate.get("candidate_type")
        content = (candidate.get("content") or "").strip()
        if candidate_type == "address" and content:
            patch["web_address"] = content
            if not scenic.get("address"):
                patch["address"] = content
        if candidate_type == "opening_hours" and content:
            patch["web_update_note"] = f"高德开放时间候选：{content[:80]}"
        if candidate_type == "phone" and content and not scenic.get("phone"):
            patch["phone"] = content
    if raw_poi:
        if raw_poi.get("id"):
            patch["poiid"] = raw_poi.get("id")
        location = raw_poi.get("location") or ""
        if "," in location:
            lng, lat = location.split(",", 1)
            try:
                patch["longitude"] = float(lng)
                patch["latitude"] = float(lat)
                patch["web_longitude"] = float(lng)
                patch["web_latitude"] = float(lat)
            except ValueError:
                pass
        patch["web_source_confidence"] = "amap"
    return patch


def _patch_from_public_profiles(scenic: dict, candidates: list[dict]) -> dict:
    patch = {}
    notes = []
    for candidate in candidates:
        candidate_type = candidate.get("candidate_type")
        source_type = candidate.get("source_type") or "public_source"
        content = (candidate.get("content") or "").strip()
        if not content:
            continue
        if candidate_type == "address" and not (scenic.get("web_address") or scenic.get("address")):
            patch["web_address"] = content[:240]
        elif candidate_type == "opening_hours":
            notes.append(f"{source_type}开放时间：{content[:80]}")
        elif candidate_type == "official_site" and not scenic.get("profile_source_url"):
            patch["profile_source_url"] = content[:240]
        elif candidate_type == "coordinate":
            try:
                point = json.loads(content)
                lat = float(point.get("latitude"))
                lng = float(point.get("longitude"))
                patch["web_latitude"] = lat
                patch["web_longitude"] = lng
                if not scenic.get("latitude"):
                    patch["latitude"] = lat
                if not scenic.get("longitude"):
                    patch["longitude"] = lng
            except (TypeError, ValueError, json.JSONDecodeError):
                continue
        elif candidate_type in {"traffic", "tips"} and "徒步" in content and not scenic.get("route_idea"):
            patch["route_idea"] = f"{scenic.get('name') or '景区'}主入口 -> 核心景观 -> OSM 徒步/慢行路线候选 -> 返回游客服务点"
            notes.append(content[:120])
    if notes:
        patch["web_update_note"] = "；".join(notes)[:260]
    if patch:
        patch["web_source_confidence"] = "public_sources"
    return patch


def _image_patch_from_candidates(candidates: list[dict]) -> dict:
    clean = [item for item in candidates if item.get("image_url")]
    cover = clean[0]
    gallery = []
    for item in clean[:6]:
        if item["image_url"] not in gallery:
            gallery.append(item["image_url"])
    return {
        "cover_image_url": cover["image_url"],
        "gallery": json.dumps(gallery, ensure_ascii=False),
        "image_source": cover.get("source_name") or cover.get("source_type") or "",
        "image_source_url": cover.get("source_url") or "",
        "image_license": cover.get("license") or "",
        "image_attribution": cover.get("attribution") or "",
        "image_status": "approved_external_url",
    }


def _as_public_scenic(scenic: dict) -> dict:
    return {
        "id": scenic.get("source_id"),
        "name": scenic.get("name"),
        "province": scenic.get("province") or "",
        "city": scenic.get("city") or "",
        "district": scenic.get("district") or "",
        "address": scenic.get("address") or scenic.get("web_address") or "",
        "latitude": scenic.get("latitude") or scenic.get("web_latitude"),
        "longitude": scenic.get("longitude") or scenic.get("web_longitude"),
        "web_latitude": scenic.get("web_latitude"),
        "web_longitude": scenic.get("web_longitude"),
        "summary": scenic.get("summary") or "",
        "description": scenic.get("description") or "",
        "tags": json.dumps(_tags(scenic, _category(scenic), scenic.get("official_level") or ""), ensure_ascii=False),
    }


def _is_generic_description(value: str) -> bool:
    text = str(value or "")
    return not text.strip() or any(marker in text for marker in GENERIC_DESC_MARKERS)


def _join_area(province: str, city: str, district: str) -> str:
    parts = []
    for part in (province, city, district):
        if part and part not in parts:
            parts.append(part)
    return "".join(parts)


def _category(scenic: dict) -> str:
    text = " ".join(str(scenic.get(key) or "") for key in ("name", "category_path", "category", "main_category", "theme_names", "tags"))
    if _has_any_text(text, CULTURE_TERMS):
        return "历史文化"
    if _has_any_text(text, PARK_TERMS):
        return "公园休闲"
    if _has_any_text(text, NATURE_TERMS):
        return "自然风光"
    if _has_any_text(text, LEISURE_TERMS):
        return "休闲度假"
    return scenic.get("main_category") or "本地旅游"


def _experience(scenic: dict) -> str:
    category = _category(scenic)
    if category == "历史文化":
        return "人文探访、研学旅行、建筑摄影和城市漫步"
    if category == "公园休闲":
        return "亲子休闲、轻量运动、周末散步和城市放松"
    if category == "自然风光":
        return "自然观光、摄影打卡、徒步休闲和自驾联游"
    if category == "休闲度假":
        return "家庭短途、朋友出游、休闲度假和周边联游"
    return "城市探索、路线途经、周边游和轻量打卡"


def _duration(scenic: dict) -> str:
    if scenic.get("official_level") == "5A":
        return "4-8 小时"
    if scenic.get("official_level") == "4A":
        return "2-5 小时"
    if _has_any(scenic, HIKING_TERMS):
        return "3-5 小时"
    return "1-3 小时"


def _best_season(scenic: dict) -> str:
    text = " ".join(str(scenic.get(key) or "") for key in ("name", "category_path", "theme_names", "tags"))
    if any(term in text for term in ("海", "湖", "水", "瀑", "湿地")):
        return "春夏秋季"
    if any(term in text for term in ("山", "森林", "峡", "谷", "长城")):
        return "春季、秋季"
    if any(term in text for term in CULTURE_TERMS):
        return "四季皆宜，春秋更舒适"
    return scenic.get("best_season") or "四季皆宜"


def _tags(scenic: dict, category: str, level: str) -> list[str]:
    tags = []
    if level:
        tags.append(level)
    tags.append(category)
    if _has_any(scenic, HIKING_TERMS):
        tags.append("徒步")
    if _has_any(scenic, PHOTO_TERMS):
        tags.append("摄影")
    if scenic.get("city"):
        tags.append("城市周边")
    seen = []
    for tag in tags:
        if tag and tag not in seen:
            seen.append(tag)
    return seen[:6]


def _has_any(scenic: dict, terms: tuple[str, ...]) -> bool:
    text = " ".join(str(scenic.get(key) or "") for key in ("name", "category_path", "category", "main_category", "theme_names", "tags", "summary"))
    return _has_any_text(text, terms)


def _has_any_text(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _has_rate_limited_provider(failures: list[dict]) -> bool:
    return any((item.get("status") == "rate_limited") for item in failures or [])


def _has_provider_failures(failures: list[dict]) -> bool:
    return bool(failures)


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
