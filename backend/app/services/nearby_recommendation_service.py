from math import atan2, cos, radians, sin, sqrt

from app.core.database import get_db, rows_to_list
from app.services.audit_service import write_audit


def distance_km(a, b):
    if not a.get("latitude") or not a.get("longitude") or not b.get("latitude") or not b.get("longitude"):
        return None
    radius = 6371
    dlat = radians(float(b["latitude"]) - float(a["latitude"]))
    dlng = radians(float(b["longitude"]) - float(a["longitude"]))
    lat1 = radians(float(a["latitude"]))
    lat2 = radians(float(b["latitude"]))
    h = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlng / 2) ** 2
    return 2 * radius * atan2(sqrt(h), sqrt(1 - h))


def recommendation_reason(base, item, distance):
    if base["city"] == item["city"]:
        return "同城顺路，适合串联一日游"
    if base["province"] == item["province"]:
        return "同省周边，适合作为延伸行程"
    if distance is not None and distance < 80:
        return "距离较近，适合周边短途"
    if item.get("rating", 0) >= 4.8:
        return "高评分目的地，适合精选推荐"
    return "主题相近，可作为备选目的地"


def generate_nearby(scenic_id: int, limit: int = 6):
    with get_db() as db:
        base = db.execute("SELECT * FROM scenic_spots WHERE id=?", (scenic_id,)).fetchone()
        if not base:
            return []
        base = dict(base)
        candidates = [dict(row) for row in db.execute("SELECT * FROM scenic_spots WHERE id<>?", (scenic_id,)).fetchall()]
        scored = []
        for item in candidates:
            distance = distance_km(base, item)
            score = 0
            if base["district"] == item["district"]:
                score += 45
            if base["city"] == item["city"]:
                score += 35
            if base["province"] == item["province"]:
                score += 18
            if distance is not None:
                score += max(0, 35 - min(distance, 350) / 10)
            score += float(item.get("rating") or 0) * 5
            scored.append((score, distance, item))
        scored.sort(key=lambda entry: entry[0], reverse=True)
        db.execute("DELETE FROM nearby_recommendations WHERE scenic_id=?", (scenic_id,))
        for score, distance, item in scored[:limit]:
            db.execute(
                """
                INSERT INTO nearby_recommendations
                (scenic_id,recommended_scenic_id,reason,distance_text,score,source)
                VALUES (?,?,?,?,?,?)
                """,
                (
                    scenic_id,
                    item["id"],
                    recommendation_reason(base, item, distance),
                    f"{distance:.1f} km" if distance is not None else "同城/同省推荐",
                    round(score, 2),
                    "rule",
                ),
            )
    write_audit("附近推荐", f"生成景区 #{scenic_id} 附近推荐")
    return get_nearby(scenic_id)


def get_nearby(scenic_id: int):
    with get_db() as db:
        rows = rows_to_list(db.execute(
            """
            SELECT n.*, s.name, s.city, s.district, s.rating, s.cover_image_url, s.summary
            FROM nearby_recommendations n
            JOIN scenic_spots s ON s.id=n.recommended_scenic_id
            WHERE n.scenic_id=?
            ORDER BY n.score DESC, n.id ASC
            """,
            (scenic_id,),
        ).fetchall())
    return rows
