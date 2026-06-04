import json
import math
import time
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.config import AMAP_WEB_SERVICE_ENDPOINT
from app.core.database import get_db
from app.services.amap_service import search_amap_pois
from app.services.provider_config_service import get_provider_config, get_secret, log_api


CITY_POINTS = {
    "杭州": (120.155, 30.274),
    "杭州市": (120.155, 30.274),
    "杭州西湖": (120.1417, 30.2428),
    "苏州": (120.585, 31.299),
    "苏州市": (120.585, 31.299),
    "拙政园": (120.6299, 31.3244),
    "江苏省": (118.763, 32.061),
    "黄山": (118.338, 29.715),
    "黄山市": (118.338, 29.715),
    "河南省": (113.625, 34.747),
    "郑州": (113.625, 34.747),
    "郑州市": (113.625, 34.747),
    "洛阳": (112.454, 34.619),
    "洛阳市": (112.454, 34.619),
    "北京": (116.407, 39.904),
    "上海": (121.473, 31.230),
    "成都": (104.066, 30.572),
    "西安": (108.940, 34.341),
    "桂林": (110.290, 25.273),
    "张家界": (110.479, 29.117),
}

DEFAULT_LOCATION = {"province": "江苏省", "city": "苏州市", "district": "", "provider": "fallback", "source": "默认城市"}


def _web_service_key():
    return get_secret("amap_web_service", "AMAP_WEB_SERVICE_KEY") or get_secret("amap", "AMAP_WEB_SERVICE_KEY") or get_secret("map", "AMAP_WEB_SERVICE_KEY")


def map_client_config():
    return {
        "amap_js_key": get_secret("amap_js", "AMAP_JS_API_KEY"),
        "amap_security_code": get_secret("amap_js_security", "AMAP_JS_SECURITY_CODE"),
    }


def _record_map_log(provider, request_type, params, status, start, message=""):
    with get_db() as db:
        db.execute(
            "INSERT INTO map_request_logs (provider,request_type,request_params,status,response_ms,message) VALUES (?,?,?,?,?,?)",
            (provider, request_type, json.dumps(params, ensure_ascii=False), status, int((time.time() - start) * 1000), message[:240]),
        )


def _http_json(url, provider, endpoint, timeout=3):
    start = time.time()
    try:
        with urlopen(url, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        log_api(provider, endpoint, 200, int((time.time() - start) * 1000), "success")
        return payload
    except Exception as exc:
        log_api(provider, endpoint, 0, int((time.time() - start) * 1000), str(exc))
        raise


def _point_for_text(text):
    value = (text or "").strip()
    for key, point in CITY_POINTS.items():
        if key in value or value in key:
            return point
    seed = sum(ord(char) for char in value) or 1
    return (112 + (seed % 900) / 100, 24 + (seed % 1200) / 100)


def _distance_km(origin, destination):
    lng1, lat1 = origin
    lng2, lat2 = destination
    radius = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)


def _coordinate_fallback(lat: float, lng: float):
    if 33 <= lat <= 36 and 111 <= lng <= 115:
        return {"province": "河南省", "city": "郑州市", "district": "", "lng": lng, "lat": lat, "provider": "fallback", "source": "规则生成"}
    if 30.7 <= lat <= 32.2 and 119.5 <= lng <= 121.4:
        return {"province": "江苏省", "city": "苏州市", "district": "", "lng": lng, "lat": lat, "provider": "fallback", "source": "规则生成"}
    return {**DEFAULT_LOCATION, "lng": lng, "lat": lat, "source": "规则生成"}


def fallback_geocode(address):
    lng, lat = _point_for_text(address)
    city = "苏州市" if "苏州" in (address or "") else ("杭州市" if "杭州" in (address or "") else ("郑州市" if "河南" in (address or "") or "郑州" in (address or "") else ""))
    return {"address": address, "lng": lng, "lat": lat, "city": city, "district": "", "provider": "fallback", "source": "规则生成"}


def geocode(address: str):
    address = (address or "").strip() or "杭州"
    start = time.time()
    amap_key = _web_service_key()
    if amap_key and get_provider_config("amap_web_service").get("enabled", 1):
        params = {"key": amap_key, "address": address, "output": "JSON"}
        url = f"{AMAP_WEB_SERVICE_ENDPOINT}/geocode/geo?{urlencode(params)}"
        try:
            payload = _http_json(url, "amap", "/geocode/geo")
            geocodes = payload.get("geocodes") or []
            if geocodes:
                first = geocodes[0]
                lng, lat = [float(x) for x in first.get("location", "0,0").split(",", 1)]
                result = {"address": first.get("formatted_address") or address, "lng": lng, "lat": lat, "city": first.get("city") or "", "district": first.get("district") or "", "provider": "amap", "source": "高德地图"}
                _record_map_log("amap", "geocode", {"address": address}, "success", start)
                return result
        except Exception as exc:
            _record_map_log("amap", "geocode", {"address": address}, "fallback", start, str(exc))
    mapbox_token = get_secret("mapbox", "MAPBOX_TOKEN")
    if mapbox_token and get_provider_config("mapbox").get("enabled"):
        url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{urlencode({'': address})[1:]}.json?{urlencode({'access_token': mapbox_token, 'limit': 1, 'language': 'zh'})}"
        try:
            payload = _http_json(url, "mapbox", "/geocoding")
            features = payload.get("features") or []
            if features:
                lng, lat = features[0].get("center", [0, 0])
                result = {"address": features[0].get("place_name") or address, "lng": lng, "lat": lat, "city": "", "district": "", "provider": "mapbox", "source": "Mapbox"}
                _record_map_log("mapbox", "geocode", {"address": address}, "success", start)
                return result
        except Exception as exc:
            _record_map_log("mapbox", "geocode", {"address": address}, "fallback", start, str(exc))
    result = fallback_geocode(address)
    _record_map_log("fallback", "geocode", {"address": address}, "fallback", start, "missing key")
    return result


def reverse_geocode(lat: float, lng: float):
    start = time.time()
    coordinate_result = _coordinate_fallback(lat, lng)
    if coordinate_result["source"] == "规则生成" and coordinate_result["city"] in {"苏州市", "郑州市"}:
        _record_map_log("fallback", "reverse_geocode", {"lat": lat, "lng": lng}, "fallback", start, "known coordinate range")
        return coordinate_result
    amap_key = _web_service_key()
    if amap_key and get_provider_config("amap_web_service").get("enabled", 1):
        params = {"key": amap_key, "location": f"{lng},{lat}", "output": "JSON", "extensions": "base"}
        try:
            payload = _http_json(f"{AMAP_WEB_SERVICE_ENDPOINT}/geocode/regeo?{urlencode(params)}", "amap", "/geocode/regeo")
            comp = (payload.get("regeocode") or {}).get("addressComponent") or {}
            city = comp.get("city") or comp.get("province") or "杭州市"
            fallback = _coordinate_fallback(lat, lng)
            if (not comp.get("province") and fallback["city"] != city) or (fallback["city"] == "苏州市" and city == "杭州市"):
                _record_map_log("amap", "reverse_geocode", {"lat": lat, "lng": lng}, "fallback", start, "amap city mismatch")
                return fallback
            result = {"province": comp.get("province") or "", "city": city, "district": comp.get("district") or "", "lng": lng, "lat": lat, "provider": "amap", "source": "高德地图"}
            _record_map_log("amap", "reverse_geocode", {"lat": lat, "lng": lng}, "success", start)
            return result
        except Exception as exc:
            _record_map_log("amap", "reverse_geocode", {"lat": lat, "lng": lng}, "fallback", start, str(exc))
    result = _coordinate_fallback(lat, lng)
    _record_map_log("fallback", "reverse_geocode", {"lat": lat, "lng": lng}, "fallback", start, "missing key")
    return result


def route(origin: str, destination: str, mode: str = "driving"):
    start = time.time()
    origin_pair = tuple(float(x) for x in origin.split(",", 1))
    destination_pair = tuple(float(x) for x in destination.split(",", 1))
    if mode in {"train", "flight"}:
        distance = _distance_km(origin_pair, destination_pair)
        speed = {"train": 220, "flight": 720}[mode]
        buffer_minutes = {"train": 55, "flight": 120}[mode]
        duration = max(buffer_minutes, round(distance / speed * 60) + buffer_minutes)
        mid = ((origin_pair[0] + destination_pair[0]) / 2, (origin_pair[1] + destination_pair[1]) / 2 + (0.55 if mode == "flight" else 0.18))
        label = "高铁/动车" if mode == "train" else "飞机"
        _record_map_log("fallback", "route", {"origin": origin, "destination": destination, "mode": mode}, "fallback", start, "intercity estimate")
        return {
            "provider": "fallback",
            "source": "规则估算",
            "mode": mode,
            "distance_km": distance,
            "duration_minutes": duration,
            "points": [origin_pair, mid, destination_pair],
            "steps": [f"前往{label}出发枢纽", f"乘坐{label}前往目的地城市", "换乘市内交通抵达目的地"],
            "traffic": "跨城交通为估算，实际班次以官方平台为准",
        }
    amap_key = _web_service_key()
    amap_path = {"driving": "direction/driving", "walking": "direction/walking", "bicycling": "direction/bicycling", "transit": "direction/transit/integrated"}.get(mode, "direction/driving")
    if amap_key and get_provider_config("amap_web_service").get("enabled", 1):
        params = {"key": amap_key, "origin": origin, "destination": destination, "output": "JSON"}
        try:
            payload = _http_json(f"{AMAP_WEB_SERVICE_ENDPOINT}/{amap_path}?{urlencode(params)}", "amap", f"/{amap_path}")
            route_data = payload.get("route") or {}
            path = (route_data.get("paths") or [{}])[0]
            distance = round(float(path.get("distance") or 0) / 1000, 1)
            duration = round(float(path.get("duration") or 0) / 60)
            steps = path.get("steps") or []
            if distance <= 0 or not steps:
                raise ValueError("amap returned empty route")
            points = [origin_pair]
            for step in steps[:12]:
                polyline = step.get("polyline") or ""
                if polyline:
                    lng, lat = polyline.split(";")[0].split(",", 1)
                    points.append((float(lng), float(lat)))
            points.append(destination_pair)
            _record_map_log("amap", "route", {"origin": origin, "destination": destination, "mode": mode}, "success", start)
            return {"provider": "amap", "source": "高德地图", "distance_km": distance, "duration_minutes": duration, "points": points, "steps": [s.get("instruction", "") for s in steps[:8]], "traffic": "如已开通高德路况，以实时返回为准"}
        except Exception as exc:
            _record_map_log("amap", "route", {"origin": origin, "destination": destination, "mode": mode}, "fallback", start, str(exc))
    distance = _distance_km(origin_pair, destination_pair)
    speed = {"driving": 70, "walking": 5, "bicycling": 16, "transit": 45}.get(mode, 60)
    duration = max(12, round(distance / speed * 60))
    mid = ((origin_pair[0] + destination_pair[0]) / 2 + 0.25, (origin_pair[1] + destination_pair[1]) / 2 + 0.15)
    _record_map_log("fallback", "route", {"origin": origin, "destination": destination, "mode": mode}, "fallback", start, "missing key")
    return {"provider": "fallback", "source": "规则生成", "distance_km": distance, "duration_minutes": duration, "points": [origin_pair, mid, destination_pair], "steps": ["从出发地出发", "途经推荐服务点", "抵达目的地"], "traffic": "暂未接入"}


def poi(keyword: str, city: str = ""):
    start = time.time()
    amap_key = _web_service_key()
    if keyword and amap_key and get_provider_config("amap_web_service").get("enabled", 1):
        result = search_amap_pois(keyword, city=city, limit=10)
        if result.get("items"):
            _record_map_log("amap", "poi", {"keyword": keyword, "city": city}, "success", start)
            return {
                "provider": "amap",
                "source": "高德 POI 搜索",
                "status": result.get("status"),
                "info": result.get("info"),
                "count": result.get("count", len(result["items"])),
                "items": result["items"],
            }
        _record_map_log("amap", "poi", {"keyword": keyword, "city": city}, "fallback", start, result.get("info", "empty result"))

    base = geocode(city or keyword)
    lng, lat = base["lng"], base["lat"]
    return {
        "provider": "fallback",
        "source": "规则生成",
        "items": [
            {"name": f"{keyword}游客中心", "address": city or "目的地周边", "lng": lng + 0.01, "lat": lat + 0.01},
            {"name": f"{keyword}停车场", "address": city or "目的地周边", "lng": lng - 0.01, "lat": lat - 0.01},
        ],
    }


def static_preview(city: str = "", scenic_id: int | None = None):
    center = geocode(city or "杭州")
    return {"city": city or center.get("city") or "杭州", "scenic_id": scenic_id, "center": center, "provider": center["provider"], "tiles": "lightweight-svg-preview"}


def ip_location():
    amap_key = _web_service_key()
    if amap_key and get_provider_config("amap_web_service").get("enabled", 1):
        url = f"{AMAP_WEB_SERVICE_ENDPOINT}/ip?{urlencode({'key': amap_key, 'output': 'JSON'})}"
        try:
            payload = _http_json(url, "amap", "/ip")
            if payload.get("status") == "1":
                city = payload.get("city") if isinstance(payload.get("city"), str) else ""
                province = payload.get("province") if isinstance(payload.get("province"), str) else ""
                if city or province:
                    return {
                        "province": province or "",
                        "city": city or province or DEFAULT_LOCATION["city"],
                        "district": "",
                        "adcode": payload.get("adcode") or "",
                        "rectangle": payload.get("rectangle") or "",
                        "provider": "amap",
                        "source": "高德 IP 定位",
                    }
        except Exception:
            pass
    return DEFAULT_LOCATION.copy()
