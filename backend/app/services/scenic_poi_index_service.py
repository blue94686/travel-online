import json
from datetime import datetime
from urllib.parse import urlencode

from app.core.database import get_db, row_to_dict, rows_to_list
from app.services.audit_service import write_audit
from app.services.scenic_quality_score_service import calculate_completeness_score
from app.services.theme_catalog import THEME_CATALOG


POI_GROUPS = [
    ("traffic", "交通换乘", [
        ("bus_station", "公交站", "公交站"),
        ("subway_station", "地铁站", "地铁站"),
        ("parking", "停车场", "停车场"),
    ]),
    ("food", "餐饮美食", [
        ("restaurant", "餐厅", "餐厅"),
        ("cafe", "咖啡厅", "咖啡厅"),
        ("snack_street", "小吃街", "小吃街 夜市"),
    ]),
    ("stay", "住宿营地", [
        ("hotel", "酒店", "酒店"),
        ("homestay", "民宿", "民宿"),
        ("campground", "露营地", "露营地"),
    ]),
    ("shopping", "购物补给", [
        ("mall", "商场", "商场"),
        ("supermarket", "超市", "超市"),
        ("specialty_store", "特产店", "特产店"),
    ]),
    ("scenic", "周边游览", [
        ("nearby_scenic", "其他景区", "景区"),
        ("viewpoint", "观景台", "观景台"),
        ("park", "公园", "公园"),
    ]),
    ("hiking", "徒步补给", [
        ("trailhead", "步道入口", "步道入口"),
        ("supply_point", "补给点", "补给点 便利店"),
        ("trail_camp", "营地", "营地"),
    ]),
]

FOOD_CATEGORIES = {"restaurant", "cafe", "snack_street"}
HOTEL_CATEGORIES = {"hotel", "homestay", "campground"}


def backfill_theme_poi_index(limit: int = 1000, province: str = "", city: str = "", force: bool = False) -> dict:
    limit = max(1, min(int(limit or 1000), 50000))
    updated = 0
    skipped = 0
    poi_items = 0
    with get_db() as db:
        rows = _select_scenics(db, limit, province, city, force)
        for scenic in rows:
            patch = build_theme_poi_patch(scenic)
            if not patch["nearby_pois"]:
                skipped += 1
                continue
            db.execute(
                """
                UPDATE scenic_spots
                SET nearby_pois=?, nearby_food=?, nearby_hotels=?, recommended_routes=?,
                    travel_tips=?, traffic_info=?, public_transport=?, parking_info=?,
                    self_driving_route=?, last_enriched_at=?, completeness_score=?
                WHERE id=?
                """,
                (
                    _json(patch["nearby_pois"]),
                    _json(patch["nearby_food"]),
                    _json(patch["nearby_hotels"]),
                    _json(patch["recommended_routes"]),
                    _json(patch["travel_tips"]),
                    patch["traffic_info"],
                    patch["public_transport"],
                    patch["parking_info"],
                    patch["self_driving_route"],
                    _now(),
                    calculate_completeness_score(row_to_dict(scenic) | patch),
                    scenic["id"],
                ),
            )
            updated += 1
            poi_items += len(patch["nearby_pois"]) + len(patch["nearby_food"]) + len(patch["nearby_hotels"])
    _safe_audit("主题POI补全", f"补齐主题 POI：景区 {updated}，POI 索引 {poi_items}，跳过 {skipped}")
    return {"updated": updated, "skipped": skipped, "poiItems": poi_items, "read": updated + skipped}


def poi_index_stats() -> dict:
    with get_db() as db:
        row = db.execute(
            """
            SELECT
              COUNT(*) AS totalScenic,
              SUM(CASE WHEN nearby_pois IS NULL OR nearby_pois='' OR nearby_pois='[]' THEN 1 ELSE 0 END) AS missingNearbyPois,
              SUM(CASE WHEN nearby_food IS NULL OR nearby_food='' OR nearby_food='[]' THEN 1 ELSE 0 END) AS missingFoodPois,
              SUM(CASE WHEN nearby_hotels IS NULL OR nearby_hotels='' OR nearby_hotels='[]' THEN 1 ELSE 0 END) AS missingStayPois,
              SUM(CASE WHEN nearby_pois LIKE '%bus_station%' AND nearby_pois LIKE '%trailhead%' THEN 1 ELSE 0 END) AS fullPoiIndex
            FROM scenic_spots
            """
        ).fetchone()
    return _canonical_stats(dict(row or {}))


def build_theme_poi_patch(scenic: dict) -> dict:
    scenic = row_to_dict(scenic) or scenic
    name = scenic.get("name") or "景区"
    area = " ".join(part for part in [scenic.get("province"), scenic.get("city"), scenic.get("district")] if part)
    themes = _matched_themes(scenic)
    items = []
    for group_key, group_name, categories in POI_GROUPS:
        for category, label, keyword in categories:
            query = f"{name} {keyword}"
            items.append(
                {
                    "name": f"{name}附近{label}",
                    "group": group_key,
                    "group_name": group_name,
                    "category": category,
                    "category_name": label,
                    "keyword": keyword,
                    "address": f"{area}周边" if area else "景区周边",
                    "distance_text": "景区周边，需以实时地图为准",
                    "source": "高德地图公开检索",
                    "source_name": "高德地图公开检索",
                    "source_type": "public_map_search",
                    "source_url": _amap_search_url(query),
                    "risk_level": "low",
                    "confidence": 68,
                    "theme_slugs": [theme["slug"] for theme in themes],
                }
            )
    nearby_food = [item for item in items if item["category"] in FOOD_CATEGORIES]
    nearby_hotels = [item for item in items if item["category"] in HOTEL_CATEGORIES]
    nearby_pois = [item for item in items if item["category"] not in FOOD_CATEGORIES | HOTEL_CATEGORIES]
    return {
        "nearby_pois": nearby_pois,
        "nearby_food": nearby_food,
        "nearby_hotels": nearby_hotels,
        "recommended_routes": _routes(name, themes),
        "travel_tips": _tips(name),
        "traffic_info": f"已建立{name}周边公交站、地铁站、停车场公开地图检索索引，出发前建议按实时地图确认线路和步行距离。",
        "public_transport": f"可优先检索“{name} 公交站”“{name} 地铁站”，结合实时换乘结果选择到达方式。",
        "parking_info": f"自驾可检索“{name} 停车场”，旺季建议提前确认停车容量、收费和步行入口。",
        "self_driving_route": f"自驾导航至“{name}”后，可结合停车场、补给点和步道入口索引规划落客与返程。",
    }


def _select_scenics(db, limit: int, province: str, city: str, force: bool):
    sql = "SELECT * FROM scenic_spots WHERE 1=1"
    params = []
    if province:
        sql += " AND province=?"
        params.append(province)
    if city:
        sql += " AND city=?"
        params.append(city)
    if not force:
        sql += """
          AND (
            nearby_pois IS NULL OR nearby_pois='' OR nearby_pois='[]' OR nearby_pois NOT LIKE '%bus_station%' OR nearby_pois NOT LIKE '%trailhead%' OR
            nearby_food IS NULL OR nearby_food='' OR nearby_food='[]' OR
            nearby_hotels IS NULL OR nearby_hotels='' OR nearby_hotels='[]'
          )
        """
    sql += " ORDER BY id ASC LIMIT ?"
    params.append(limit)
    return rows_to_list(db.execute(sql, params).fetchall())


def _matched_themes(scenic: dict) -> list[dict]:
    text = " ".join(str(scenic.get(key) or "") for key in ("name", "summary", "description", "tags", "level"))
    matched = []
    for theme in THEME_CATALOG:
        if any(term in text for term in theme.get("keywords", [])):
            matched.append({"slug": theme["slug"], "name": theme["name"]})
    return matched[:4] or [{"slug": "nature", "name": "自然风光"}]


def _routes(name: str, themes: list[dict]) -> list[str]:
    theme_names = " / ".join(theme["name"] for theme in themes[:2])
    return [
        f"交通到达 -> {name}主入口 -> 核心游览区 -> 周边餐饮补给",
        f"停车场/地铁站 -> 游客中心 -> 观景台/公园 -> 特产店或商场",
        f"步道入口 -> 补给点 -> 徒步观景段 -> 营地/返程点（{theme_names}）",
    ]


def _tips(name: str) -> list[str]:
    return [
        f"已为{name}建立公交、地铁、停车、餐饮、住宿、购物、周边游览和徒步补给索引，具体营业和距离以实时地图为准。",
        "山区、步道和露营类点位请优先确认天气、开放状态、补给能力和返程交通。",
        "餐厅、咖啡厅、小吃街、酒店、民宿等商业点位会随季节变化，建议出发前二次核对。",
    ]


def _amap_search_url(keyword: str) -> str:
    return "https://uri.amap.com/search?keyword=" + urlencode({"": keyword})[1:]


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _canonical_stats(values: dict) -> dict:
    mapping = {
        "totalscenic": "totalScenic",
        "missingnearbypois": "missingNearbyPois",
        "missingfoodpois": "missingFoodPois",
        "missingstaypois": "missingStayPois",
        "fullpoiindex": "fullPoiIndex",
    }
    return {mapping.get(str(key).lower(), key): (0 if value is None else value) for key, value in values.items()}


def _safe_audit(module: str, action: str):
    try:
        write_audit(module, action)
    except Exception:
        return


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
