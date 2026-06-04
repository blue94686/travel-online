from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.core.database import get_db, row_to_dict, rows_to_list
from app.core.response import ok
from app.services.audit_service import write_audit

router = APIRouter(prefix="/admin/content", tags=["Admin Content"])

class BannerPayload(BaseModel):
    id: Optional[int] = None
    title: str
    image_url: str
    link_url: str = ""
    order_index: int = 0
    is_active: int = 1

class ArticlePayload(BaseModel):
    id: Optional[int] = None
    title: str
    content: str
    author: str = "管理员"
    category: str = "攻略"
    cover_image: str = ""
    is_published: int = 1

@router.get("/banners")
def get_banners():
    with get_db() as db:
        rows = db.execute("SELECT * FROM banners ORDER BY order_index ASC").fetchall()
        return ok(rows_to_list(rows))

@router.post("/banners")
def create_banner(payload: BannerPayload):
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO banners (title, image_url, link_url, order_index, is_active) VALUES (?, ?, ?, ?, ?)",
            (payload.title, payload.image_url, payload.link_url, payload.order_index, payload.is_active)
        )
        banner_id = cursor.lastrowid
    write_audit("内容管理", f"创建 Banner: {payload.title}")
    return ok({"id": banner_id}, "Banner 已创建")

@router.put("/banners/{banner_id}")
def update_banner(banner_id: int, payload: BannerPayload):
    with get_db() as db:
        db.execute(
            "UPDATE banners SET title=?, image_url=?, link_url=?, order_index=?, is_active=? WHERE id=?",
            (payload.title, payload.image_url, payload.link_url, payload.order_index, payload.is_active, banner_id)
        )
    write_audit("内容管理", f"更新 Banner #{banner_id}")
    return ok({"id": banner_id}, "Banner 已更新")

@router.delete("/banners/{banner_id}")
def delete_banner(banner_id: int):
    with get_db() as db:
        db.execute("DELETE FROM banners WHERE id=?", (banner_id,))
    write_audit("内容管理", f"删除 Banner #{banner_id}")
    return ok({"id": banner_id}, "Banner 已删除")

@router.get("/articles")
def get_articles():
    with get_db() as db:
        rows = db.execute("SELECT * FROM articles ORDER BY created_at DESC").fetchall()
        return ok(rows_to_list(rows))

@router.post("/articles")
def create_article(payload: ArticlePayload):
    with get_db() as db:
        cursor = db.execute(
            "INSERT INTO articles (title, content, author, category, cover_image, is_published) VALUES (?, ?, ?, ?, ?, ?)",
            (payload.title, payload.content, payload.author, payload.category, payload.cover_image, payload.is_published)
        )
        article_id = cursor.lastrowid
    write_audit("内容管理", f"发布文章: {payload.title}")
    return ok({"id": article_id}, "文章已发布")

@router.put("/articles/{article_id}")
def update_article(article_id: int, payload: ArticlePayload):
    with get_db() as db:
        db.execute(
            "UPDATE articles SET title=?, content=?, author=?, category=?, cover_image=?, is_published=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (payload.title, payload.content, payload.author, payload.category, payload.cover_image, payload.is_published, article_id)
        )
    write_audit("内容管理", f"更新文章 #{article_id}")
    return ok({"id": article_id}, "文章已更新")

@router.delete("/articles/{article_id}")
def delete_article(article_id: int):
    with get_db() as db:
        db.execute("DELETE FROM articles WHERE id=?", (article_id,))
    write_audit("内容管理", f"删除文章 #{article_id}")
    return ok({"id": article_id}, "文章已删除")
