import json

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from app.core.auth import get_current_user, require_user
from app.core.database import get_db, rows_to_list
from app.core.response import ok
from app.core.sanitize import sanitize_comment, sanitize_html

router = APIRouter()


class CommentCreate(BaseModel):
    scenic_id: int = 1
    content: str
    rating: float = 5


class CommunityPostCreate(BaseModel):
    scenic_id: int = 1
    category: str = "点评"
    title: str = ""
    content: str
    images: list[str] = []


@router.get("/comments")
def comments_list(scenic_id: int | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    sql = "SELECT * FROM comments WHERE status IN ('approved','pending')"
    params = []
    if scenic_id:
        sql += " AND scenic_id = ?"
        params.append(scenic_id)
    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) as c")
    with get_db() as db:
        total = db.execute(count_sql, params).fetchone()["c"]
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, (page - 1) * limit])
        rows = rows_to_list(db.execute(sql, params).fetchall())
    return ok({"items": rows, "total": total, "page": page, "limit": limit})


@router.post("/comments")
def create_comment(payload: CommentCreate, user: dict = Depends(require_user)):
    cleaned, error = sanitize_comment(payload.content)
    if error:
        return ok({"status": "rejected"}, error)
    # Rate limiting: max 5 comments per minute per user
    with get_db() as db:
        from datetime import datetime, timedelta, timezone
        one_min_ago = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
        recent = db.execute("SELECT COUNT(*) c FROM comments WHERE user_id=? AND created_at>?", (user["id"], one_min_ago)).fetchone()["c"]
        if recent >= 5:
            return ok({"status": "rate_limited"}, "评论过于频繁，请稍后再试")
        cur = db.execute(
            "INSERT INTO comments (scenic_id,user_id,nickname,content,rating,status,images,ip) VALUES (?,?,?,?,?,?,?,?)",
            (payload.scenic_id, user["id"], user.get("nickname", "用户"), cleaned, payload.rating, "pending", "[]", "0.0.0.0"),
        )
    return ok({"id": cur.lastrowid, "status": "pending"}, "评论已提交，等待审核")


@router.get("/community/posts")
def community_posts(category: str | None = None, status: str | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100)):
    sql = "SELECT * FROM community_posts WHERE status IN ('approved','pending')"
    params = []
    if category and category != "全部":
        sql += " AND category=?"
        params.append(category)
    if status:
        sql += " AND status=?"
        params.append(status)
    count_sql = sql.replace("SELECT *", "SELECT COUNT(*) as c")
    with get_db() as db:
        total = db.execute(count_sql, params).fetchone()["c"]
        sql += " ORDER BY id DESC LIMIT ? OFFSET ?"
        params.extend([limit, (page - 1) * limit])
        rows = rows_to_list(db.execute(sql, params).fetchall())
    return ok({"items": rows, "total": total, "page": page, "limit": limit})


@router.post("/community/posts")
def create_community_post(payload: CommunityPostCreate, user: dict = Depends(require_user)):
    cleaned, error = sanitize_comment(payload.content)
    if error:
        return ok({"status": "rejected"}, error)
    title = sanitize_html(payload.title)[:200] if payload.title else ""
    with get_db() as db:
        cur = db.execute(
            """
            INSERT INTO community_posts (user_id,scenic_id,nickname,category,title,content,images,status,likes,reports)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            """,
            (user["id"], payload.scenic_id, user.get("nickname", "用户"), payload.category, title, cleaned, json.dumps(payload.images, ensure_ascii=False), "pending", 0, 0),
        )
    return ok({"id": cur.lastrowid, "status": "pending"}, "内容已提交审核")


@router.post("/community/posts/{post_id}/like")
def like_community_post(post_id: int):
    with get_db() as db:
        db.execute("UPDATE community_posts SET likes=likes+1 WHERE id=?", (post_id,))
        row = db.execute("SELECT id, likes FROM community_posts WHERE id=?", (post_id,)).fetchone()
    return ok(dict(row) if row else {"id": post_id, "likes": 0}, "已点赞")


@router.post("/community/posts/{post_id}/report")
def report_community_post(post_id: int):
    with get_db() as db:
        db.execute("UPDATE community_posts SET reports=reports+1 WHERE id=?", (post_id,))
        row = db.execute("SELECT id, reports FROM community_posts WHERE id=?", (post_id,)).fetchone()
    return ok(dict(row) if row else {"id": post_id, "reports": 0}, "举报已记录")
