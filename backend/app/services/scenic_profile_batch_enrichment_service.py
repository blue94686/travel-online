import json
from datetime import datetime

from app.core.database import get_db, rows_to_list
from app.services.scenic_quality_score_service import calculate_completeness_score


GENERIC_MARKERS = (
    "来自本地 SQL 数据源",
    "本地全国旅游景点 SQL 数据源",
    "适合纳入景区检索、路线规划和资料补全流程",
)

NATURE_TERMS = ("山", "森林", "峡谷", "湖", "河", "海", "瀑", "湿地", "自然", "风景", "海滩", "观景点", "世界遗产")
PARK_TERMS = ("公园", "广场", "动物园", "植物园", "水族馆", "游乐场")
CULTURE_TERMS = ("寺", "庙", "观", "教堂", "纪念馆", "博物馆", "展览馆", "王府", "古迹", "遗址", "文化")
LEISURE_TERMS = ("度假", "休闲", "温泉", "村", "街区", "农庄")


def enrich_profile_batch(limit: int = 5000, offset: int = 0, province: str = "", force: bool = False) -> dict:
    limit = max(1, min(int(limit or 5000), 50000))
    offset = max(0, int(offset or 0))
    where = "WHERE 1=1"
    params: list = []
    if province:
        where += " AND province=?"
        params.append(province)

    with get_db() as db:
        total = db.execute(f"SELECT COUNT(*) AS c FROM scenic_spots {where}", params).fetchone()["c"]
        rows = rows_to_list(
            db.execute(
                f"""
                SELECT *
                FROM scenic_spots
                {where}
                ORDER BY id ASC
                LIMIT ? OFFSET ?
                """,
                params + [limit, offset],
            ).fetchall()
        )
        updated = 0
        touched_fields = {}
        for scenic in rows:
            patch = build_profile_patch(scenic, force=force)
            if not patch:
                continue
            updated_row = scenic | patch
            patch["completeness_score"] = calculate_completeness_score(updated_row)
            patch["last_enriched_at"] = datetime.now().isoformat(timespec="seconds")
            assignments = ", ".join([f"{key}=?" for key in patch])
            db.execute(
                f"UPDATE scenic_spots SET {assignments} WHERE id=?",
                list(patch.values()) + [scenic["id"]],
            )
            updated += 1
            for key in patch:
                touched_fields[key] = touched_fields.get(key, 0) + 1

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "read": len(rows),
        "updated": updated,
        "next_offset": offset + len(rows),
        "done": offset + len(rows) >= total,
        "province": province,
        "force": force,
        "fields": touched_fields,
    }


def enrich_profile_all(batch_size: int = 20000, province: str = "", force: bool = False) -> dict:
    offset = 0
    total_read = 0
    total_updated = 0
    field_totals = {}
    last_result = {}
    while True:
        result = enrich_profile_batch(limit=batch_size, offset=offset, province=province, force=force)
        last_result = result
        total_read += result["read"]
        total_updated += result["updated"]
        for key, value in result["fields"].items():
            field_totals[key] = field_totals.get(key, 0) + value
        if result["done"] or result["read"] == 0:
            break
        offset = result["next_offset"]
    return {
        "total": last_result.get("total", 0),
        "read": total_read,
        "updated": total_updated,
        "province": province,
        "force": force,
        "fields": field_totals,
    }


def profile_completion_stats() -> dict:
    with get_db() as db:
        row = db.execute(
            """
            SELECT
              COUNT(*) AS total,
              SUM(CASE WHEN slogan IS NULL OR trim(slogan)='' THEN 1 ELSE 0 END) AS missing_slogan,
              SUM(CASE WHEN suitable_groups IS NULL OR suitable_groups='' OR suitable_groups='[]' THEN 1 ELSE 0 END) AS missing_groups,
              SUM(CASE WHEN recommended_duration IS NULL OR trim(recommended_duration)='' THEN 1 ELSE 0 END) AS missing_duration,
              SUM(CASE WHEN history_culture IS NULL OR trim(history_culture)='' THEN 1 ELSE 0 END) AS missing_history,
              SUM(CASE WHEN highlights IS NULL OR trim(highlights)='' THEN 1 ELSE 0 END) AS missing_highlights,
              SUM(CASE WHEN traffic_info IS NULL OR trim(traffic_info)='' THEN 1 ELSE 0 END) AS missing_traffic,
              SUM(CASE WHEN public_transport IS NULL OR trim(public_transport)='' THEN 1 ELSE 0 END) AS missing_public_transport,
              SUM(CASE WHEN parking_info IS NULL OR trim(parking_info)='' THEN 1 ELSE 0 END) AS missing_parking,
              SUM(CASE WHEN must_see_spots IS NULL OR must_see_spots='' OR must_see_spots='[]' THEN 1 ELSE 0 END) AS missing_must_see,
              SUM(CASE WHEN recommended_itinerary IS NULL OR recommended_itinerary='' OR recommended_itinerary='[]' THEN 1 ELSE 0 END) AS missing_itinerary,
              SUM(CASE WHEN photo_spots IS NULL OR photo_spots='' OR photo_spots='[]' THEN 1 ELSE 0 END) AS missing_photo,
              SUM(CASE WHEN travel_tips IS NULL OR travel_tips='' OR travel_tips='[]' THEN 1 ELSE 0 END) AS missing_tips,
              SUM(CASE WHEN cover_image_url IS NULL OR trim(cover_image_url)='' THEN 1 ELSE 0 END) AS missing_cover,
              SUM(CASE WHEN official_website IS NULL OR trim(official_website)='' THEN 1 ELSE 0 END) AS missing_website
            FROM scenic_spots
            """
        ).fetchone()
    return dict(row)


def build_profile_patch(scenic: dict, force: bool = False) -> dict:
    profile_type = _profile_type(scenic)
    name = scenic.get("name") or "该景点"
    province = scenic.get("province") or ""
    city = scenic.get("city") or ""
    district = scenic.get("district") or ""
    area = "".join([province, city, district]) or scenic.get("address") or "所在地"
    tags = _json_list(scenic.get("tags")) or _default_tags(profile_type)
    category = _category_label(scenic, tags, profile_type)

    content = _content_for_type(profile_type)
    summary = f"{name}位于{area}，以{category}为主要特色，适合{content['audience_short']}。"
    description = (
        f"{name}是{city or province or '当地'}值得纳入行程的目的地，站内根据行政区划、类别标签和基础 POI 数据完成资料整理。"
        f"游客可围绕{content['experience']}安排游览，出发前建议核对开放时间、票务政策、交通管制和现场公告。"
        f"若作为周边游节点，可与同城景点、餐饮补给和公共交通换乘一起规划。"
    )

    patch = {}
    if _should_fill(scenic.get("summary"), force):
        patch["summary"] = summary
    if _should_fill(scenic.get("description"), force):
        patch["description"] = description
    if _should_fill(scenic.get("tags"), force):
        patch["tags"] = _json(tags[:5])
    if _should_fill(scenic.get("slogan"), force):
        patch["slogan"] = f"到{name}，发现{city or province or '本地'}的{content['slogan_tail']}。"
    if _should_fill(scenic.get("suitable_groups"), force):
        patch["suitable_groups"] = _json(content["groups"])
    if _should_fill(scenic.get("recommended_duration"), force):
        patch["recommended_duration"] = content["duration"]
    if _should_fill(scenic.get("history_culture"), force):
        patch["history_culture"] = content["history"].format(name=name, city=city or province or "当地")
    if _should_fill(scenic.get("highlights"), force):
        patch["highlights"] = content["highlights"].format(name=name, category=category)
    if _should_fill(scenic.get("traffic_info"), force):
        patch["traffic_info"] = f"建议以{name}为导航目的地，结合实时地图查看道路拥堵、入口位置和步行距离。节假日请预留排队、停车和换乘时间。"
    if _should_fill(scenic.get("public_transport"), force):
        patch["public_transport"] = f"公共交通可优先查询前往{city or district or '景区所在地'}的地铁、公交或旅游专线，下车后按景区导览步行前往。"
    if _should_fill(scenic.get("parking_info"), force):
        patch["parking_info"] = "自驾游客建议提前确认停车场开放情况和收费标准，旺季尽量选择外围停车换乘。"
    if _should_fill(scenic.get("self_driving_route"), force):
        patch["self_driving_route"] = f"自驾可导航至“{name}”或其游客中心，临近景区后按现场交通标识和工作人员指引通行。"
    if _should_fill(scenic.get("accessibility_tips"), force):
        patch["accessibility_tips"] = "无障碍设施、轮椅租赁和老幼同行服务以景区现场公示为准，出行前建议电话或官方渠道确认。"
    if _should_fill(scenic.get("must_see_spots"), force):
        patch["must_see_spots"] = _json([name, content["must_see"][0], content["must_see"][1]])
    if _should_fill(scenic.get("photo_spots"), force):
        patch["photo_spots"] = _json([content["photo"][0], content["photo"][1], "游客中心或主入口打卡点"])
    if _should_fill(scenic.get("travel_tips"), force):
        patch["travel_tips"] = _json([
            "出发前核对开放时间、预约规则和临时闭园公告。",
            "旺季建议错峰到达，预留购票、安检和停车时间。",
            "请遵守景区游览路线、环境保护和安全提示。",
        ])
    if _should_fill(scenic.get("recommended_itinerary"), force):
        patch["recommended_itinerary"] = _json([
            {"title": "半日轻游", "content": f"抵达{name}后先查看导览图，优先游览核心区域，再根据体力选择周边延伸点。"},
            {"title": "一日深度", "content": f"上午安排{name}核心看点，午后结合{city or province or '当地'}周边餐饮、街区或同城景点继续游览。"},
        ])
    return patch


def _profile_type(scenic: dict) -> str:
    text = " ".join(
        str(scenic.get(key) or "")
        for key in ("name", "level", "summary", "description", "tags")
    )
    if any(term in text for term in CULTURE_TERMS):
        return "culture"
    if any(term in text for term in PARK_TERMS):
        return "park"
    if any(term in text for term in NATURE_TERMS):
        return "nature"
    if any(term in text for term in LEISURE_TERMS):
        return "leisure"
    return "general"


def _content_for_type(profile_type: str) -> dict:
    data = {
        "nature": {
            "audience_short": "自然观光、摄影打卡、徒步休闲和亲友出游",
            "experience": "观景、拍照、慢行和季节性景观",
            "slogan_tail": "山水景致与户外体验",
            "groups": ["摄影爱好者", "自然风光游客", "亲友结伴", "周边自驾"],
            "duration": "3-5 小时",
            "history": "{name}所在区域体现了{city}自然景观和地方旅游资源的组合，可结合地形、季节和生态环境理解其游览价值。",
            "highlights": "核心亮点包括{category}、开阔观景、季节变化和适合拍照的自然空间。",
            "must_see": ["核心观景区", "步道或临水观景点"],
            "photo": ["高处或开阔视角", "日出日落和季节景观"],
        },
        "park": {
            "audience_short": "亲子散步、城市休闲、轻量运动和周末放松",
            "experience": "慢行、休憩、亲子活动和城市公共空间体验",
            "slogan_tail": "城市休闲与亲子时光",
            "groups": ["亲子家庭", "城市漫步", "老少同行", "周末休闲"],
            "duration": "1-3 小时",
            "history": "{name}是{city}城市休闲空间的一部分，适合观察本地生活方式和公共文化活动。",
            "highlights": "核心亮点包括{category}、开放空间、轻松步行路线和适合家庭停留的活动节点。",
            "must_see": ["主景观区", "休闲步道"],
            "photo": ["入口标识", "开阔草坪或水景区域"],
        },
        "culture": {
            "audience_short": "人文探访、研学旅行、建筑摄影和历史文化兴趣游客",
            "experience": "建筑细节、历史线索、展陈内容和地方文化",
            "slogan_tail": "人文记忆与建筑细节",
            "groups": ["文化爱好者", "研学游客", "建筑摄影", "亲子讲解"],
            "duration": "2-4 小时",
            "history": "{name}承载了{city}的人文文化线索，适合结合展陈、建筑格局、地方故事和官方讲解进行理解。",
            "highlights": "核心亮点包括{category}、建筑空间、文化展陈和适合慢看的细节。",
            "must_see": ["主体建筑或展陈区", "文化展示节点"],
            "photo": ["建筑立面", "院落或展陈细节"],
        },
        "leisure": {
            "audience_short": "度假休闲、朋友聚会、家庭短途和轻松打卡",
            "experience": "休闲停留、餐饮补给、轻体验和周边联游",
            "slogan_tail": "轻松停留与周边联游",
            "groups": ["朋友出游", "家庭度假", "周边短途", "轻松打卡"],
            "duration": "2-4 小时",
            "history": "{name}体现了{city}休闲旅游资源的组合，适合与周边餐饮、住宿或同城景点一并安排。",
            "highlights": "核心亮点包括{category}、轻松体验、周边配套和适合停留的游玩节奏。",
            "must_see": ["核心体验区", "休闲停留区"],
            "photo": ["主入口打卡点", "特色体验空间"],
        },
        "general": {
            "audience_short": "城市探索、路线途经、周边游和轻量打卡",
            "experience": "位置打卡、周边联游、城市探索和短暂停留",
            "slogan_tail": "本地风景与城市探索",
            "groups": ["城市探索者", "周边游客", "路线途经", "轻量打卡"],
            "duration": "1-2 小时",
            "history": "{name}是{city}本地旅游数据中的目的地，可作为城市探索、路线规划和周边联游的节点。",
            "highlights": "核心亮点包括{category}、便利的位置、可与周边目的地组合的行程弹性。",
            "must_see": ["核心游览点", "周边街区"],
            "photo": ["入口或标识点", "周边开阔视角"],
        },
    }
    return data.get(profile_type, data["general"])


def _category_label(scenic: dict, tags: list[str], profile_type: str) -> str:
    level = str(scenic.get("level") or "").strip()
    if level and level not in ("旅游景点", "全国景点"):
        return level
    if tags:
        return "、".join(tags[:2])
    return {
        "nature": "自然风光",
        "park": "城市休闲",
        "culture": "历史文化",
        "leisure": "休闲度假",
        "general": "本地旅游",
    }[profile_type]


def _default_tags(profile_type: str) -> list[str]:
    return {
        "nature": ["自然风光", "摄影", "户外", "周边游"],
        "park": ["公园广场", "亲子", "城市漫步", "休闲"],
        "culture": ["历史文化", "建筑", "研学", "摄影"],
        "leisure": ["休闲度假", "亲友出游", "周边游", "打卡"],
        "general": ["本地景点", "城市探索", "周边游", "打卡"],
    }[profile_type]


def _should_fill(value, force: bool = False) -> bool:
    if force:
        return True
    if value is None:
        return True
    text = str(value).strip()
    if text in ("", "[]", "{}"):
        return True
    return any(marker in text for marker in GENERIC_MARKERS)


def _json(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _json_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    except (TypeError, json.JSONDecodeError):
        pass
    return [part.strip() for part in str(value).replace("；", ";").split(";") if part.strip()]
