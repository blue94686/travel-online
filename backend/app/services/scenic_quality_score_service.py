import json


def _has_value(value):
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, (list, tuple, dict)):
        return bool(value)
    text = str(value).strip()
    return text not in ("", "[]", "{}")


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


def calculate_completeness_score(scenic: dict) -> int:
    score = 0
    if _has_value(scenic.get("name")):
        score += 5
    if _has_value(scenic.get("province")) and _has_value(scenic.get("city")) and _has_value(scenic.get("district")):
        score += 10
    if _has_value(scenic.get("address")):
        score += 10
    if _has_value(scenic.get("latitude")) and _has_value(scenic.get("longitude")):
        score += 10
    if _has_value(scenic.get("summary")):
        score += 10
    if _has_value(scenic.get("description")):
        score += 15
    if _has_value(scenic.get("cover_image_url")):
        score += 10
    if len(_json_list(scenic.get("gallery"))) >= 3:
        score += 10
    if _has_value(scenic.get("official_website")):
        score += 5
    if _has_value(scenic.get("opening_hours")):
        score += 5
    if _has_value(scenic.get("ticket_price")):
        score += 5
    if _json_list(scenic.get("nearby_pois")) or _json_list(scenic.get("linked_scenic_recommendations")):
        score += 5
    if _has_value(scenic.get("slogan")) and _has_value(scenic.get("recommended_duration")):
        score += 5
    if _has_value(scenic.get("history_culture")) and _has_value(scenic.get("highlights")):
        score += 5
    if _has_value(scenic.get("traffic_info")) or _has_value(scenic.get("public_transport")):
        score += 5
    if _json_list(scenic.get("travel_tips")) and _json_list(scenic.get("must_see_spots")):
        score += 5
    return min(score, 100)


def score_level(score: int) -> str:
    if score < 60:
        return "低完整度"
    if score < 80:
        return "基本完整"
    return "优质资料"
