import json
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.config import AMAP_WEB_SERVICE_ENDPOINT
from app.services.provider_config_service import get_secret


AMAP_SCENIC_TYPES = "110000"


def mask_amap_key(key=None):
    key = key if key is not None else (get_secret("amap_web_service", "AMAP_WEB_SERVICE_KEY") or get_secret("amap", "AMAP_WEB_SERVICE_KEY"))
    if not key:
        return ""
    if len(key) <= 8:
        return "*" * len(key)
    return f"{key[:4]}{'*' * (len(key) - 8)}{key[-4:]}"


def amap_marker_url(name, longitude, latitude):
    if longitude in (None, "") or latitude in (None, ""):
        return "https://uri.amap.com/search?keyword=" + urlencode({"": name})[1:]
    return f"https://uri.amap.com/marker?position={longitude},{latitude}&name={urlencode({'': name})[1:]}"


def search_amap_pois(keyword, city="", limit=10, page=1, types=AMAP_SCENIC_TYPES):
    keyword = (keyword or "").strip()
    amap_key = get_secret("amap_web_service", "AMAP_WEB_SERVICE_KEY") or get_secret("amap", "AMAP_WEB_SERVICE_KEY")
    if not keyword or not amap_key:
        return {"items": [], "status": "0", "info": "empty keyword or missing key"}
    params = {
        "key": amap_key,
        "keywords": keyword,
        "types": types,
        "city": city or "",
        "citylimit": "false",
        "offset": max(1, min(int(limit), 25)),
        "page": max(1, int(page)),
        "extensions": "base",
        "output": "JSON",
    }
    url = f"{AMAP_WEB_SERVICE_ENDPOINT}/place/text?{urlencode(params)}"
    try:
        with urlopen(url, timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        return {"items": [], "status": "0", "info": str(exc)}
    pois = payload.get("pois") if isinstance(payload.get("pois"), list) else []
    return {
        "items": [_normalize_amap_poi(poi) for poi in pois],
        "status": payload.get("status", "0"),
        "info": payload.get("info", ""),
        "count": int(payload.get("count") or 0),
    }


def _normalize_amap_poi(poi):
    lng, lat = _split_location(poi.get("location", ""))
    tags = [part for part in (poi.get("type") or "风景名胜").split(";") if part]
    name = poi.get("name") or "高德景点"
    address = poi.get("address")
    if isinstance(address, list):
        address = ""
    return {
        "id": f"amap-{poi.get('id') or name}",
        "source": "amap",
        "source_id": poi.get("id", ""),
        "name": name,
        "province": poi.get("pname") or "",
        "city": poi.get("cityname") or "",
        "district": poi.get("adname") or "",
        "level": "高德POI",
        "rating": 4.5,
        "address": address or "",
        "latitude": lat,
        "longitude": lng,
        "summary": f"{' / '.join(tags[:3])} · 高德 Web 服务补充结果",
        "description": "",
        "tags": tags[:4],
        "ticket_price": "以景区公示为准",
        "opening_hours": "以景区公示为准",
        "cover_image_url": "",
        "map_url": amap_marker_url(name, lng, lat),
    }


def _split_location(location):
    if not location or "," not in location:
        return None, None
    lng, lat = location.split(",", 1)
    try:
        return float(lng), float(lat)
    except ValueError:
        return None, None
