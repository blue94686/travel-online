import json

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.database import get_db, rows_to_list
from app.core.response import ok
from app.services.scenic_service import create_scenic
from app.services.audit_service import write_audit
from app.services.scenic_enrichment_service import run_profile_search

router = APIRouter()


class ScenicPayload(BaseModel):
    name: str
    slug: str
    province: str = "浙江省"
    city: str = "杭州市"
    district: str = "西湖区"
    level: str = "4A"
    rating: float = 4.5
    address: str = ""
    latitude: float = 30.0
    longitude: float = 120.0
    summary: str = ""
    description: str = ""
    tags: list[str] = []
    ticket_price: str = "以景区公示为准"
    opening_hours: str = "08:00-17:30"
    best_season: str = "春秋两季"
    cover_image_url: str = ""
    gallery: list[str] = []
    weather: dict = {}
    map_point: dict = {}
    nearby_pois: list[str] = []
    recommended_routes: list[str] = []


@router.get("/admin/scenic")
def admin_scenic_list(
    q: str | None = None,
    keyword: str | None = None,
    province: str | None = None,
    city: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    sql = "SELECT * FROM scenic_spots WHERE 1=1"
    count_sql = "SELECT COUNT(*) c FROM scenic_spots WHERE 1=1"
    params = []
    search = q or keyword
    if search:
        clause = " AND (name LIKE ? OR province LIKE ? OR city LIKE ? OR district LIKE ?)"
        sql += clause
        count_sql += clause
        like = f"%{search}%"
        params.extend([like, like, like, like])
    if province:
        sql += " AND province = ?"
        count_sql += " AND province = ?"
        params.append(province)
    if city:
        sql += " AND city = ?"
        count_sql += " AND city = ?"
        params.append(city)
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)
    sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
    with get_db() as db:
        total = db.execute(count_sql, params).fetchone()["c"]
        rows = rows_to_list(db.execute(sql, [*params, limit, offset]).fetchall())
        return ok({"list": rows, "total": total, "limit": limit, "offset": offset})


@router.post("/admin/scenic")
def admin_scenic_create(payload: ScenicPayload):
    data = payload.model_dump()
    for key in ("tags", "gallery", "weather", "map_point", "nearby_pois", "recommended_routes"):
        data[key] = json.dumps(data[key], ensure_ascii=False)
    created = create_scenic(data)
    write_audit("景区管理", f"新增景区 {created['name']}")
    return ok(created, "景区已创建")


@router.put("/admin/scenic/{scenic_id}")
def admin_scenic_update(scenic_id: int, payload: ScenicPayload):
    data = payload.model_dump()
    for key in ("tags", "gallery", "weather", "map_point", "nearby_pois", "recommended_routes"):
        data[key] = json.dumps(data[key], ensure_ascii=False)
    with get_db() as db:
        db.execute(
            """
            UPDATE scenic_spots SET slug=?,name=?,province=?,city=?,district=?,level=?,rating=?,address=?,
            latitude=?,longitude=?,summary=?,description=?,tags=?,ticket_price=?,opening_hours=?,
            best_season=?,cover_image_url=?,gallery=?,weather=?,map_point=?,nearby_pois=?,recommended_routes=?
            WHERE id=?
            """,
            (
                data["slug"], data["name"], data["province"], data["city"], data["district"], data["level"], data["rating"],
                data["address"], data["latitude"], data["longitude"], data["summary"], data["description"], data["tags"],
                data["ticket_price"], data["opening_hours"], data["best_season"], data["cover_image_url"], data["gallery"],
                data["weather"], data["map_point"], data["nearby_pois"], data["recommended_routes"], scenic_id,
            ),
        )
    write_audit("景区管理", f"编辑景区 #{scenic_id}")
    return ok({"id": scenic_id}, "景区已更新")


@router.delete("/admin/scenic/{scenic_id}")
def admin_scenic_delete(scenic_id: int):
    with get_db() as db:
        db.execute("DELETE FROM scenic_spots WHERE id=?", (scenic_id,))
    write_audit("景区管理", f"删除景区 #{scenic_id}")
    return ok({"id": scenic_id}, "景区已删除")


@router.post("/admin/scenic/{scenic_id}/enrich")
def admin_scenic_enrich(scenic_id: int):
    result = run_profile_search(scenic_id)
    write_audit("景区资料补全", f"生成景区 #{scenic_id} 待审核资料候选")
    return ok(result, "景区资料候选已生成，审核通过前不会覆盖正式数据")
