import json
from urllib.parse import quote_plus


SEARCH_TEMPLATES = [
    "{name} 官方网站",
    "{name} 景区介绍",
    "{name} 门票 开放时间",
    "{name} 游玩攻略",
    "{name} 地址 交通",
    "{name} 历史文化",
    "{name} 特色 看点",
    "{province}{city}{name} 旅游",
    "{name} {level} 景区",
    "{name} 图片",
]

SOURCE_PRIORITY_NOTE = "未配置外部 API Key，当前候选为搜索链接和本地规则草稿，需管理员核验。"


def build_search_keywords(scenic: dict) -> list[str]:
    context = {
        "name": scenic.get("name") or "",
        "province": scenic.get("province") or "",
        "city": scenic.get("city") or "",
        "district": scenic.get("district") or "",
        "level": scenic.get("level") or "",
        "address": scenic.get("address") or "",
        "tags": " ".join(_json_list(scenic.get("tags"))),
        "website": scenic.get("official_website") or "",
        "latlng": f"{scenic.get('latitude') or ''},{scenic.get('longitude') or ''}".strip(","),
    }
    keywords = [template.format(**context).strip() for template in SEARCH_TEMPLATES]
    extras = [
        f"{context['name']} {context['district']} {context['address']}".strip(),
        f"{context['name']} {context['tags']}".strip(),
    ]
    return [item for item in dict.fromkeys(keywords + extras) if item]


def generate_profile_candidates(scenic: dict, api_config: dict | None = None) -> list[dict]:
    config = api_config or {}
    keywords = build_search_keywords(scenic)
    main_keyword = keywords[0]
    intro_keyword = next((item for item in keywords if "景区介绍" in item), main_keyword)
    image_keyword = next((item for item in keywords if "图片" in item), main_keyword)
    search_url = _bing_search_url(main_keyword)
    intro_url = _bing_search_url(intro_keyword)
    image_url = _bing_image_url(image_keyword)
    city = scenic.get("city") or scenic.get("province") or ""
    name = scenic.get("name") or "该景区"
    location = "".join(filter(None, [scenic.get("province"), scenic.get("city"), scenic.get("district")]))
    tags = _json_list(scenic.get("tags")) or ["自然风光", "摄影", "自驾"]

    generated_summary = f"{name}位于{location or '目的地所在地'}，本条为待审核简介草稿，仅基于站内已有字段生成，需结合官方资料复核后发布。"
    generated_full = (
        f"{name}是{city or '当地'}具有代表性的旅游目的地。当前系统未直接抓取或复制外部网页正文，"
        f"仅根据景区名称、行政区划、等级、地址和主题标签生成待审核资料框架。管理员应优先核验官方网站、文旅局公开页面、"
        f"地图 POI 与票务开放时间公告，再决定是否发布到前台。适合人群可先按{ '、'.join(tags[:4]) }等标签初步归类。"
    )

    base_payload = {
        "keywords": keywords,
        "fallback": not any(config.values()),
        "note": SOURCE_PRIORITY_NOTE,
    }
    return [
        _candidate(scenic, "official_site", f"{name} 官方网站搜索候选", search_url, search_url, "Bing Search", "bing", 60, "medium", base_payload),
        _candidate(scenic, "summary", f"{name} 150字短介绍草稿", generated_summary, intro_url, "本地规则草稿", "generated_draft", 56, "medium", base_payload),
        _candidate(scenic, "summary_full", f"{name} 详细介绍草稿", generated_full, intro_url, "本地规则草稿", "generated_draft", 54, "medium", base_payload),
        _candidate(scenic, "slogan", f"{name} 一句话推荐语", f"到{name}，用半天到一天读懂{city or '这座城市'}的风景与人文。", intro_url, "本地规则草稿", "generated_draft", 50, "medium", base_payload),
        _candidate(scenic, "ticket", f"{name} 门票搜索候选", scenic.get("ticket_price") or "以景区官网、公众号或现场公示为准", _bing_search_url(f"{name} 门票 开放时间"), "Bing Search", "bing", 48, "medium", base_payload),
        _candidate(scenic, "opening_hours", f"{name} 开放时间搜索候选", scenic.get("opening_hours") or "以景区官网、公众号或现场公示为准", _bing_search_url(f"{name} 开放时间"), "Bing Search", "bing", 48, "medium", base_payload),
        _candidate(scenic, "address", f"{name} 地址交通候选", scenic.get("address") or f"{location}{name}", _bing_search_url(f"{name} 地址 交通"), "Bing Search", "bing", 58, "medium", base_payload),
        _candidate(scenic, "traffic", f"{name} 交通攻略候选", "建议核验地铁、公交、停车场与节假日交通管制信息后发布。", _bing_search_url(f"{name} 地址 交通"), "Bing Search", "bing", 45, "medium", base_payload),
        _candidate(scenic, "history", f"{name} 历史文化候选", "历史文化内容需以官方介绍、文旅局公开资料或景区展陈资料为准。", _bing_search_url(f"{name} 历史文化"), "Bing Search", "bing", 42, "medium", base_payload),
        _candidate(scenic, "highlights", f"{name} 特色看点候选", "特色看点需从官方介绍、游览图和审核后的公开摘要中提炼。", _bing_search_url(f"{name} 特色 看点"), "Bing Search", "bing", 42, "medium", base_payload),
        _candidate(scenic, "image", f"{name} 图片搜索候选", image_url, image_url, "Bing Image Search", "bing", 46, "high", base_payload | {"copyright": "需审核图片授权与景区匹配度"}),
    ]


def _candidate(scenic, candidate_type, title, content, source_url, source_name, source_type, confidence, risk_level, raw_payload):
    return {
        "scenic_id": scenic["id"],
        "candidate_type": candidate_type,
        "title": title,
        "content": content,
        "source_url": source_url,
        "source_name": source_name,
        "source_type": source_type,
        "confidence": confidence,
        "risk_level": risk_level,
        "status": "pending",
        "raw_payload_json": json.dumps(raw_payload, ensure_ascii=False),
    }


def _bing_search_url(keyword: str) -> str:
    return f"https://www.bing.com/search?q={quote_plus(keyword)}"


def _bing_image_url(keyword: str) -> str:
    return f"https://www.bing.com/images/search?q={quote_plus(keyword)}"


def _json_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value) if isinstance(value, str) else value
        return parsed if isinstance(parsed, list) else []
    except json.JSONDecodeError:
        return []
