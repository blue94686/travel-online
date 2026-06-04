import json
from datetime import datetime

from app.services.scenic_quality_score_service import calculate_completeness_score


FIELD_MAP = {
    "summary": "summary",
    "summary_short": "summary",
    "summary_full": "description",
    "official_site": "official_website",
    "ticket": "ticket_price",
    "opening_hours": "opening_hours",
    "address": "address",
    "traffic": "traffic_info",
    "history": "history_culture",
    "highlights": "highlights",
    "tips": "travel_tips",
    "phone": "phone",
    "coordinate": "map_point",
    "poi": "nearby_pois",
    "slogan": "slogan",
}

JSON_FIELDS = {"travel_tips", "nearby_pois", "must_see_spots", "recommended_itinerary", "photo_spots", "nearby_food", "nearby_hotels", "linked_scenic_recommendations"}


def build_diff(scenic: dict, candidate: dict) -> dict:
    field = FIELD_MAP.get(candidate["candidate_type"], candidate["candidate_type"])
    return {
        "field": field,
        "old": scenic.get(field),
        "new": candidate.get("content"),
        "source_url": candidate.get("source_url"),
        "source_type": candidate.get("source_type"),
        "confidence": candidate.get("confidence"),
        "risk_level": candidate.get("risk_level"),
    }


def merge_approved_candidates(db, scenic_id: int) -> dict:
    scenic = db.execute("SELECT * FROM scenic_spots WHERE id=?", (scenic_id,)).fetchone()
    if not scenic:
        return {"scenic_id": scenic_id, "status": "not_found", "merged_count": 0}
    scenic = dict(scenic)
    candidates = db.execute(
        """
        SELECT * FROM scenic_profile_candidates
        WHERE scenic_id=? AND status='approved'
        ORDER BY confidence DESC, id ASC
        """,
        (scenic_id,),
    ).fetchall()
    merged = []
    for row in candidates:
        candidate = dict(row)
        field = FIELD_MAP.get(candidate["candidate_type"])
        if not field or field in ("map_point",):
            continue
        value = candidate["content"]
        if field in JSON_FIELDS:
            value = json.dumps(_as_list(value), ensure_ascii=False)
        db.execute(f"UPDATE scenic_spots SET {field}=? WHERE id=?", (value, scenic_id))
        db.execute(
            "UPDATE scenic_profile_candidates SET status='merged', reviewed_at=COALESCE(reviewed_at, CURRENT_TIMESTAMP) WHERE id=?",
            (candidate["id"],),
        )
        merged.append({"candidate_id": candidate["id"], "field": field})
    updated = dict(db.execute("SELECT * FROM scenic_spots WHERE id=?", (scenic_id,)).fetchone())
    score = calculate_completeness_score(updated)
    db.execute(
        "UPDATE scenic_spots SET completeness_score=?, last_enriched_at=? WHERE id=?",
        (score, datetime.now().isoformat(timespec="seconds"), scenic_id),
    )
    return {"scenic_id": scenic_id, "status": "merged", "merged_count": len(merged), "merged": merged, "completeness_score": score}


def _as_list(value):
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return parsed
    except (TypeError, json.JSONDecodeError):
        pass
    return [part.strip() for part in str(value).replace("；", ";").split(";") if part.strip()]
