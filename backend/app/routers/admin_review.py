from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.database import get_db, rows_to_list
from app.core.response import ok
from app.services.audit_service import write_audit

router = APIRouter()


class ImageUpdate(BaseModel):
    scenic_id: int | None = None


class BlacklistPayload(BaseModel):
    ip: str
    reason: str = "评论审核加入黑名单"


@router.get("/admin/images/review")
def image_review():
    with get_db() as db:
        return ok(rows_to_list(db.execute("""
          SELECT scenic_images.*, scenic_spots.name AS scenic
          FROM scenic_images LEFT JOIN scenic_spots ON scenic_spots.id = scenic_images.scenic_id
          ORDER BY scenic_images.status='pending' DESC, scenic_images.id DESC
        """).fetchall()))


@router.post("/admin/images/{image_id}/approve")
def approve_image(image_id: int):
    with get_db() as db:
        db.execute("UPDATE scenic_images SET status='approved' WHERE id=?", (image_id,))
    write_audit("图片审核", f"通过图片 #{image_id}")
    return ok({"id": image_id}, "图片已通过")


@router.post("/admin/images/{image_id}/reject")
def reject_image(image_id: int):
    with get_db() as db:
        db.execute("UPDATE scenic_images SET status='rejected' WHERE id=?", (image_id,))
    write_audit("图片审核", f"驳回图片 #{image_id}")
    return ok({"id": image_id}, "图片已驳回")


@router.post("/admin/images/{image_id}/cover")
def set_cover_image(image_id: int):
    with get_db() as db:
        image = db.execute("SELECT * FROM scenic_images WHERE id=?", (image_id,)).fetchone()
        if not image:
            raise HTTPException(status_code=404, detail="图片不存在")
        db.execute("UPDATE scenic_images SET is_cover=0 WHERE scenic_id=?", (image["scenic_id"],))
        db.execute("UPDATE scenic_images SET status='approved', is_cover=1 WHERE id=?", (image_id,))
        db.execute("UPDATE scenic_spots SET cover_image_url=? WHERE id=?", (image["url"], image["scenic_id"]))
    write_audit("图片审核", f"设为封面 #{image_id}")
    return ok({"id": image_id}, "已设为封面")


@router.put("/admin/images/{image_id}")
def update_image(image_id: int, payload: ImageUpdate):
    with get_db() as db:
        db.execute("UPDATE scenic_images SET scenic_id=COALESCE(?, scenic_id) WHERE id=?", (payload.scenic_id, image_id))
    write_audit("图片审核", f"更新图片关联 #{image_id}")
    return ok({"id": image_id}, "图片关联已更新")


@router.delete("/admin/images/{image_id}")
def delete_image(image_id: int):
    with get_db() as db:
        db.execute("DELETE FROM scenic_images WHERE id=?", (image_id,))
    write_audit("图片审核", f"删除图片 #{image_id}")
    return ok({"id": image_id}, "图片已删除")


@router.get("/admin/comments/review")
def comment_review():
    with get_db() as db:
        return ok(rows_to_list(db.execute("SELECT * FROM comments ORDER BY id DESC").fetchall()))


@router.post("/admin/comments/{comment_id}/approve")
def approve_comment(comment_id: int):
    with get_db() as db:
        db.execute("UPDATE comments SET status='approved' WHERE id=?", (comment_id,))
    write_audit("评论审核", f"通过评论 #{comment_id}")
    return ok({"id": comment_id}, "评论已通过")


@router.post("/admin/comments/{comment_id}/hide")
def hide_comment(comment_id: int):
    with get_db() as db:
        db.execute("UPDATE comments SET status='hidden' WHERE id=?", (comment_id,))
    write_audit("评论审核", f"隐藏评论 #{comment_id}")
    return ok({"id": comment_id}, "评论已隐藏")


@router.delete("/admin/comments/{comment_id}")
def delete_comment(comment_id: int):
    with get_db() as db:
        db.execute("DELETE FROM comments WHERE id=?", (comment_id,))
    write_audit("评论审核", f"删除评论 #{comment_id}")
    return ok({"id": comment_id}, "评论已删除")


@router.post("/admin/security/ip-blacklist")
def add_ip_blacklist(payload: BlacklistPayload):
    with get_db() as db:
        db.execute(
            "INSERT OR IGNORE INTO ip_blacklist (ip, reason) VALUES (?, ?)",
            (payload.ip, payload.reason),
        )
    write_audit("安全管理", f"加入 IP 黑名单 {payload.ip}")
    return ok({"ip": payload.ip}, "IP 已加入黑名单")
