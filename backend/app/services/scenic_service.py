import json
from pathlib import Path

from app.core.database import get_db, row_to_dict, rows_to_list
from app.core.region_utils import is_fallback_area_label, label_area, normalize_region_name, resolve_areaid
from app.services.amap_service import amap_marker_url, search_amap_pois
from app.services.theme_catalog import THEME_BY_NAME, THEME_TERMS
from app.services.tpt_jingdian_importer import search_tpt_jingdian


def _theme_terms(theme):
    theme = (theme or "").strip()
    if not theme:
        return []
    if theme in THEME_TERMS:
        return THEME_TERMS[theme]
    for item in THEME_BY_NAME.values():
        if item["slug"] == theme:
            return item["keywords"]
    return [theme]


def _append_like_terms(sql, params, columns, terms):
    terms = [term for term in terms if term]
    if not terms:
        return sql
    clauses = []
    for term in terms:
        like = f"%{term}%"
        column_clauses = []
        for column in columns:
            column_clauses.append(f"{column} LIKE ?")
            params.append(like)
        clauses.append("(" + " OR ".join(column_clauses) + ")")
    return sql + " AND (" + " OR ".join(clauses) + ")"


def _like_where(columns, terms, prefix=""):
    terms = [term for term in terms if term]
    if not terms:
        return "", []
    params = []
    clauses = []
    for term in terms:
        like = f"%{term}%"
        column_clauses = [f"{prefix}{column} LIKE ?" for column in columns]
        params.extend([like] * len(columns))
        clauses.append("(" + " OR ".join(column_clauses) + ")")
    return "(" + " OR ".join(clauses) + ")", params


def _scenic_filter_sql(columns, q=None, province=None, city=None, district=None, theme=None):
    sql = " FROM scenic_spots WHERE 1=1"
    params = []
    if q:
        sql += " AND (name LIKE ? OR province LIKE ? OR city LIKE ? OR district LIKE ? OR tags LIKE ? OR summary LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like, like, like, like])
    if province:
        if "normalized_province" in columns:
            sql += " AND (province = ? OR normalized_province = ?)"
            params.extend([province, province])
        else:
            sql += " AND province = ?"
            params.append(province)
    if city:
        if "normalized_city" in columns:
            sql += " AND (city = ? OR normalized_city = ?)"
            params.extend([city, city])
        else:
            sql += " AND city = ?"
            params.append(city)
    if district:
        if "normalized_district" in columns:
            sql += " AND (district = ? OR normalized_district = ?)"
            params.extend([district, district])
        else:
            sql += " AND district = ?"
            params.append(district)
    theme_terms = _theme_terms(theme)
    if theme_terms:
        sql = _append_like_terms(sql, params, ["name", "level", "tags", "summary", "description"], theme_terms)
    return sql, params, theme_terms


def list_scenic(
    q: str | None = None,
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    theme: str | None = None,
    include_amap: bool = False,
    limit: int = 80,
    offset: int = 0,
):
    province = normalize_region_name(province)
    city = normalize_region_name(city)
    district = normalize_region_name(district)
    limit = max(1, min(int(limit or 80), 200))
    offset = max(0, int(offset or 0))
    with get_db() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(scenic_spots)").fetchall()}
        filter_sql, params, theme_terms = _scenic_filter_sql(
            columns, q=q, province=province, city=city, district=district, theme=theme
        )
        scenic_total = db.execute("SELECT COUNT(*) AS c" + filter_sql, params).fetchone()["c"]
        items = []
        scenic_limit = max(0, min(limit, scenic_total - offset)) if offset < scenic_total else 0
        if scenic_limit:
            sql = "SELECT *" + filter_sql + " ORDER BY rating DESC, id ASC LIMIT ? OFFSET ?"
            items = rows_to_list(db.execute(sql, [*params, scenic_limit, offset]).fetchall())
        keyword = (q or "").strip()
        category = " ".join(theme_terms)
        areaid = resolve_areaid(province=province, city=city, district=district)
        remaining = max(0, limit - len(items))
        if remaining:
            tpt_offset = 0 if offset < scenic_total else offset - scenic_total
            tpt_result = search_tpt_jingdian(
                db,
                keyword=keyword,
                areaid=areaid,
                province=province,
                city=city,
                district=district,
                category=category,
                limit=remaining,
            )
            items.extend(_normalize_tpt_item(row) for row in tpt_result["items"])
    remaining = max(0, limit - len(items))
    if remaining and include_amap and (q or "").strip():
        amap_result = search_amap_pois(q, city=city or province or "", limit=min(10, remaining))
        items.extend(amap_result.get("items", []))
    return items[:limit]


def count_scenic(q=None, province=None, city=None, district=None, theme=None):
    province = normalize_region_name(province)
    city = normalize_region_name(city)
    district = normalize_region_name(district)
    with get_db() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(scenic_spots)").fetchall()}
        filter_sql, params, _ = _scenic_filter_sql(
            columns, q=q, province=province, city=city, district=district, theme=theme
        )
        scenic_count = db.execute("SELECT COUNT(*) AS c" + filter_sql, params).fetchone()["c"]
        terms = _theme_terms(theme)
        areaid = resolve_areaid(province=province, city=city, district=district)
        tpt_count = search_tpt_jingdian(
            db,
            keyword=(q or "").strip(),
            areaid=areaid,
            province=province,
            city=city,
            district=district,
            category=" ".join(terms),
            limit=1,
        )["total"]
        return scenic_count + tpt_count


def _count_tpt_theme_rows(db, terms):
    where_sql, params = _like_where(["name", "address", "category_path", "category", "search_text"], terms)
    if not where_sql:
        return 0
    return db.execute(f"SELECT COUNT(*) AS c FROM tpt_jingdian WHERE {where_sql}", params).fetchone()["c"]


def _count_scenic_themes(db):
    selects = []
    params = []
    for index, name in enumerate(THEME_TERMS):
        where_sql, where_params = _like_where(["name", "level", "tags", "summary", "description"], _theme_terms(name))
        selects.append(f"SUM(CASE WHEN {where_sql} THEN 1 ELSE 0 END) AS c{index}")
        params.extend(where_params)
    row = db.execute("SELECT " + ", ".join(selects) + " FROM scenic_spots", params).fetchone()
    return {name: row[f"c{index}"] or 0 for index, name in enumerate(THEME_TERMS)}


def _theme_catalog_rows(db):
    has_table = db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='scenic_themes'"
    ).fetchone()
    if not has_table:
        return []
    return db.execute(
        """
        SELECT *
        FROM scenic_themes
        WHERE is_active=1
        ORDER BY sort_order ASC, id ASC
        """
    ).fetchall()


def _parse_keywords(value):
    try:
        payload = json.loads(value or "[]")
    except json.JSONDecodeError:
        payload = []
    return payload if isinstance(payload, list) else []


def _theme_metadata(row, name):
    if row:
        return {
            "slug": row["slug"],
            "name": row["name"],
            "description": row["description"] or "",
            "guide": row["guide"] or "",
            "image": row["image_url"] or "",
            "icon": row["icon"] or "",
            "keywords": _parse_keywords(row["keywords_json"]),
            "season": row["season"] or "",
            "audience": row["audience"] or "",
            "routeIdea": row["route_idea"] or "",
        }
    fallback = THEME_BY_NAME.get(name, {})
    return {
        "slug": fallback.get("slug", name),
        "name": name,
        "description": fallback.get("description", ""),
        "guide": fallback.get("guide", ""),
        "image": fallback.get("image_url", ""),
        "icon": fallback.get("icon", ""),
        "keywords": fallback.get("keywords", _theme_terms(name)),
        "season": fallback.get("season", ""),
        "audience": fallback.get("audience", ""),
        "routeIdea": fallback.get("route_idea", ""),
    }


def list_theme_summaries():
    with get_db() as db:
        scenic_columns = {row["name"] for row in db.execute("PRAGMA table_info(scenic_spots)").fetchall()}
        include_tpt_directly = "source_url" not in scenic_columns
        scenic_counts = _count_scenic_themes(db)
        summaries = []
        catalog_rows = _theme_catalog_rows(db)
        rows_by_name = {row["name"]: row for row in catalog_rows}
        names = [row["name"] for row in catalog_rows] or list(THEME_TERMS)
        for name in names:
            terms = _theme_terms(name)
            scenic_count = scenic_counts.get(name, 0)
            tpt_count = _count_tpt_theme_rows(db, terms) if include_tpt_directly else 0
            summaries.append(
                {
                    **_theme_metadata(rows_by_name.get(name), name),
                    "count": scenic_count + tpt_count,
                    "terms": terms,
                }
            )
        return summaries

def get_scenic_region_options(province="", city=""):
    province = normalize_region_name(province)
    city = normalize_region_name(city)
    province_prefix = resolve_areaid(province=province)
    city_prefix = resolve_areaid(city=city)
    with get_db() as db:
        province_rows = db.execute(
            """
            SELECT substr(areaid, 1, 2) AS code, COUNT(*) AS count
            FROM tpt_jingdian
            WHERE areaid != ''
            GROUP BY code
            ORDER BY count DESC, code ASC
            """
        ).fetchall()
        provinces = [label for row in province_rows if not is_fallback_area_label(label := label_area(row["code"], 2))]
        cities = []
        districts = []
        if province_prefix:
            city_rows = db.execute(
                """
                SELECT substr(areaid, 1, 4) AS code, COUNT(*) AS count
                FROM tpt_jingdian
                WHERE areaid LIKE ? AND length(areaid) >= 4
                GROUP BY code
                ORDER BY count DESC, code ASC
                """,
                (f"{province_prefix[:2]}%",),
            ).fetchall()
            cities = [label for row in city_rows if not is_fallback_area_label(label := label_area(row["code"], 4))]
        if city_prefix:
            district_rows = db.execute(
                """
                SELECT substr(areaid, 1, 6) AS code, COUNT(*) AS count
                FROM tpt_jingdian
                WHERE areaid LIKE ? AND length(areaid) >= 6
                GROUP BY code
                ORDER BY count DESC, code ASC
                """,
                (f"{city_prefix[:4]}%",),
            ).fetchall()
            districts = [label for row in district_rows if not is_fallback_area_label(label := label_area(row["code"], 6))]
        return {"provinces": provinces, "cities": cities, "districts": districts}


def _label_area(code, size):
    return label_area(code, size)


def _resolve_areaid(province=None, city=None, district=None):
    return resolve_areaid(province=province, city=city, district=district)


def _normalize_tpt_item(row):
    tags = [part.strip() for part in (row.get("category_path") or "").split(";") if part.strip()]
    longitude = row.get("longitude")
    latitude = row.get("latitude")
    name = row.get("name") or "全国景点"
    province_code = row.get("province_code") or ""
    city_code = row.get("city_code") or ""
    district_code = row.get("district_code") or ""
    gallery = row.get("gallery") or []
    if isinstance(gallery, str):
        try:
            gallery = json.loads(gallery)
        except json.JSONDecodeError:
            gallery = [part.strip() for part in gallery.split(";") if part.strip()]
    if not isinstance(gallery, list):
        gallery = []
    cover_image_url = row.get("cover_image_url") or (gallery[0] if gallery else "")
    return {
        "id": f"jingdian-{row.get('source_id')}",
        "source": "jingdian",
        "source_id": row.get("source_id"),
        "name": name,
        "province": row.get("province") or (label_area(province_code, 2) if province_code else ""),
        "city": row.get("city") or (label_area(city_code, 4) if city_code else ""),
        "district": row.get("district") or (label_area(district_code, 6) if district_code else ""),
        "level": row.get("official_level") or row.get("main_category") or "全国景点",
        "rating": 4.4,
        "address": row.get("address") or "地址待补充",
        "latitude": latitude,
        "longitude": longitude,
        "summary": row.get("summary") or f"{row.get('category_path') or '风景名胜'} · 全国景点数据源",
        "description": row.get("description") or f"{name} 来自全国景点源表，可用于三级浏览、路线规划和资料补全候选审核。",
        "tags": tags[-4:] if tags else ["风景名胜"],
        "ticket_price": "以景区公示为准",
        "opening_hours": "以景区公示为准",
        "best_season": "四季皆宜",
        "cover_image_url": cover_image_url,
        "gallery": gallery,
        "image_source": row.get("image_source") or "",
        "image_source_url": row.get("image_source_url") or "",
        "image_license": row.get("image_license") or "",
        "image_attribution": row.get("image_attribution") or "",
        "image_status": row.get("image_status") or "missing",
        "media_checked_at": row.get("media_checked_at") or "",
        "profile_source": row.get("profile_source") or "",
        "profile_source_url": row.get("profile_source_url") or "",
        "profile_updated_at": row.get("profile_updated_at") or "",
        "weather": {},
        "map_point": {"longitude": longitude, "latitude": latitude},
        "nearby_pois": [],
        "recommended_routes": [],
        "source_url": row.get("level_source_url") or f"local-sql:tpt_data_jingdian:{row.get('source_id')}",
        "data_quality": row.get("quality_score") or 0,
        "recommended_duration": row.get("recommended_duration") or "",
        "best_season": row.get("best_season") or "四季皆宜",
        "poiid": row.get("poiid") or "",
        "areaid": row.get("areaid") or "",
        "map_url": amap_marker_url(name, longitude, latitude),
    }


def _source_id_from_public_id(value):
    text = str(value or "")
    if text.startswith("jingdian-") and text.removeprefix("jingdian-").isdigit():
        return int(text.removeprefix("jingdian-"))
    return None


def get_scenic_source_detail(public_id):
    source_id = _source_id_from_public_id(public_id)
    if source_id is None:
        return None
    with get_db() as db:
        row = db.execute("SELECT * FROM tpt_jingdian WHERE source_id = ?", (source_id,)).fetchone()
    return _normalize_tpt_item(dict(row)) if row else None


def get_scenic(scenic_id):
    if _source_id_from_public_id(scenic_id) is not None:
        return get_scenic_source_detail(scenic_id)
    source_detail = get_scenic_source_detail(scenic_id)
    if source_detail:
        return source_detail
    with get_db() as db:
        return row_to_dict(db.execute("SELECT * FROM scenic_spots WHERE id = ?", (scenic_id,)).fetchone())


def create_scenic(payload: dict):
    fields = ["slug", "name", "province", "city", "district", "level", "rating", "address", "latitude", "longitude", "summary", "description", "tags", "ticket_price", "opening_hours", "best_season", "cover_image_url", "gallery", "weather", "map_point", "nearby_pois", "recommended_routes"]
    values = [payload.get(field, "" if field not in ("rating", "latitude", "longitude") else 0) for field in fields]
    with get_db() as db:
        cur = db.execute(f"INSERT INTO scenic_spots ({','.join(fields)}) VALUES ({','.join(['?'] * len(fields))})", values)
        return get_scenic(cur.lastrowid)
