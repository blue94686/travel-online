from fastapi import APIRouter, HTTPException, Query

from app.core.config import TPT_JINGDIAN_SQL_PATH
from app.core.database import get_db
from app.core.response import ok
from app.services.nearby_recommendation_service import generate_nearby, get_nearby
from app.services.scenic_enrichment_service import public_profile
from app.services.scenic_service import count_scenic, get_scenic, get_scenic_region_options, list_scenic, list_theme_summaries
from app.services.tpt_jingdian_importer import (
    get_tpt_jingdian_status,
    import_tpt_jingdian_sql,
    search_tpt_jingdian,
)

router = APIRouter()


@router.get("/scenic")
def scenic_list(
    q: str | None = None,
    keyword: str | None = None,
    province: str | None = None,
    city: str | None = None,
    district: str | None = None,
    theme: str | None = None,
    amap: bool = False,
    limit: int = Query(80, ge=1, le=200),
    offset: int = Query(0, ge=0),
    page: int | None = Query(None, ge=1),
    sort: str | None = Query(None),
):
    # Support page-based pagination
    if page is not None:
        offset = (page - 1) * limit
    items = list_scenic(q=keyword or q, province=province, city=city, district=district, theme=theme, include_amap=amap, limit=limit, offset=offset)
    total = count_scenic(q=keyword or q, province=province, city=city, district=district, theme=theme)
    # Server-side sorting
    if sort == "rating":
        items = sorted(items, key=lambda x: x.get("rating") or 0, reverse=True)
    elif sort == "name":
        items = sorted(items, key=lambda x: x.get("name") or "")
    return ok({"items": items, "total": total, "page": page or 1, "limit": limit})


@router.get("/scenic/search")
def scenic_search(q: str = Query(""), amap: bool = Query(True)):
    return ok(list_scenic(q=q, include_amap=amap, limit=80))


@router.get("/scenic/regions")
def scenic_regions(province: str = Query(""), city: str = Query("")):
    return ok(get_scenic_region_options(province=province, city=city))


@router.get("/scenic/themes")
def scenic_themes():
    return ok(list_theme_summaries())


@router.get("/admin/scenic-source/jingdian/status")
@router.get("/scenic-source/jingdian/status")
def scenic_source_jingdian_status():
    with get_db() as db:
        return ok(get_tpt_jingdian_status(db, TPT_JINGDIAN_SQL_PATH))


@router.post("/admin/scenic-source/jingdian/import")
@router.post("/scenic-source/jingdian/import")
def scenic_source_jingdian_import(limit: int | None = Query(None, ge=1)):
    if not TPT_JINGDIAN_SQL_PATH.exists():
        raise HTTPException(status_code=404, detail="tpt_data_jingdian.sql 不存在")
    with get_db() as db:
        imported = import_tpt_jingdian_sql(db, TPT_JINGDIAN_SQL_PATH, limit=limit)
        status = get_tpt_jingdian_status(db, TPT_JINGDIAN_SQL_PATH)
        return ok({**status, "parsed_count": imported})


@router.get("/admin/scenic-source/jingdian/search")
@router.get("/scenic-source/jingdian/search")
def scenic_source_jingdian_search(
    q: str = Query(""),
    areaid: str = Query(""),
    category: str = Query(""),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with get_db() as db:
        return ok(search_tpt_jingdian(db, keyword=q, areaid=areaid, category=category, limit=limit, offset=offset))


@router.get("/scenic/{scenic_id}")
def scenic_detail(scenic_id: str):
    scenic = get_scenic(scenic_id)
    if not scenic:
        raise HTTPException(status_code=404, detail="景区不存在")
    return ok(scenic)


@router.get("/scenic/{scenic_id}/profile")
def scenic_profile(scenic_id: str):
    if scenic_id.startswith("jingdian-"):
        scenic = get_scenic(scenic_id)
    else:
        try:
            scenic = public_profile(int(scenic_id))
        except ValueError:
            scenic = None
    if not scenic:
        raise HTTPException(status_code=404, detail="景区不存在")
    return ok(scenic)


@router.get("/scenic/{scenic_id}/nearby")
def scenic_nearby(scenic_id: str):
    if scenic_id.startswith("jingdian-"):
        return ok([])
    try:
        scenic_id = int(scenic_id)
    except ValueError:
        return ok([])
    nearby = get_nearby(scenic_id)
    if not nearby:
        nearby = generate_nearby(scenic_id)
    return ok(nearby)
