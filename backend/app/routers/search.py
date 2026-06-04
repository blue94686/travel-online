"""Full-site search API endpoints."""
from fastapi import APIRouter, Depends, Query

from app.core.auth import get_current_user
from app.core.response import ok
from app.services.search_service import (
    clear_search_history,
    get_hot_searches,
    get_no_result_recommendations,
    get_search_history,
    get_suggestions,
    increment_hot_search,
    save_search_history,
    unified_search,
)

router = APIRouter()


@router.get("/search")
def search(
    q: str = Query("", description="搜索关键词"),
    category: str = Query("all", description="分类筛选: all/scenic/city/theme/route/community"),
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
    user: dict | None = Depends(get_current_user),
):
    """Full-site unified search across scenic spots, cities, themes, routes, and community."""
    keyword = q.strip()
    if not keyword:
        return ok({
            "keyword": "",
            "correction": None,
            "total": 0,
            "categories": {},
            "items": [],
            "recommendations": get_no_result_recommendations(""),
        })

    result = unified_search(keyword, category=category, limit=limit, offset=offset)

    # No results → return recommendations
    if result["total"] == 0:
        result["recommendations"] = get_no_result_recommendations(keyword)

    # Save search history for logged-in users
    if user and result["total"] > 0:
        save_search_history(user["id"], keyword, result["total"])

    # Increment hot search counter
    increment_hot_search(keyword)

    return ok(result)


@router.get("/search/suggestions")
def search_suggestions(q: str = Query("", description="输入关键词")):
    """Autocomplete suggestions for search input."""
    return ok(get_suggestions(q))


@router.get("/search/hot")
def hot_searches(category: str = Query("", description="分类: scenic/city/theme"), limit: int = Query(10, ge=1, le=20)):
    """Get trending/hot search keywords."""
    return ok(get_hot_searches(category=category, limit=limit))


@router.get("/user/search-history")
def user_search_history(user: dict | None = Depends(get_current_user)):
    """Get current user's search history. Requires login."""
    if not user:
        return ok([])
    return ok(get_search_history(user["id"]))


@router.delete("/user/search-history")
def delete_search_history(user: dict | None = Depends(get_current_user)):
    """Clear current user's search history. Requires login."""
    if not user:
        return ok({"cleared": False}, "请先登录")
    clear_search_history(user["id"])
    return ok({"cleared": True}, "搜索历史已清空")
