"""Full-site search service: suggestions, unified results, hot searches, history."""
import json
import re
from datetime import datetime

from app.core.database import get_db, row_to_dict, rows_to_list
from app.services.scenic_service import list_scenic


# ─── Search Correction ───

COMMON_TYPOS = {
    "杭洲": "杭州", "杭洲西湖": "杭州西湖",
    "黄三": "黄山", "簧山": "黄山",
    "柱林": "桂林", "桂林离江": "桂林漓江",
    "丽水古城": "丽江古城", "理江": "丽江",
    "西双版纳": "西双版纳",
    "張家界": "张家界", "張家介": "张家界",
    "九寨构": "九寨沟", "九寨勾": "九寨沟",
    "北景": "北京", "北鲸": "北京",
    "上诲": "上海", "上嗨": "上海",
    "深川": "深圳", "深训": "深圳",
    "三涯": "三亚", "山亚": "三亚",
    "西按": "西安", "希安": "西安",
    "成读": "成都", "成嘟": "成都",
    "度桥": "断桥", "雷锋塔": "雷峰塔",
}


def correct_keyword(keyword: str) -> str | None:
    """Return corrected keyword if a known typo is found, else None."""
    k = keyword.strip()
    if k in COMMON_TYPOS:
        return COMMON_TYPOS[k]
    return None


# ─── Search Suggestions ───

THEMES = [
    "徒步", "摄影", "古迹", "美食", "自驾", "亲子",
    "避暑", "赏花", "看雪", "自然风光", "人文古迹",
    "湖光山色", "世界文化遗产", "5A景区", "4A景区",
]


def get_suggestions(keyword: str, limit: int = 8) -> list[dict]:
    """Return autocomplete suggestions grouped by type."""
    if not keyword or len(keyword.strip()) < 1:
        return []
    q = keyword.strip()
    like = f"%{q}%"
    suggestions = []

    with get_db() as db:
        # Scenic spots
        spots = db.execute(
            "SELECT id, name, province, city, level FROM scenic_spots WHERE name LIKE ? ORDER BY rating DESC LIMIT 5",
            (like,),
        ).fetchall()
        for row in spots:
            suggestions.append({
                "type": "scenic",
                "id": row["id"],
                "text": row["name"],
                "subtitle": f"{row['province']} {row['city']}",
                "level": row["level"] or "",
                "url": f"/scenic/{row['id']}",
            })

        # Cities
        cities = db.execute(
            "SELECT DISTINCT city, province FROM scenic_spots WHERE city LIKE ? OR province LIKE ? GROUP BY city ORDER BY COUNT(*) DESC LIMIT 3",
            (like, like),
        ).fetchall()
        for row in cities:
            suggestions.append({
                "type": "city",
                "text": row["city"],
                "subtitle": row["province"],
                "url": f"/destinations?city={row['city']}",
            })

        # Themes
        for t in THEMES:
            if q in t or t in q:
                suggestions.append({
                    "type": "theme",
                    "text": t,
                    "subtitle": "主题旅行",
                    "url": f"/themes/{t}",
                })
                if sum(1 for s in suggestions if s["type"] == "theme") >= 3:
                    break

        # Provinces
        provinces = db.execute(
            "SELECT DISTINCT province FROM scenic_spots WHERE province LIKE ? ORDER BY province LIMIT 2",
            (like,),
        ).fetchall()
        for row in provinces:
            suggestions.append({
                "type": "province",
                "text": row["province"],
                "subtitle": "省份",
                "url": f"/provinces/{row['province']}",
            })

    return suggestions[:limit]


# ─── Unified Search ───

def unified_search(keyword: str, category: str = "all", limit: int = 20, offset: int = 0) -> dict:
    """Search across scenic, cities, themes, and community posts."""
    q = keyword.strip()
    result = {
        "keyword": q,
        "correction": correct_keyword(q),
        "total": 0,
        "categories": {},
        "items": [],
    }

    if category in ("all", "scenic"):
        scenic_items = list_scenic(q=q, limit=limit, offset=offset)
        scenic_group = {
            "label": "景区",
            "count": len(scenic_items),
            "items": scenic_items[:limit],
        }
        result["categories"]["scenic"] = scenic_group
        result["total"] += scenic_group["count"]

    if category in ("all", "city"):
        city_items = _search_cities(q)
        city_group = {
            "label": "城市",
            "count": len(city_items),
            "items": city_items[:10],
        }
        result["categories"]["city"] = city_group
        result["total"] += city_group["count"]

    if category in ("all", "theme"):
        theme_items = _search_themes(q)
        theme_group = {
            "label": "主题",
            "count": len(theme_items),
            "items": theme_items[:8],
        }
        result["categories"]["theme"] = theme_group
        result["total"] += theme_group["count"]

    if category in ("all", "route"):
        route_items = _search_routes(q)
        route_group = {
            "label": "路线",
            "count": len(route_items),
            "items": route_items[:8],
        }
        result["categories"]["route"] = route_group
        result["total"] += route_group["count"]

    if category in ("all", "community"):
        post_items = _search_community(q)
        community_group = {
            "label": "攻略",
            "count": len(post_items),
            "items": post_items[:8],
        }
        result["categories"]["community"] = community_group
        result["total"] += community_group["count"]

    # Mixed flat items for "all" view (interleaved)
    if category == "all":
        mixed = []
        for cat_key in ("scenic", "city", "theme", "route", "community"):
            cat_data = result["categories"].get(cat_key, {})
            for item in cat_data.get("items", [])[:3]:
                item_copy = dict(item)
                item_copy["_category"] = cat_key
                mixed.append(item_copy)
        result["items"] = mixed

    return result


def _search_cities(q: str) -> list[dict]:
    like = f"%{q}%"
    with get_db() as db:
        rows = db.execute(
            """
            SELECT city, province, COUNT(*) AS scenic_count
            FROM scenic_spots
            WHERE city LIKE ? OR province LIKE ?
            GROUP BY city, province
            ORDER BY scenic_count DESC
            LIMIT 10
            """,
            (like, like),
        ).fetchall()
    return [{"text": r["city"], "province": r["province"], "scenic_count": r["scenic_count"], "url": f"/destinations?city={r['city']}"} for r in rows]


def _search_themes(q: str) -> list[dict]:
    matched = [t for t in THEMES if q in t or t in q]
    if not matched:
        # Fuzzy: check each character
        for t in THEMES:
            if any(ch in t for ch in q) and t not in matched:
                matched.append(t)
    return [{"text": t, "subtitle": "主题旅行", "url": f"/themes/{t}"} for t in matched[:8]]


def _search_routes(q: str) -> list[dict]:
    like = f"%{q}%"
    with get_db() as db:
        rows = db.execute(
            """
            SELECT DISTINCT s.name AS scenic_name, s.province, s.city,
                   json_extract(s.recommended_routes, '$') AS routes
            FROM scenic_spots s
            WHERE s.name LIKE ? OR s.city LIKE ? OR s.tags LIKE ?
            LIMIT 10
            """,
            (like, like, like),
        ).fetchall()
    routes = []
    for r in rows:
        try:
            route_list = json.loads(r["routes"]) if r["routes"] else []
        except (json.JSONDecodeError, TypeError):
            route_list = []
        for route_name in route_list[:2]:
            routes.append({
                "text": f"{r['scenic_name']} - {route_name}",
                "scenic": r["scenic_name"],
                "province": r["province"],
                "url": f"/trip-planning?to={r['scenic_name']}",
            })
    return routes[:8]


def _search_community(q: str) -> list[dict]:
    like = f"%{q}%"
    with get_db() as db:
        rows = db.execute(
            "SELECT id, title, nickname, category, likes, created_at FROM community_posts WHERE (title LIKE ? OR content LIKE ?) AND status='approved' ORDER BY likes DESC LIMIT 8",
            (like, like),
        ).fetchall()
    return [{"id": r["id"], "text": r["title"], "author": r["nickname"], "category": r["category"], "likes": r["likes"], "url": f"/community"} for r in rows]


# ─── No-Result Recommendations ───

def get_no_result_recommendations(keyword: str) -> dict:
    """Return fallback recommendations when search has no results."""
    q = keyword.strip()
    recommendations = {
        "nearby_cities": [],
        "popular_scenic": [],
        "themes": [],
    }

    # Try to find a city from the keyword
    with get_db() as db:
        # Match partial city name
        city_match = db.execute(
            "SELECT DISTINCT city, province FROM scenic_spots WHERE city LIKE ? LIMIT 3",
            (f"%{q[:2]}%",),
        ).fetchall()
        recommendations["nearby_cities"] = [
            {"text": r["city"], "province": r["province"], "url": f"/destinations?city={r['city']}"} for r in city_match
        ]

        # Always show popular scenic
        popular = db.execute(
            "SELECT id, name, province, city, level FROM scenic_spots ORDER BY rating DESC LIMIT 6",
        ).fetchall()
        recommendations["popular_scenic"] = [
            {"id": r["id"], "name": r["name"], "province": r["province"], "city": r["city"], "level": r["level"], "url": f"/scenic/{r['id']}"} for r in popular
        ]

    # Suggest themes
    recommendations["themes"] = [
        {"text": "自然风光", "url": "/themes/自然风光"},
        {"text": "人文古迹", "url": "/themes/人文古迹"},
        {"text": "摄影打卡", "url": "/themes/摄影打卡"},
        {"text": "亲子旅行", "url": "/themes/亲子乐园"},
    ]

    return recommendations


# ─── Hot Searches ───

def get_hot_searches(category: str = "", limit: int = 10) -> list[dict]:
    """Return trending search keywords."""
    with get_db() as db:
        if category:
            rows = db.execute(
                "SELECT keyword, category, search_count FROM hot_searches WHERE category=? ORDER BY search_count DESC, id ASC LIMIT ?",
                (category, limit),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT keyword, category, search_count FROM hot_searches ORDER BY search_count DESC, id ASC LIMIT ?",
                (limit,),
            ).fetchall()
    return [{"keyword": r["keyword"], "category": r["category"], "count": r["search_count"]} for r in rows]


def increment_hot_search(keyword: str, category: str = "scenic"):
    """Increment search count for a keyword, or create new entry."""
    if not keyword or len(keyword.strip()) < 2:
        return
    k = keyword.strip()
    with get_db() as db:
        db.execute(
            """
            INSERT INTO hot_searches (keyword, category, search_count, is_manual)
            VALUES (?, ?, 1, 0)
            ON CONFLICT(keyword) DO UPDATE SET search_count = search_count + 1, updated_at = CURRENT_TIMESTAMP
            """,
            (k, category),
        )


# ─── Search History ───

def save_search_history(user_id: int, keyword: str, result_count: int = 0):
    """Save a search query to user's history."""
    if not keyword or len(keyword.strip()) < 1:
        return
    k = keyword.strip()
    with get_db() as db:
        # Deduplicate: remove same keyword from same user, keep only latest
        db.execute("DELETE FROM search_history WHERE user_id=? AND keyword=?", (user_id, k))
        db.execute(
            "INSERT INTO search_history (user_id, keyword, result_count) VALUES (?,?,?)",
            (user_id, k, result_count),
        )
        # Keep only last 50 per user
        db.execute(
            "DELETE FROM search_history WHERE user_id=? AND id NOT IN (SELECT id FROM search_history WHERE user_id=? ORDER BY created_at DESC LIMIT 50)",
            (user_id, user_id),
        )


def get_search_history(user_id: int, limit: int = 20) -> list[dict]:
    """Get user's recent search history."""
    with get_db() as db:
        rows = db.execute(
            "SELECT keyword, result_count, created_at FROM search_history WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [{"keyword": r["keyword"], "result_count": r["result_count"], "created_at": r["created_at"]} for r in rows]


def clear_search_history(user_id: int):
    """Clear all search history for a user."""
    with get_db() as db:
        db.execute("DELETE FROM search_history WHERE user_id=?", (user_id,))
