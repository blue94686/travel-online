from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.core.database import get_db, row_to_dict, rows_to_list
from app.core.response import ok

router = APIRouter()

CATEGORIES = [
    {"key": "all", "label": "全部"},
    {"key": "scenic_official", "label": "景区官方"},
    {"key": "city_live", "label": "城市实况"},
    {"key": "nature_live", "label": "自然风景"},
    {"key": "weather_earth", "label": "天气地球"},
    {"key": "satellite_earth", "label": "卫星地球"},
    {"key": "space_earth", "label": "太空视角"},
    {"key": "map_poi", "label": "地图 POI"},
    {"key": "global_featured", "label": "全球精选"},
]


class EarthFavoritePayload(BaseModel):
    source_id: int
    user_id: int = 1


def with_can_embed(item):
    if not item:
        return item
    item["is_live"] = bool(item.get("is_live"))
    item["is_embeddable"] = bool(item.get("is_embeddable"))
    item["can_embed"] = bool(
        item["is_embeddable"]
        and item.get("embed_url")
        and item.get("review_status") == "approved"
        and item.get("availability_status") == "online"
    )
    return item


def approved_sources_sql(category=None, keyword=None, platform=None, country=None, city=None, is_live=None, availability_status=None):
    sql = "SELECT * FROM earth_online_sources WHERE review_status='approved' AND risk_level='low' AND source_url!=''"
    params = []
    if category and category != "all":
        sql += " AND category=?"
        params.append(category)
    if keyword:
        sql += " AND (name LIKE ? OR description LIKE ? OR source_platform LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like])
    if platform:
        sql += " AND source_platform LIKE ?"
        params.append(f"%{platform}%")
    if country:
        sql += " AND country LIKE ?"
        params.append(f"%{country}%")
    if city:
        sql += " AND city LIKE ?"
        params.append(f"%{city}%")
    if is_live is not None:
        sql += " AND is_live=?"
        params.append(1 if is_live else 0)
    if availability_status:
        sql += " AND availability_status=?"
        params.append(availability_status)
    sql += " ORDER BY category, id"
    return sql, params


@router.get("/earth-online/sources")
def sources(
    category: str | None = None,
    keyword: str | None = None,
    platform: str | None = None,
    country: str | None = None,
    city: str | None = None,
    is_live: bool | None = Query(default=None),
    availability_status: str | None = None,
):
    sql, params = approved_sources_sql(category, keyword, platform, country, city, is_live, availability_status)
    with get_db() as db:
        return ok([with_can_embed(item) for item in rows_to_list(db.execute(sql, params).fetchall())])


@router.get("/earth-online/sources/{source_id}")
def source_detail(source_id: int):
    with get_db() as db:
        item = row_to_dict(db.execute(
            "SELECT * FROM earth_online_sources WHERE id=? AND review_status='approved' AND risk_level='low'",
            (source_id,),
        ).fetchone())
    return ok(with_can_embed(item))


@router.get("/earth-online/categories")
def categories():
    return ok(CATEGORIES)


@router.get("/earth-online/featured")
def featured():
    sql, params = approved_sources_sql("global_featured")
    with get_db() as db:
        return ok([with_can_embed(item) for item in rows_to_list(db.execute(sql, params).fetchall())])


@router.get("/earth-online/stats")
def stats():
    with get_db() as db:
        row = db.execute(
            """
            SELECT
              SUM(CASE WHEN review_status='approved' THEN 1 ELSE 0 END) AS approved,
              COUNT(DISTINCT category) AS categories,
              SUM(CASE WHEN availability_status='online' THEN 1 ELSE 0 END) AS online,
              SUM(CASE WHEN is_embeddable=0 THEN 1 ELSE 0 END) AS external_only
            FROM earth_online_sources
            """
        ).fetchone()
    return ok(row_to_dict(row) | {"lastChecked": "按需检测"})


@router.get("/user/earth-online/favorites")
def earth_favorites(user_id: int = 1):
    with get_db() as db:
        rows = rows_to_list(db.execute(
            """
            SELECT s.* FROM earth_online_favorites f
            JOIN earth_online_sources s ON s.id=f.source_id
            WHERE f.user_id=? ORDER BY f.id DESC
            """,
            (user_id,),
        ).fetchall())
    return ok([with_can_embed(item) for item in rows])


@router.post("/user/earth-online/favorites")
def add_earth_favorite(payload: EarthFavoritePayload):
    with get_db() as db:
        db.execute("INSERT OR IGNORE INTO earth_online_favorites (user_id, source_id) VALUES (?,?)", (payload.user_id, payload.source_id))
    return ok({"source_id": payload.source_id, "status": "saved"}, "来源已收藏")


@router.delete("/user/earth-online/favorites/{source_id}")
def remove_earth_favorite(source_id: int, user_id: int = 1):
    with get_db() as db:
        db.execute("DELETE FROM earth_online_favorites WHERE user_id=? AND source_id=?", (user_id, source_id))
    return ok({"source_id": source_id}, "来源收藏已取消")
