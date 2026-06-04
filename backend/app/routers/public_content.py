from fastapi import APIRouter
from app.core.database import get_db, rows_to_list
from app.core.response import fail, ok

router = APIRouter(prefix="/content", tags=["Public Content"])

@router.get("/banners")
def list_banners():
    with get_db() as db:
        rows = db.execute(
            """
            SELECT * FROM banners
            WHERE id IN (
              SELECT MAX(id)
              FROM banners
              WHERE is_active=1
              GROUP BY title, image_url, order_index
            )
            ORDER BY order_index ASC, id ASC
            """
        ).fetchall()
        return ok(rows_to_list(rows))

@router.get("/articles")
def list_articles(category: str | None = None, limit: int = 10):
    sql = """
        SELECT * FROM articles
        WHERE id IN (
          SELECT MAX(id)
          FROM articles
          WHERE is_published=1
    """
    params = []
    if category:
        sql += " AND category=?"
        params.append(category)
    sql += """
          GROUP BY title, category, author
        )
        ORDER BY created_at DESC, id DESC
        LIMIT ?
    """
    params.append(limit)
    
    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
        return ok(rows_to_list(rows))

@router.get("/articles/{article_id}")
def get_article(article_id: int):
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM articles WHERE id=? AND is_published=1",
            (article_id,),
        ).fetchone()
        if not row:
            return fail("文章不存在")
        return ok(dict(row))
