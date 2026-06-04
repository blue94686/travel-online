import json
import os
import re
import time
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request, urlopen

from app.core.config import AMAP_WEB_SERVICE_ENDPOINT
from app.core.database import get_db, row_to_dict, rows_to_list
from app.services.scenic_content_merge_service import build_diff


BING_WEB_ENDPOINT = "https://api.bing.microsoft.com/v7.0/search"
BING_IMAGE_ENDPOINT = "https://api.bing.microsoft.com/v7.0/images/search"
WIKIPEDIA_ENDPOINT = "https://zh.wikipedia.org/w/api.php"
WIKIVOYAGE_ENDPOINT = "https://zh.wikivoyage.org/w/api.php"
COMMONS_ENDPOINT = "https://commons.wikimedia.org/w/api.php"
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.openstreetmap.ru/api/interpreter",
)
MCT_SCENIC_URL = "https://www.mct.gov.cn/"
SOURCE_COOLDOWN_SECONDS = 300
_SOURCE_COOLDOWNS: dict[str, float] = {}

LOW_TRUST_DOMAINS = (
    "bing.com",
    "baidu.com",
    "ctrip.com",
    "trip.com",
    "mafengwo.cn",
    "dianping.com",
    "xiaohongshu.com",
    "douyin.com",
    "toutiao.com",
)

TITLE_SUFFIXES = (
    "风景名胜区",
    "国家森林公园",
    "森林公园",
    "风景区",
    "景区",
    "旅游区",
    "公园",
    "景点",
)

TITLE_ALIASES = {
    "黄山风景区": ["黄山"],
    "九寨沟风景名胜区": ["九寨沟"],
    "桂林漓江风景区": ["漓江"],
    "千岛湖风景区": ["千岛湖"],
    "雷峰塔景区": ["雷峰塔"],
}


def external_enrichment_readiness():
    with get_db() as db:
        config = _provider_config(db)
    return {
        "bing_search": bool(config.get("bing_search")),
        "bing_image": bool(config.get("bing_image")),
        "amap_web_service": bool(config.get("amap_web_service")),
        "wikipedia": True,
        "wikivoyage": True,
        "wikimedia_commons": True,
        "openstreetmap_overpass": True,
        "mct_official": True,
        "ctrip_open": bool(config.get("ctrip_open")),
        "mafengwo": bool(config.get("mafengwo")),
        "baidu_map": bool(config.get("baidu_map")),
        "tencent_lbs": bool(config.get("tencent_lbs")),
        "storage_policy": "本地只存轻量索引和审核状态，图片保持外链或后续转对象存储/CDN。",
        "review_policy": "外部资料进入候选池，管理员审核通过后才写入正式景区资料或图片索引。",
        "fallback_policy": "前台优先使用已审核资料；外部失败时使用本地基础资料、占位图和候选重试。",
        "provider_order": ["wikimedia_commons", "wikipedia", "wikivoyage", "openstreetmap_overpass", "mct_official", "bing_image", "bing_search", "baidu_map", "tencent_lbs", "amap_web_service"],
        "quota_policy": "批量补全默认不使用高德；如配额恢复，可在接口参数里显式开启付费/配额型来源。",
        "note": "Wikipedia、Wikivoyage、Commons、OpenStreetMap 为公开来源；文旅部用于官方名录校验；携程、马蜂窝、百度、腾讯需后台配置后再启用。",
    }


def external_enrich_profile_batch(
    limit: int = 20,
    offset: int = 0,
    province: str = "",
    city: str = "",
    only_missing_media: bool = True,
    include_public_sources: bool = True,
    include_paid_providers: bool = False,
    sleep_seconds: float = 0.9,
):
    limit = max(1, min(int(limit or 20), 200))
    offset = max(0, int(offset or 0))
    sql = "SELECT * FROM scenic_spots WHERE 1=1"
    params = []
    if province:
        sql += " AND province=?"
        params.append(province)
    if city:
        sql += " AND city=?"
        params.append(city)
    if only_missing_media:
        sql += " AND (official_website IS NULL OR official_website='' OR cover_image_url IS NULL OR cover_image_url='')"
    sql += " ORDER BY id ASC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    with get_db() as db:
        rows = rows_to_list(db.execute(sql, params).fetchall())
        config = _provider_config(db)

        stats = {
            "requested": len(rows),
            "searched": 0,
            "profile_candidates": 0,
            "image_candidates": 0,
            "skipped_no_provider": 0,
            "failures": [],
            "limit": limit,
            "offset": offset,
            "next_offset": offset + len(rows),
            "done": len(rows) < limit,
            "providers": {
                "bing_search": bool(include_paid_providers and config.get("bing_search")),
                "bing_image": bool(include_paid_providers and config.get("bing_image")),
                "amap_web_service": bool(include_paid_providers and config.get("amap_web_service")),
                "public_sources": include_public_sources,
                "wikipedia": include_public_sources,
                "wikivoyage": include_public_sources,
                "wikimedia_commons": include_public_sources,
                "openstreetmap_overpass": include_public_sources,
            },
        }

        any_provider = bool((include_paid_providers and (config.get("bing_search") or config.get("bing_image") or config.get("amap_web_service"))) or include_public_sources)
        for scenic in rows:
            if not any_provider:
                stats["skipped_no_provider"] += 1
                continue
            try:
                result = _enrich_one(db, scenic, config, include_public_sources, include_paid_providers)
                stats["searched"] += 1
                stats["profile_candidates"] += result["profile_candidates"]
                stats["image_candidates"] += result["image_candidates"]
                stats["failures"].extend(result.get("failures", []))
            except Exception as exc:  # bulk jobs must continue
                stats["failures"].append({"scenic_id": scenic["id"], "name": scenic["name"], "message": str(exc)[:180]})
            if sleep_seconds:
                time.sleep(max(0, min(float(sleep_seconds), 2)))
    return stats


def external_enrich_profile_all(
    batch_size: int = 50,
    max_total: int = 500,
    province: str = "",
    city: str = "",
    include_public_sources: bool = True,
    include_paid_providers: bool = False,
):
    batch_size = max(1, min(int(batch_size or 50), 200))
    max_total = max(1, min(int(max_total or 500), 1000))
    offset = 0
    total = {"requested": 0, "searched": 0, "profile_candidates": 0, "image_candidates": 0, "skipped_no_provider": 0, "failures": []}
    batches = []
    while total["requested"] < max_total:
        result = external_enrich_profile_batch(
            limit=min(batch_size, max_total - total["requested"]),
            offset=offset,
            province=province,
            city=city,
            include_public_sources=include_public_sources,
            include_paid_providers=include_paid_providers,
        )
        batches.append(result)
        for key in ("requested", "searched", "profile_candidates", "image_candidates", "skipped_no_provider"):
            total[key] += result[key]
        total["failures"].extend(result["failures"])
        offset = result["next_offset"]
        if result["done"] or result["requested"] == 0:
            break
    return total | {"batch_size": batch_size, "max_total": max_total, "batches": batches}


def public_source_candidates(scenic):
    profiles, image_candidates = public_source_bundle(scenic)
    return (profiles[0] if profiles else None), image_candidates


def public_source_bundle(scenic, include_osm: bool = True):
    profiles, image_candidates, _failures = public_source_bundle_detailed(scenic, include_osm=include_osm)
    return profiles, image_candidates


def public_sources_blocked_seconds(include_osm: bool = True):
    providers = ["wikipedia", "wikivoyage", "wikimedia_commons"]
    if include_osm:
        providers.append("openstreetmap_overpass")
    remaining = [_cooldown_remaining(provider) for provider in providers]
    active = [value for value in remaining if value > 0]
    if active and len(active) == len(providers):
        return max(1, min(active))
    return 0


def public_source_bundle_detailed(scenic, include_osm: bool = True):
    scenic = row_to_dict(scenic)
    profile_candidates = []
    image_candidates = []
    failures = []
    fetchers = [
        ("wikipedia", _wikipedia_candidates),
        ("wikivoyage", _wikivoyage_candidates),
    ]
    if include_osm:
        fetchers.append(("openstreetmap_overpass", _osm_candidates))
    for provider, fetcher in fetchers:
        cooldown = _cooldown_remaining(provider)
        if cooldown:
            failures.append(_provider_failure(provider, f"cooldown {cooldown}s"))
            continue
        try:
            profiles, images = fetcher(scenic)
            if profiles:
                if isinstance(profiles, list):
                    profile_candidates.extend(profiles)
                else:
                    profile_candidates.append(profiles)
            image_candidates.extend(images or [])
        except RuntimeError as exc:
            _record_source_cooldown(provider, exc)
            failures.append(_provider_failure(provider, exc))
        time.sleep(0.12)
    commons_cooldown = _cooldown_remaining("wikimedia_commons")
    if commons_cooldown:
        failures.append(_provider_failure("wikimedia_commons", f"cooldown {commons_cooldown}s"))
    else:
        try:
            image_candidates.extend(_commons_image_candidates(scenic))
        except RuntimeError as exc:
            _record_source_cooldown("wikimedia_commons", exc)
            failures.append(_provider_failure("wikimedia_commons", exc))
    profile_candidates.sort(key=lambda item: int(item.get("confidence") or 0), reverse=True)
    return profile_candidates[:8], _dedupe_images(image_candidates)[:8], failures


def _enrich_one(db, scenic, config, include_public_sources, include_paid_providers=False):
    scenic = row_to_dict(scenic)
    profile_candidates = []
    image_candidates = []
    failures = []

    if include_paid_providers and config.get("bing_search"):
        try:
            profile_candidates.extend(_bing_web_candidates(scenic, config["bing_search"]))
        except RuntimeError as exc:
            failures.append(_source_failure(scenic, "bing_search", exc))
    if include_paid_providers and config.get("bing_image"):
        try:
            image_candidates.extend(_bing_image_candidates(scenic, config["bing_image"]))
        except RuntimeError as exc:
            failures.append(_source_failure(scenic, "bing_image", exc))
    if include_paid_providers and config.get("amap_web_service"):
        try:
            amap_profiles, amap_images = _amap_candidates(scenic, config["amap_web_service"])
            profile_candidates.extend(amap_profiles)
            image_candidates.extend(amap_images)
        except RuntimeError as exc:
            failures.append(_source_failure(scenic, "amap_web_service", exc))
    if include_public_sources:
        try:
            public_profiles, public_images = public_source_bundle(scenic)
            profile_candidates.extend(public_profiles)
            image_candidates.extend(public_images)
        except RuntimeError as exc:
            failures.append(_source_failure(scenic, "public_sources", exc))

    inserted_profiles = 0
    for candidate in profile_candidates:
        candidate["diff_json"] = json.dumps(build_diff(scenic, candidate), ensure_ascii=False)
        inserted_profiles += _insert_profile_candidate(db, candidate)

    inserted_images = 0
    for candidate in image_candidates:
        inserted_images += _insert_image_candidate(db, candidate)

    return {"profile_candidates": inserted_profiles, "image_candidates": inserted_images, "failures": failures}


def _source_failure(scenic, source, exc):
    return {"scenic_id": scenic["id"], "name": scenic["name"], "source": source, "message": str(exc)[:180]}


def _provider_config(db):
    rows = db.execute(
        "SELECT provider, enabled, api_key_secret, api_key_masked FROM api_configs WHERE provider IN ('bing_search','bing_image','amap_web_service','ctrip_open','mafengwo','baidu_map','tencent_lbs')"
    ).fetchall()
    config = {}
    env_map = {
        "bing_search": "BING_SEARCH_KEY",
        "bing_image": "BING_IMAGE_SEARCH_KEY",
        "amap_web_service": "AMAP_WEB_SERVICE_KEY",
        "ctrip_open": "CTRIP_OPEN_KEY",
        "mafengwo": "MAFENGWO_KEY",
        "baidu_map": "BAIDU_MAP_KEY",
        "tencent_lbs": "TENCENT_LBS_KEY",
    }
    for row in rows:
        env_value = os.environ.get(env_map.get(row["provider"], ""), "")
        db_value = row["api_key_secret"] or ""
        masked = row["api_key_masked"] or ""
        key = env_value or db_value or (masked if masked and "*" not in masked else "")
        if row["enabled"] and key:
            config[row["provider"]] = key
    return config


def _bing_web_candidates(scenic, api_key):
    keyword = _search_keyword(scenic, "官方网站 景区介绍 开放时间 门票")
    payload = _http_get_json(
        f"{BING_WEB_ENDPOINT}?{urlencode({'q': keyword, 'mkt': 'zh-CN', 'count': 6, 'safeSearch': 'Strict'})}",
        headers={"Ocp-Apim-Subscription-Key": api_key},
    )
    results = ((payload or {}).get("webPages") or {}).get("value") or []
    candidates = []
    seen_summary = False
    for item in results:
        source_url = item.get("url") or ""
        snippet = _clean_text(item.get("snippet") or "")
        title = _clean_text(item.get("name") or scenic["name"])
        if not source_url or not snippet:
            continue
        domain = _domain(source_url)
        confidence = _web_confidence(source_url, title, scenic)
        if not seen_summary:
            candidates.append(_profile_candidate(scenic, "summary", title, _trim(snippet, 180), source_url, "Bing Web Search", "bing_web", confidence, "medium", item))
            seen_summary = True
        if _looks_official(source_url, title, scenic):
            candidates.append(_profile_candidate(scenic, "official_site", f"{scenic['name']} 官网候选", source_url, source_url, "Bing Web Search", "bing_web", min(95, confidence + 8), "low", item))
        field = _snippet_field(snippet)
        if field:
            candidates.append(_profile_candidate(scenic, field[0], f"{scenic['name']} {field[1]}候选", field[2], source_url, "Bing Web Search", "bing_web", confidence, "medium", item))
        if domain and not any(low in domain for low in LOW_TRUST_DOMAINS) and len(candidates) >= 4:
            break
    return candidates


def _bing_image_candidates(scenic, api_key):
    keyword = _search_keyword(scenic, "景区 实景 图片")
    payload = _http_get_json(
        f"{BING_IMAGE_ENDPOINT}?{urlencode({'q': keyword, 'mkt': 'zh-CN', 'count': 6, 'safeSearch': 'Strict', 'imageType': 'Photo'})}",
        headers={"Ocp-Apim-Subscription-Key": api_key},
    )
    return [
        _image_candidate(
            scenic,
            image_url=item.get("contentUrl") or "",
            thumbnail_url=item.get("thumbnailUrl") or "",
            source_url=item.get("hostPageUrl") or "",
            title=item.get("name") or scenic["name"],
            source_name="Bing Image Search",
            source_type="bing_image",
            confidence=0.72,
            risk_level="medium",
            raw=item,
        )
        for item in ((payload or {}).get("value") or [])
        if item.get("contentUrl")
    ][:4]


def _amap_candidates(scenic, api_key):
    payload = _http_get_json(
        f"{AMAP_WEB_SERVICE_ENDPOINT}/place/text?{urlencode({'key': api_key, 'keywords': scenic['name'], 'city': scenic.get('city') or '', 'citylimit': 'false', 'offset': 5, 'page': 1, 'extensions': 'all', 'output': 'JSON'})}"
    )
    pois = (payload or {}).get("pois") or []
    poi = _best_amap_poi(scenic, pois)
    if not poi:
        return [], []
    source_url = _amap_source_url(poi)
    raw = {"poi": poi}
    profile_candidates = []
    if _as_text(poi.get("address")):
        profile_candidates.append(_profile_candidate(scenic, "address", f"{scenic['name']} 高德地址候选", _as_text(poi.get("address")), source_url, "高德地图", "amap", 78, "low", raw))
    if _as_text(poi.get("opentime")):
        profile_candidates.append(_profile_candidate(scenic, "opening_hours", f"{scenic['name']} 高德开放时间候选", _as_text(poi.get("opentime")), source_url, "高德地图", "amap", 70, "medium", raw))
    if _as_text(poi.get("website")):
        profile_candidates.append(_profile_candidate(scenic, "official_site", f"{scenic['name']} 高德官网候选", _as_text(poi.get("website")), source_url, "高德地图", "amap", 74, "medium", raw))
    if _as_text(poi.get("tel")):
        profile_candidates.append(_profile_candidate(scenic, "phone", f"{scenic['name']} 高德电话候选", _as_text(poi.get("tel")), source_url, "高德地图", "amap", 68, "medium", raw))

    image_candidates = []
    for photo in poi.get("photos") or []:
        image_url = photo.get("url") or ""
        if not image_url:
            continue
        image_candidates.append(
            _image_candidate(
                scenic,
                image_url=image_url,
                thumbnail_url=image_url,
                source_url=source_url,
                title=photo.get("title") or scenic["name"],
                source_name="高德地图",
                source_type="amap",
                confidence=0.7,
                risk_level="medium",
                raw={"poi_id": poi.get("id"), "photo": photo},
            )
        )
    return profile_candidates, image_candidates[:4]


def _wikipedia_candidates(scenic):
    return _mediawiki_candidates(scenic, WIKIPEDIA_ENDPOINT, "维基百科", "wikipedia", "https://zh.wikipedia.org/wiki/", 62)


def _wikivoyage_candidates(scenic):
    return _mediawiki_candidates(scenic, WIKIVOYAGE_ENDPOINT, "维基导游", "wikivoyage", "https://zh.wikivoyage.org/wiki/", 66)


def _mediawiki_candidates(scenic, endpoint, source_name, source_type, page_base, confidence):
    for title in _title_variants(scenic["name"]):
        params = {
            "action": "query",
            "format": "json",
            "prop": "extracts|info|pageimages|coordinates",
            "exintro": 1,
            "explaintext": 1,
            "inprop": "url",
            "piprop": "original|thumbnail",
            "pithumbsize": 900,
            "colimit": 1,
            "redirects": 1,
            "titles": title,
            "origin": "*",
        }
        payload = _http_get_json(f"{endpoint}?{urlencode(params)}")
        pages = ((payload or {}).get("query") or {}).get("pages") or {}
        for page in pages.values():
            if page.get("missing") is not None:
                continue
            extract = _clean_text(page.get("extract") or "")
            source_url = page.get("fullurl") or ""
            images = []
            image_url = ((page.get("original") or {}).get("source") or (page.get("thumbnail") or {}).get("source") or "")
            if image_url:
                images.append(
                    _image_candidate(
                        scenic,
                        image_url=image_url,
                        thumbnail_url=(page.get("thumbnail") or {}).get("source") or image_url,
                        source_url=source_url or f"{page_base}{quote(title)}",
                        title=f"{scenic['name']} 页面主图",
                        source_name=source_name,
                        source_type=source_type,
                        confidence=0.64,
                        risk_level="medium",
                        raw=page,
                    )
                )
            if len(extract) >= 24:
                return (
                    _profile_candidate(
                        scenic,
                        "summary",
                        f"{scenic['name']} {source_name}摘要候选",
                        _trim(extract, 220),
                        source_url or f"{page_base}{quote(title)}",
                        source_name,
                        source_type,
                        confidence,
                        "medium",
                        page,
                    ),
                    images,
                )
            if images:
                return None, images
        time.sleep(0.1)
    return None, []


def _osm_candidates(scenic):
    name = _clean_text(scenic.get("name") or "")
    if len(name) < 2:
        return [], []
    variants = _title_variants(name)[:2]
    query_parts = []
    for variant in variants:
        regex = _overpass_regex(variant)
        query_parts.extend(
            [
                f'node["name"~"{regex}",i]["tourism"];',
                f'way["name"~"{regex}",i]["tourism"];',
                f'relation["name"~"{regex}",i]["tourism"];',
                f'node["name"~"{regex}",i]["historic"];',
                f'way["name"~"{regex}",i]["historic"];',
                f'relation["name"~"{regex}",i]["historic"];',
            ]
        )
    lat = _float_or_none(scenic.get("latitude") or scenic.get("web_latitude"))
    lon = _float_or_none(scenic.get("longitude") or scenic.get("web_longitude"))
    if lat is not None and lon is not None:
        query_parts.extend(
            [
                f'node(around:5000,{lat},{lon})["route"="hiking"];',
                f'way(around:5000,{lat},{lon})["route"="hiking"];',
                f'relation(around:5000,{lat},{lon})["route"="hiking"];',
            ]
        )
    query = f"[out:json][timeout:10];({''.join(query_parts)});out center tags 8;"
    payload = _overpass_get_json(query)
    elements = (payload or {}).get("elements") or []
    if not elements:
        return [], []
    profiles = []
    for element in elements[:6]:
        tags = element.get("tags") or {}
        element_name = _clean_text(tags.get("name") or name)
        source_url = _osm_source_url(element)
        confidence = _osm_confidence(name, element_name, tags)
        lat_value = element.get("lat") or (element.get("center") or {}).get("lat")
        lon_value = element.get("lon") or (element.get("center") or {}).get("lon")
        address = _osm_address(tags)
        if address:
            profiles.append(_profile_candidate(scenic, "address", f"{name} OSM 地址候选", address, source_url, "OpenStreetMap", "openstreetmap_overpass", confidence, "medium", element))
        if lat_value and lon_value:
            profiles.append(_profile_candidate(scenic, "coordinate", f"{name} OSM 坐标候选", json.dumps({"latitude": lat_value, "longitude": lon_value}, ensure_ascii=False), source_url, "OpenStreetMap", "openstreetmap_overpass", confidence, "medium", element))
        if tags.get("opening_hours"):
            profiles.append(_profile_candidate(scenic, "opening_hours", f"{name} OSM 开放时间候选", tags.get("opening_hours"), source_url, "OpenStreetMap", "openstreetmap_overpass", confidence - 4, "medium", element))
        if tags.get("website"):
            profiles.append(_profile_candidate(scenic, "official_site", f"{name} OSM 官网候选", tags.get("website"), source_url, "OpenStreetMap", "openstreetmap_overpass", confidence - 2, "medium", element))
        if tags.get("route") == "hiking" or tags.get("highway") in {"path", "footway", "track"}:
            profiles.append(_profile_candidate(scenic, "tips", f"{name} 徒步路线候选", f"OpenStreetMap 收录附近徒步路线：{element_name}。出行前请结合官方公告、天气和现场标识确认路线开放状态。", source_url, "OpenStreetMap", "openstreetmap_overpass", confidence, "medium", element))
    return profiles[:8], []


def _commons_image_candidates(scenic):
    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrnamespace": 6,
        "gsrlimit": 5,
        "gsrsearch": _search_keyword(scenic, "scenic"),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata|mime",
        "iiurlwidth": 900,
        "origin": "*",
    }
    payload = _http_get_json(f"{COMMONS_ENDPOINT}?{urlencode(params)}")
    pages = ((payload or {}).get("query") or {}).get("pages") or {}
    candidates = []
    for page in pages.values():
        imageinfo = (page.get("imageinfo") or [{}])[0]
        image_url = imageinfo.get("url") or ""
        if not image_url:
            continue
        meta = imageinfo.get("extmetadata") or {}
        license_name = (meta.get("LicenseShortName") or {}).get("value") or ""
        attribution = _clean_metadata((meta.get("Artist") or {}).get("value") or (meta.get("Credit") or {}).get("value") or "")
        raw = {"page": page, "license": license_name, "attribution": attribution}
        candidates.append(
            _image_candidate(
                scenic,
                image_url=image_url,
                thumbnail_url=imageinfo.get("thumburl") or image_url,
                source_url=(meta.get("ObjectURL") or {}).get("value") or imageinfo.get("descriptionurl") or "",
                title=page.get("title") or scenic["name"],
                source_name="Wikimedia Commons",
                source_type="wikimedia_commons",
                confidence=0.58,
                risk_level="medium",
                raw=raw,
                license_name=license_name,
                attribution=attribution,
            )
        )
    return candidates[:3]


def _dedupe_images(candidates):
    seen = set()
    deduped = []
    for item in candidates:
        url = item.get("image_url") or ""
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(item)
    deduped.sort(key=lambda item: int(item.get("quality_score") or 0), reverse=True)
    return deduped


def _cooldown_remaining(provider):
    until = _SOURCE_COOLDOWNS.get(provider, 0)
    remaining = int(until - time.time())
    return max(0, remaining)


def _record_source_cooldown(provider, exc):
    message = str(exc)
    if "429" in message or "Too Many Requests" in message:
        _SOURCE_COOLDOWNS[provider] = time.time() + SOURCE_COOLDOWN_SECONDS


def _provider_failure(provider, exc):
    message = str(exc)
    status = "rate_limited" if "429" in message or "Too Many Requests" in message or "cooldown" in message else "error"
    retry_after = _cooldown_remaining(provider)
    if not retry_after and "cooldown" in message:
        match = re.search(r"cooldown\s+(\d+)s", message)
        retry_after = int(match.group(1)) if match else 0
    return {"provider": provider, "status": status, "message": message[:180], "retryAfterSeconds": retry_after}


def _overpass_regex(value):
    value = re.escape(_clean_text(value))
    return value.replace('"', '\\"')


def _float_or_none(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _osm_source_url(element):
    element_type = element.get("type") or "node"
    element_id = element.get("id") or ""
    if element_id:
        return f"https://www.openstreetmap.org/{element_type}/{element_id}"
    return "https://www.openstreetmap.org/"


def _osm_address(tags):
    if tags.get("addr:full"):
        return _clean_text(tags.get("addr:full"))
    parts = [
        tags.get("addr:province"),
        tags.get("addr:city"),
        tags.get("addr:district"),
        tags.get("addr:street"),
        tags.get("addr:housenumber"),
    ]
    return "".join(_clean_text(part) for part in parts if part)


def _osm_confidence(scenic_name, element_name, tags):
    score = 52
    if element_name == scenic_name:
        score += 24
    elif element_name and (element_name in scenic_name or scenic_name in element_name):
        score += 12
    if tags.get("tourism") in {"attraction", "viewpoint", "museum", "theme_park", "zoo"}:
        score += 8
    if tags.get("historic"):
        score += 5
    if tags.get("route") == "hiking":
        score += 6
    return max(40, min(score, 84))


def _http_get_json(url, headers=None, timeout=8, retries=2):
    request = Request(url, headers={"User-Agent": "ScenicOnline/1.0 (+admin enrichment)", **(headers or {})})
    last_error = None
    for attempt in range(max(0, retries) + 1):
        try:
            with urlopen(request, timeout=timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            last_error = exc
            if exc.code != 429 or attempt >= retries:
                break
            time.sleep(1.2 * (attempt + 1))
        except (URLError, TimeoutError, HTTPException, OSError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            time.sleep(0.8 * (attempt + 1))
        except json.JSONDecodeError as exc:
            last_error = exc
            break
    raise RuntimeError(f"external request failed: {last_error}") from last_error


def _overpass_get_json(query):
    errors = []
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            return _http_get_json(f"{endpoint}?{urlencode({'data': query})}", timeout=3, retries=0)
        except RuntimeError as exc:
            errors.append(str(exc)[:120])
            time.sleep(0.2)
    raise RuntimeError("overpass endpoints unavailable: " + " | ".join(errors))


def _profile_candidate(scenic, candidate_type, title, content, source_url, source_name, source_type, confidence, risk_level, raw):
    return {
        "scenic_id": scenic["id"],
        "candidate_type": candidate_type,
        "title": title,
        "content": content,
        "source_url": source_url,
        "source_name": source_name,
        "source_type": source_type,
        "confidence": int(confidence),
        "risk_level": risk_level,
        "raw_payload_json": json.dumps(raw, ensure_ascii=False),
    }


def _image_candidate(scenic, image_url, thumbnail_url, source_url, title, source_name, source_type, confidence, risk_level, raw, license_name="", attribution=""):
    return {
        "scenic_id": scenic["id"],
        "image_url": image_url,
        "thumbnail_url": thumbnail_url or image_url,
        "source_url": source_url,
        "source_name": source_name,
        "source_type": source_type,
        "license": license_name or _license_from_raw(raw),
        "attribution": attribution or _attribution_from_raw(raw),
        "provider": source_type,
        "risk_level": risk_level,
        "status": "pending",
        "title": _clean_text(title),
        "confidence": float(confidence),
        "quality_score": int(round(float(confidence) * 100)),
        "availability_status": "unchecked",
        "failure_count": 0,
        "review_status": "pending",
        "raw_payload_json": json.dumps(raw, ensure_ascii=False),
    }


def _insert_profile_candidate(db, candidate):
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
    return 1 if cur.rowcount else 0


def _insert_image_candidate(db, candidate):
    exists = db.execute(
        "SELECT id FROM scenic_image_candidates WHERE scenic_id=? AND image_url=? LIMIT 1",
        (candidate["scenic_id"], candidate["image_url"]),
    ).fetchone()
    if exists:
        return 0
    db.execute(
        """
        INSERT INTO scenic_image_candidates
        (scenic_id,image_url,thumbnail_url,source_url,source_name,source_type,license,attribution,provider,risk_level,status,title,confidence,quality_score,availability_status,failure_count,review_status,raw_payload_json)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            candidate["scenic_id"], candidate["image_url"], candidate["thumbnail_url"], candidate["source_url"],
            candidate["source_name"], candidate["source_type"], candidate.get("license", ""), candidate.get("attribution", ""),
            candidate.get("provider", candidate["source_type"]), candidate["risk_level"], "pending",
            candidate["title"], candidate["confidence"], candidate.get("quality_score", 0), candidate.get("availability_status", "unchecked"),
            candidate.get("failure_count", 0), "pending", candidate.get("raw_payload_json", "{}"),
        ),
    )
    return 1


def _clean_metadata(value):
    return re.sub(r"<[^>]+>", "", _clean_text(value))


def _license_from_raw(raw):
    if not isinstance(raw, dict):
        return ""
    if raw.get("license"):
        return _clean_text(raw.get("license"))
    photo = raw.get("photo") or {}
    if isinstance(photo, dict):
        return _clean_text(photo.get("license") or "")
    return ""


def _attribution_from_raw(raw):
    if not isinstance(raw, dict):
        return ""
    if raw.get("attribution"):
        return _clean_metadata(raw.get("attribution"))
    photo = raw.get("photo") or {}
    if isinstance(photo, dict):
        return _clean_metadata(photo.get("author") or photo.get("copyright") or "")
    return ""


def _search_keyword(scenic, suffix):
    parts = [scenic.get("name") or "", scenic.get("province") or "", scenic.get("city") or "", scenic.get("district") or "", suffix]
    return " ".join(part for part in parts if part).strip()


def _title_variants(name):
    name = _clean_text(name)
    variants = [name, *TITLE_ALIASES.get(name, [])]
    bracket_stripped = re.sub(r"[（(].*?[）)]", "", name).strip()
    if bracket_stripped and bracket_stripped != name:
        variants.append(bracket_stripped)
    for suffix in TITLE_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix) + 1:
            variants.append(name[: -len(suffix)])
        if bracket_stripped.endswith(suffix) and len(bracket_stripped) > len(suffix) + 1:
            variants.append(bracket_stripped[: -len(suffix)])
    unique = []
    for value in variants:
        if value and value not in unique:
            unique.append(value)
    return unique[:4]


def _best_amap_poi(scenic, pois):
    if not pois:
        return None
    scenic_name = _clean_text(scenic.get("name"))
    scenic_city = _clean_text(scenic.get("city"))
    scored = []
    for poi in pois:
        name = _clean_text(poi.get("name"))
        score = 0
        if name == scenic_name:
            score += 60
        elif name and (name in scenic_name or scenic_name in name):
            score += 35
        if scenic_city and scenic_city in _clean_text(poi.get("cityname")):
            score += 20
        if _as_text(poi.get("photos")):
            score += 8
        scored.append((score, poi))
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[0][1] if scored and scored[0][0] >= 20 else None


def _amap_source_url(poi):
    location = poi.get("location") or ""
    name = poi.get("name") or "景区"
    if location:
        return f"https://uri.amap.com/marker?position={location}&name={quote(name)}"
    return f"https://uri.amap.com/search?keyword={quote(name)}"


def _as_text(value):
    if isinstance(value, list):
        return ""
    return _clean_text(value)


def _clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _trim(value, length):
    value = _clean_text(value)
    return value if len(value) <= length else value[: length - 1].rstrip() + "..."


def _domain(url):
    return urlparse(url or "").netloc.lower()


def _looks_official(url, title, scenic):
    domain = _domain(url)
    title = title or ""
    if any(low in domain for low in LOW_TRUST_DOMAINS):
        return False
    return ".gov.cn" in domain or "官网" in title or "官方" in title or "文旅" in title or scenic["name"] in title


def _web_confidence(url, title, scenic):
    score = 60
    domain = _domain(url)
    if ".gov.cn" in domain:
        score += 18
    if "官网" in title or "官方" in title:
        score += 12
    if scenic["name"] in title:
        score += 8
    if any(low in domain for low in LOW_TRUST_DOMAINS):
        score -= 18
    return max(35, min(score, 92))


def _snippet_field(snippet):
    if re.search(r"(开放时间|营业时间|入园时间)", snippet):
        return ("opening_hours", "开放时间", _trim(snippet, 140))
    if re.search(r"(门票|票价|免费|预约)", snippet):
        return ("ticket", "门票", _trim(snippet, 140))
    return None
