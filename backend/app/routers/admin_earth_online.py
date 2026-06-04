import csv
import io
import time
import urllib.request

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from app.core.database import get_db, row_to_dict, rows_to_list
from app.core.response import ok
from app.services.audit_service import write_audit

router = APIRouter()


class EarthSourcePayload(BaseModel):
    name: str
    slug: str
    category: str
    country: str = ""
    province: str = ""
    city: str = ""
    linked_scenic_id: int | None = None
    source_platform: str
    source_url: str
    embed_url: str = ""
    thumbnail_url: str = ""
    description: str = ""
    is_live: bool = False
    is_embeddable: bool = False
    authorization_note: str = ""
    license_note: str = ""
    review_status: str = "candidate"
    availability_status: str = "unknown"
    risk_level: str = "low"


def normalize(row):
    item = row_to_dict(row)
    if not item:
        return item
    item["is_live"] = bool(item.get("is_live"))
    item["is_embeddable"] = bool(item.get("is_embeddable"))
    item["can_embed"] = bool(item["is_embeddable"] and item.get("embed_url") and item.get("review_status") == "approved" and item.get("availability_status") == "online")
    return item


@router.get("/admin/earth-online/sources")
def admin_sources(category: str | None = None, review_status: str | None = None, availability_status: str | None = None, risk_level: str | None = None, keyword: str | None = None):
    sql = "SELECT * FROM earth_online_sources WHERE 1=1"
    params = []
    for field, value in [("category", category), ("review_status", review_status), ("availability_status", availability_status), ("risk_level", risk_level)]:
        if value:
            sql += f" AND {field}=?"
            params.append(value)
    if keyword:
        sql += " AND (name LIKE ? OR source_platform LIKE ? OR description LIKE ?)"
        like = f"%{keyword}%"
        params.extend([like, like, like])
    sql += " ORDER BY id DESC"
    with get_db() as db:
        return ok([normalize(row) for row in db.execute(sql, params).fetchall()])


@router.post("/admin/earth-online/sources")
def create_source(payload: EarthSourcePayload):
    data = payload.model_dump()
    with get_db() as db:
        cur = db.execute(
            """
            INSERT INTO earth_online_sources (
              name,slug,category,country,province,city,linked_scenic_id,source_platform,source_url,embed_url,thumbnail_url,
              description,is_live,is_embeddable,authorization_note,license_note,review_status,availability_status,risk_level
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                data["name"], data["slug"], data["category"], data["country"], data["province"], data["city"], data["linked_scenic_id"],
                data["source_platform"], data["source_url"], data["embed_url"], data["thumbnail_url"], data["description"],
                int(data["is_live"]), int(data["is_embeddable"]), data["authorization_note"], data["license_note"],
                data["review_status"], data["availability_status"], data["risk_level"],
            ),
        )
        created = normalize(db.execute("SELECT * FROM earth_online_sources WHERE id=?", (cur.lastrowid,)).fetchone())
    write_audit("地球 Online", f"新增来源 {payload.name}")
    return ok(created, "来源已创建")


@router.put("/admin/earth-online/sources/{source_id}")
def update_source(source_id: int, payload: EarthSourcePayload):
    data = payload.model_dump()
    with get_db() as db:
        db.execute(
            """
            UPDATE earth_online_sources SET name=?,slug=?,category=?,country=?,province=?,city=?,linked_scenic_id=?,
            source_platform=?,source_url=?,embed_url=?,thumbnail_url=?,description=?,is_live=?,is_embeddable=?,
            authorization_note=?,license_note=?,review_status=?,availability_status=?,risk_level=?,updated_at=CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (
                data["name"], data["slug"], data["category"], data["country"], data["province"], data["city"], data["linked_scenic_id"],
                data["source_platform"], data["source_url"], data["embed_url"], data["thumbnail_url"], data["description"],
                int(data["is_live"]), int(data["is_embeddable"]), data["authorization_note"], data["license_note"],
                data["review_status"], data["availability_status"], data["risk_level"], source_id,
            ),
        )
    write_audit("地球 Online", f"编辑来源 #{source_id}")
    return ok({"id": source_id}, "来源已更新")


@router.delete("/admin/earth-online/sources/{source_id}")
def delete_source(source_id: int):
    with get_db() as db:
        db.execute("DELETE FROM earth_online_sources WHERE id=?", (source_id,))
    write_audit("地球 Online", f"删除来源 #{source_id}")
    return ok({"id": source_id}, "来源已删除")


def set_review(source_id: int, status: str, message: str):
    with get_db() as db:
        db.execute("UPDATE earth_online_sources SET review_status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, source_id))
    write_audit("地球 Online", f"{message} #{source_id}")
    return ok({"id": source_id, "review_status": status}, message)


@router.post("/admin/earth-online/sources/{source_id}/approve")
def approve_source(source_id: int):
    return set_review(source_id, "approved", "来源已审核通过")


@router.post("/admin/earth-online/sources/{source_id}/reject")
def reject_source(source_id: int):
    return set_review(source_id, "rejected", "来源已驳回")


@router.post("/admin/earth-online/sources/{source_id}/disable")
def disable_source(source_id: int):
    return set_review(source_id, "disabled", "来源已下架")


def check_one(db, source_id: int):
    row = db.execute("SELECT * FROM earth_online_sources WHERE id=?", (source_id,)).fetchone()
    if not row:
        return {"id": source_id, "status": "missing", "message": "来源不存在"}
    item = dict(row)
    start = time.monotonic()
    status = "online"
    http_status = None
    message = "连接正常"
    try:
        request = urllib.request.Request(item["source_url"], method="HEAD", headers={"User-Agent": "ScenicOnlineSourceCheck/1.0"})
        with urllib.request.urlopen(request, timeout=6) as response:
            http_status = response.status
    except Exception:
        try:
            request = urllib.request.Request(item["source_url"], method="GET", headers={"User-Agent": "ScenicOnlineSourceCheck/1.0"})
            with urllib.request.urlopen(request, timeout=8) as response:
                http_status = response.status
        except Exception as exc:
            status = "offline" if "timed out" in str(exc).lower() else "manual_review"
            message = str(exc)[:180]
    if http_status:
        if http_status in (200, 301, 302):
            status = "online"
            message = f"HTTP {http_status}"
        elif http_status == 403:
            status = "manual_review"
            message = "HTTP 403，需人工确认授权或嵌入限制"
        elif http_status == 404:
            status = "offline"
            message = "HTTP 404"
        else:
            status = "manual_review"
            message = f"HTTP {http_status}"
    response_ms = int((time.monotonic() - start) * 1000)
    failure_sql = "failure_count+1" if status != "online" else "0"
    db.execute(
        f"UPDATE earth_online_sources SET availability_status=?, last_checked_at=CURRENT_TIMESTAMP, failure_count={failure_sql}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
        (status, source_id),
    )
    db.execute(
        "INSERT INTO earth_online_checks (source_id,check_type,status,http_status,message,response_ms) VALUES (?,?,?,?,?,?)",
        (source_id, "manual", status, http_status, message, response_ms),
    )
    return {"id": source_id, "status": status, "http_status": http_status, "message": message, "response_ms": response_ms}


@router.post("/admin/earth-online/sources/{source_id}/check")
def check_source(source_id: int):
    with get_db() as db:
        result = check_one(db, source_id)
    write_audit("地球 Online", f"检测来源 #{source_id}")
    return ok(result, "来源检测完成")


@router.post("/admin/earth-online/sources/bulk-check")
def bulk_check():
    with get_db() as db:
        ids = [row["id"] for row in db.execute("SELECT id FROM earth_online_sources ORDER BY id LIMIT 20").fetchall()]
        results = [check_one(db, source_id) for source_id in ids]
    write_audit("地球 Online", "批量检测来源")
    return ok(results, "批量检测完成")


@router.get("/admin/earth-online/checks")
def checks():
    with get_db() as db:
        rows = rows_to_list(db.execute(
            """
            SELECT c.*, s.name AS source_name FROM earth_online_checks c
            LEFT JOIN earth_online_sources s ON s.id=c.source_id
            ORDER BY c.id DESC LIMIT 80
            """
        ).fetchall())
    return ok(rows)


@router.get("/admin/earth-online/stats")
def admin_stats():
    with get_db() as db:
        row = row_to_dict(db.execute(
            """
            SELECT COUNT(*) AS total,
              SUM(CASE WHEN review_status='approved' THEN 1 ELSE 0 END) AS approved,
              SUM(CASE WHEN review_status IN ('candidate','pending') THEN 1 ELSE 0 END) AS pending,
              SUM(CASE WHEN availability_status='online' THEN 1 ELSE 0 END) AS online,
              SUM(CASE WHEN is_embeddable=0 THEN 1 ELSE 0 END) AS externalOnly,
              SUM(CASE WHEN risk_level!='low' THEN 1 ELSE 0 END) AS risk
            FROM earth_online_sources
            """
        ).fetchone())
    return ok(row)


@router.post("/admin/earth-online/import")
def import_sources():
    write_audit("地球 Online", "导入来源候选池")
    return ok({"status": "candidate", "count": 0}, "导入入口已就绪，导入来源默认进入候选池")


@router.get("/admin/earth-online/export")
def export_sources():
    with get_db() as db:
        rows = rows_to_list(db.execute("SELECT * FROM earth_online_sources ORDER BY id").fetchall())
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["id", "name", "slug", "category", "source_platform", "source_url", "review_status", "availability_status", "risk_level"])
    writer.writeheader()
    for row in rows:
        writer.writerow({key: row.get(key, "") for key in writer.fieldnames})
    return PlainTextResponse(output.getvalue(), media_type="text/csv")
