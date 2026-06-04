import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import urlopen

from app.core.database import get_db, row_to_dict, rows_to_list
from app.services.provider_config_service import get_provider_config, get_secret, log_api


CITY_WEATHER = {
    "杭州": (24, "多云", "优 32"),
    "杭州市": (24, "多云", "优 32"),
    "苏州": (25, "多云", "优 34"),
    "苏州市": (25, "多云", "优 34"),
    "北京": (22, "晴", "良 46"),
    "北京市": (22, "晴", "良 46"),
    "上海": (25, "阴", "良 52"),
    "广州": (29, "阵雨", "优 38"),
    "成都": (23, "小雨", "良 58"),
    "西安": (27, "晴", "良 49"),
    "黄山": (21, "多云", "优 35"),
    "张家界": (22, "小雨", "优 40"),
    "桂林": (27, "阵雨", "优 36"),
    "丽江": (20, "晴", "优 28"),
    "郑州": (26, "晴", "良 55"),
    "郑州市": (26, "晴", "良 55"),
    "洛阳": (25, "多云", "良 53"),
    "河南省": (26, "晴", "良 55"),
}


def _now():
    return datetime.now(timezone.utc)


def _fallback(city: str):
    temp, condition, air = CITY_WEATHER.get(city, CITY_WEATHER.get(city.replace("市", ""), (23 + len(city) % 7, "多云", "良 50")))
    forecast = []
    labels = ["今天", "明天", "周日", "周一", "周二", "周三", "周四"]
    conditions = [condition, "晴", "多云", "阵雨" if temp > 25 else "阴", "多云", "晴", "小雨" if "雨" in condition else "晴"]
    for index, label in enumerate(labels):
        low = temp - 4 + (index % 2)
        high = temp + 2 + (index % 3)
        forecast.append({"day": label, "temp": f"{low}-{high}°C", "condition": conditions[index]})
    advice = build_advice({"temp": temp, "condition": condition, "air": air, "wind": "东北风 2级"})
    return {
        "city": city,
        "current": {"temp": temp, "condition": condition, "feelsLike": temp + 1, "humidity": f"{58 + len(city) % 20}%", "wind": "东北风 2级", "air": air},
        "forecast": forecast,
        "travelAdvice": advice,
        "source": "fallback",
        "provider": "演示数据",
    }


def build_advice(current):
    condition = current.get("condition", "")
    temp = int(current.get("temp") or 24)
    air = current.get("air", "")
    advice = []
    if "雨" in condition:
        advice.extend(["带伞出行，山地和石阶线路注意防滑。", "优先选择短线景区和室内展馆。"])
    if temp >= 30:
        advice.append("高温时段注意防晒补水，避开正午长距离徒步。")
    if "风" in current.get("wind", "") and any(token in current.get("wind", "") for token in ["5级", "6级", "7级"]):
        advice.append("大风天气减少高山、索道和临水线路。")
    if "差" in air or "轻度" in air:
        advice.append("空气质量一般时减少高强度户外活动。")
    if not advice:
        advice = ["上午适合户外步行和拍照。", "午后注意补水，傍晚适合看日落。", "出发前再次确认景区开放时间。"]
    return advice


def _extend_forecast(city, forecast):
    items = list(forecast or [])
    if len(items) >= 7:
        return items[:7]
    fallback = _fallback(city)["forecast"]
    existing = {item.get("day") for item in items}
    for item in fallback:
        if len(items) >= 7:
            break
        if item.get("day") not in existing:
            items.append(item)
    return items[:7]


def _cache_get(city, provider):
    with get_db() as db:
        row = db.execute("SELECT * FROM weather_cache WHERE city=? AND provider=?", (city, provider)).fetchone()
    item = row_to_dict(row) if row else None
    if not item or not item.get("expires_at"):
        return None
    try:
        if datetime.fromisoformat(item["expires_at"]) < _now():
            return None
    except ValueError:
        return None
    return {
        "city": city,
        "current": item.get("weather_json") or {},
        "forecast": _extend_forecast(city, item.get("forecast_json") or []),
        "live": item.get("live_json") or [],
        "source": item.get("source") or provider,
        "provider": {"amap_weather": "高德天气", "qweather": "和风天气", "fallback": "演示数据"}.get(provider, provider),
        "travelAdvice": build_advice(item.get("weather_json") or {}),
    }


def _cache_set(city, provider, weather, forecast, live, source, minutes=30):
    expires = (_now() + timedelta(minutes=minutes)).isoformat()
    with get_db() as db:
        db.execute(
            """
            INSERT INTO weather_cache (city,provider,weather_json,forecast_json,live_json,source,expires_at,updated_at)
            VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(city,provider) DO UPDATE SET weather_json=excluded.weather_json,forecast_json=excluded.forecast_json,
            live_json=excluded.live_json,source=excluded.source,expires_at=excluded.expires_at,updated_at=CURRENT_TIMESTAMP
            """,
            (city, provider, json.dumps(weather, ensure_ascii=False), json.dumps(forecast, ensure_ascii=False), json.dumps(live, ensure_ascii=False), source, expires),
        )


def weather_for(city: str = "杭州"):
    city = (city or "杭州").strip()
    provider = "qweather" if get_secret("qweather", "QWEATHER_KEY") else ("amap_weather" if get_secret("amap_weather", "AMAP_WEATHER_KEY") or get_secret("weather", "AMAP_WEATHER_KEY") else "fallback")
    cached = _cache_get(city, provider)
    if cached:
        return cached
    if provider != "fallback":
        try:
            data = _fetch_provider(city, provider)
            data["forecast"] = _extend_forecast(city, data.get("forecast", []))
            _cache_set(city, provider, data["current"], data["forecast"], data.get("live", []), data["source"], int(get_provider_config(provider).get("settings", {}).get("cache_minutes", 30) or 30))
            return data
        except Exception:
            pass
    data = _fallback(city)
    _cache_set(city, "fallback", data["current"], data["forecast"], [], "fallback", 20)
    return data


def _fetch_provider(city, provider):
    start = time.time()
    if provider == "qweather":
        key = get_secret("qweather", "QWEATHER_KEY")
        location_url = f"https://geoapi.qweather.com/v2/city/lookup?{urlencode({'location': city, 'key': key})}"
        with urlopen(location_url, timeout=6) as response:
            location_payload = json.loads(response.read().decode("utf-8"))
        location_id = ((location_payload.get("location") or [{}])[0]).get("id") or city
        now_url = f"https://devapi.qweather.com/v7/weather/now?{urlencode({'location': location_id, 'key': key})}"
        with urlopen(now_url, timeout=6) as response:
            now_payload = json.loads(response.read().decode("utf-8"))
        now = now_payload.get("now") or {}
        current = {"temp": int(now.get("temp") or 24), "condition": now.get("text") or "多云", "feelsLike": now.get("feelsLike") or "", "humidity": f"{now.get('humidity', '')}%", "wind": f"{now.get('windDir', '')} {now.get('windScale', '')}级", "air": "暂未接入"}
        log_api("qweather", "/v7/weather/now", 200, int((time.time() - start) * 1000), "success")
        fallback = _fallback(city)
        return {"city": city, "current": current, "forecast": fallback["forecast"], "travelAdvice": build_advice(current), "source": "qweather", "provider": "和风天气"}
    key = get_secret("amap_weather", "AMAP_WEATHER_KEY") or get_secret("weather", "AMAP_WEATHER_KEY")
    url = f"https://restapi.amap.com/v3/weather/weatherInfo?{urlencode({'city': city, 'key': key, 'extensions': 'all', 'output': 'JSON'})}"
    with urlopen(url, timeout=6) as response:
        payload = json.loads(response.read().decode("utf-8"))
    forecasts = payload.get("forecasts") or []
    casts = (forecasts[0].get("casts") if forecasts else []) or []
    forecast = [{"day": cast.get("date", ""), "temp": f"{cast.get('nighttemp')}-{cast.get('daytemp')}°C", "condition": cast.get("dayweather") or ""} for cast in casts[:7]]
    current = _fallback(city)["current"]
    if forecast:
        current["condition"] = forecast[0]["condition"]
    log_api("amap_weather", "/v3/weather/weatherInfo", 200, int((time.time() - start) * 1000), "success")
    return {"city": city, "current": current, "forecast": _extend_forecast(city, forecast), "travelAdvice": build_advice(current), "source": "amap_weather", "provider": "高德天气"}


def weather_live(city: str = "杭州"):
    with get_db() as db:
        rows = rows_to_list(db.execute(
            "SELECT * FROM earth_online_sources WHERE review_status='approved' AND category='weather_earth' ORDER BY id LIMIT 4"
        ).fetchall())
    return [
        {"id": row["id"], "city": city, "title": row["name"], "scenic": row["description"], "source": row["source_platform"], "url": row["source_url"], "image": row.get("thumbnail_url") or ""}
        for row in rows
    ] or [{"id": 0, "city": city, "title": f"{city}天气地球观察", "scenic": "公开天气地球来源", "source": "地球 Online", "url": "/earth-online?category=weather_earth", "image": ""}]


def route_weather(cities: list[str]):
    return [{"city": city, **weather_for(city)} for city in cities if city]
