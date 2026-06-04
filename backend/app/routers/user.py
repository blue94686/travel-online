import json
import random
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import create_access_token, get_current_user, hash_password, require_user, verify_password
from app.core.database import get_db, row_to_dict, rows_to_list
from app.core.response import ok
from app.routers.admin_system import default_layout, normalize_layout_payload
from app.services.audit_service import write_audit

router = APIRouter()


# ─── Auth Endpoints ───

class EmailCodePayload(BaseModel):
    email: str


class LoginPayload(BaseModel):
    email: str
    password: str


class RegisterPayload(BaseModel):
    email: str
    password: str
    code: str
    nickname: str | None = None


@router.post("/auth/send-code")
def send_auth_code(payload: EmailCodePayload):
    if "@" not in payload.email:
        raise HTTPException(status_code=400, detail="请输入有效邮箱")
    
    code = "".join([str(random.randint(0, 9)) for _ in range(6)])
    expires_at = (datetime.now() + timedelta(minutes=10)).isoformat()
    
    with get_db() as db:
        # Clear old codes for this email
        db.execute("DELETE FROM auth_codes WHERE email=?", (payload.email,))
        db.execute(
            "INSERT INTO auth_codes (email, code, expires_at) VALUES (?, ?, ?)",
            (payload.email, code, expires_at)
        )
    
    # In production this code should be delivered by an email provider.
    print(f"Auth Code for {payload.email}: {code}")
    write_audit("认证", f"发送验证码至 {payload.email}")
    
    return ok({"email": payload.email}, "验证码已发送")


def _validate_email_password(email: str, password: str):
    if "@" not in email:
        raise HTTPException(status_code=400, detail="请输入有效邮箱")
    if len(password or "") < 6:
        raise HTTPException(status_code=400, detail="密码至少6位")


def _auth_response(user):
    user = dict(user)
    token = create_access_token({"sub": str(user["id"]), "role": user.get("role", "user")})
    return ok({
        "token": token,
        "user": {"id": user["id"], "email": user["email"], "nickname": user.get("nickname", ""), "role": user.get("role", "user")},
    }, "登录成功")


@router.post("/auth/login")
def login_with_password(payload: LoginPayload):
    _validate_email_password(payload.email, payload.password)
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (payload.email,)).fetchone()
        if not user or not user["password_hash"] or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="账号或密码错误")

        if user["status"] != "active":
            raise HTTPException(status_code=403, detail="账号已被禁用")

    return _auth_response(user)


@router.post("/auth/register")
def register_with_code(payload: RegisterPayload):
    _validate_email_password(payload.email, payload.password)
    with get_db() as db:
        record = db.execute(
            "SELECT * FROM auth_codes WHERE email=? AND code=? AND expires_at > CURRENT_TIMESTAMP",
            (payload.email, payload.code)
        ).fetchone()
        if not record:
            raise HTTPException(status_code=401, detail="验证码错误或已过期")

        user = db.execute("SELECT * FROM users WHERE email=?", (payload.email,)).fetchone()
        if user:
            raise HTTPException(status_code=409, detail="账号已存在，请直接登录")

        nickname = payload.nickname or payload.email.split("@")[0]
        cur = db.execute(
            "INSERT INTO users (email,password_hash,nickname,role,status) VALUES (?,?,?,?,?)",
            (payload.email, hash_password(payload.password), nickname, "user", "active"),
        )
        user = db.execute("SELECT * FROM users WHERE id=?", (cur.lastrowid,)).fetchone()
        db.execute("DELETE FROM auth_codes WHERE email=?", (payload.email,))

    write_audit("认证", f"新用户注册: {payload.email}")
    return _auth_response(user)


@router.get("/auth/me")
def get_me(user: dict = Depends(require_user)):
    return ok({
        "id": user["id"],
        "email": user["email"],
        "nickname": user.get("nickname", ""),
        "role": user.get("role", "user"),
    })


# ─── User Endpoints ───


class WorkbenchLayoutPayload(BaseModel):
    layout: list[dict[str, Any]] | dict[str, Any]
    change_note: str = "保存个人工作台"


class RoutePayload(BaseModel):
    title: str = "规则推荐路线"
    transport: str = "自驾"
    stops: list[str] = []
    distance_km: float = 0
    duration_hours: float = 0
    payload: dict[str, Any] = {}


@router.get("/user/profile")
def profile(user: dict = Depends(require_user)):
    return ok({"id": user["id"], "nickname": user.get("nickname", ""), "email": user.get("email", ""), "role": user.get("role", "user"), "level": "注册用户"})


@router.get("/user/favorites")
def favorites(user: dict = Depends(require_user)):
    with get_db() as db:
        rows = rows_to_list(db.execute(
            "SELECT f.*, s.name as scenic_name, s.cover_image_url, s.city FROM favorites f LEFT JOIN scenic_spots s ON s.id=f.scenic_id WHERE f.user_id=? ORDER BY f.id DESC",
            (user["id"],),
        ).fetchall())
    return ok(rows)


class FavoritePayload(BaseModel):
    scenic_id: int = 0


@router.post("/user/favorites")
def add_favorite(payload: FavoritePayload, user: dict = Depends(require_user)):
    if not payload.scenic_id:
        return ok({}, "参数缺失")
    with get_db() as db:
        existing = db.execute("SELECT id FROM favorites WHERE user_id=? AND scenic_id=?", (user["id"], payload.scenic_id)).fetchone()
        if existing:
            db.execute("DELETE FROM favorites WHERE id=?", (existing["id"],))
            return ok({"status": "removed"}, "已取消收藏")
        db.execute("INSERT INTO favorites (user_id,scenic_id) VALUES (?,?)", (user["id"], payload.scenic_id))
    return ok({"status": "saved"}, "已收藏")


@router.delete("/user/favorites/{favorite_id}")
def remove_favorite(favorite_id: int, user: dict = Depends(require_user)):
    with get_db() as db:
        db.execute("DELETE FROM favorites WHERE id=? AND user_id=?", (favorite_id, user["id"]))
    return ok({"id": favorite_id}, "已取消收藏")


@router.get("/user/trips")
def trips():
    return ok([{"id": 1, "title": "杭州周末两日", "status": "draft"}])


@router.post("/user/trips")
def create_trip():
    return ok({"id": 2, "status": "draft"}, "行程已创建")


@router.get("/user/routes")
def routes():
    return ok([{"id": 1, "title": "西湖环线", "distance_km": 12.4}])


@router.post("/user/routes")
def create_route(payload: RoutePayload = RoutePayload()):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO trip_routes (trip_id,user_id,title,transport,stops,distance_km,duration_hours,payload) VALUES (?,?,?,?,?,?,?,?)",
            (1, 1, payload.title, payload.transport, json.dumps(payload.stops or ["出发地", "途经点", "目的地"], ensure_ascii=False), payload.distance_km, payload.duration_hours, json.dumps(payload.payload, ensure_ascii=False)),
        )
    return ok({"id": cur.lastrowid, "status": "saved"}, "路线已保存")


@router.get("/user/export/trip/{trip_id}")
def export_trip(trip_id: int):
    return ok({"trip_id": trip_id, "download_url": "/mock/trip.pdf"}, "导出任务已生成")


@router.get("/user/export/route/{route_id}")
def export_route(route_id: int, format: str = "gpx"):
    suffix = "pdf" if format == "pdf" else "gpx"
    return ok({"route_id": route_id, "format": suffix, "download_url": f"/mock/route-{route_id}.{suffix}", "content_type": "application/gpx+xml" if suffix == "gpx" else "application/pdf"}, "路线导出任务已生成")


@router.get("/user/workbench-layout")
def get_workbench_layout():
    user_id = 1
    page_key = "user_center"
    with get_db() as db:
        row = db.execute("SELECT * FROM user_layouts WHERE user_id=? AND page_key=? AND is_active=1", (user_id, page_key)).fetchone()
        if row:
            return ok(row_to_dict(row))
        layout = default_layout(page_key)
        db.execute(
            "INSERT OR IGNORE INTO user_layouts (user_id,page_key,layout_json,version,is_active) VALUES (?,?,?,?,?)",
            (user_id, page_key, json.dumps(layout, ensure_ascii=False), 1, 1),
        )
        return ok({"user_id": user_id, "page_key": page_key, "layout_json": layout, "layout": layout, "version": 1, "is_active": True})


@router.put("/user/workbench-layout")
def save_workbench_layout(payload: WorkbenchLayoutPayload):
    user_id = 1
    page_key = "user_center"
    layout = normalize_layout_payload(page_key, payload.layout)
    raw = json.dumps(layout, ensure_ascii=False)
    with get_db() as db:
        row = db.execute("SELECT * FROM user_layouts WHERE user_id=? AND page_key=?", (user_id, page_key)).fetchone()
        version = (row["version"] if row else 0) + 1
        db.execute(
            """
            INSERT INTO user_layouts (user_id,page_key,layout_json,version,is_active,updated_at) VALUES (?,?,?,?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(user_id,page_key) DO UPDATE SET layout_json=excluded.layout_json,version=excluded.version,is_active=1,updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, page_key, raw, version),
        )
        saved = db.execute("SELECT * FROM user_layouts WHERE user_id=? AND page_key=?", (user_id, page_key)).fetchone()
    return ok(row_to_dict(saved) | {"layout": layout}, "个人工作台编排已保存")


@router.post("/user/workbench-layout/reset")
def reset_workbench_layout():
    user_id = 1
    page_key = "user_center"
    layout = default_layout(page_key)
    raw = json.dumps(layout, ensure_ascii=False)
    with get_db() as db:
        row = db.execute("SELECT * FROM user_layouts WHERE user_id=? AND page_key=?", (user_id, page_key)).fetchone()
        version = (row["version"] if row else 0) + 1
        db.execute(
            """
            INSERT INTO user_layouts (user_id,page_key,layout_json,version,is_active,updated_at) VALUES (?,?,?,?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(user_id,page_key) DO UPDATE SET layout_json=excluded.layout_json,version=excluded.version,is_active=1,updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, page_key, raw, version),
        )
    write_audit("用户工作台", "恢复个人工作台默认布局")
    return ok({"user_id": user_id, "page_key": page_key, "layout": layout, "version": version}, "已恢复默认布局")


@router.post("/user/workbench-layout/publish")
def publish_workbench_layout():
    user_id = 1
    page_key = "user_center"
    with get_db() as db:
        row = db.execute("SELECT * FROM user_layouts WHERE user_id=? AND page_key=?", (user_id, page_key)).fetchone()
        layout = row_to_dict(row)["layout_json"] if row else default_layout(page_key)
        version = (row["version"] if row else 1) + 1
        if row:
            db.execute("UPDATE user_layouts SET version=?,is_active=1,updated_at=CURRENT_TIMESTAMP WHERE id=?", (version, row["id"]))
            layout_id = row["id"]
        else:
            db.execute("INSERT INTO user_layouts (user_id,page_key,layout_json,version,is_active) VALUES (?,?,?,?,1)", (user_id, page_key, json.dumps(layout, ensure_ascii=False), version))
            layout_id = db.execute("SELECT last_insert_rowid() AS id").fetchone()["id"]
        db.execute("INSERT INTO user_layout_versions (user_layout_id,user_id,page_key,version,layout_json,change_note) VALUES (?,?,?,?,?,?)", (layout_id, user_id, page_key, version, json.dumps(layout, ensure_ascii=False), "发布到我的工作台"))
    write_audit("用户工作台", "发布个人工作台布局")
    return ok({"user_id": user_id, "page_key": page_key, "version": version}, "已发布到我的工作台")


@router.get("/user/workbench-layout/versions")
def workbench_layout_versions():
    with get_db() as db:
        rows = rows_to_list(db.execute("SELECT * FROM user_layout_versions WHERE user_id=? ORDER BY version DESC LIMIT 20", (1,)).fetchall())
    return ok(rows)


@router.post("/user/workbench-layout/versions/{version_id}/restore")
def restore_workbench_layout_version(version_id: int):
    user_id = 1
    page_key = "user_center"
    with get_db() as db:
        version = db.execute("SELECT * FROM user_layout_versions WHERE id=? AND user_id=?", (version_id, user_id)).fetchone()
        layout = version["layout_json"] if version else json.dumps(default_layout(page_key), ensure_ascii=False)
        current = db.execute("SELECT * FROM user_layouts WHERE user_id=? AND page_key=?", (user_id, page_key)).fetchone()
        next_version = (current["version"] if current else 1) + 1
        db.execute(
            """
            INSERT INTO user_layouts (user_id,page_key,layout_json,version,is_active,updated_at) VALUES (?,?,?,?,1,CURRENT_TIMESTAMP)
            ON CONFLICT(user_id,page_key) DO UPDATE SET layout_json=excluded.layout_json,version=excluded.version,is_active=1,updated_at=CURRENT_TIMESTAMP
            """,
            (user_id, page_key, layout, next_version),
        )
    write_audit("用户工作台", f"恢复个人工作台版本 #{version_id}")
    return ok({"user_id": user_id, "page_key": page_key, "version": next_version, "layout": parse_layout_value(layout, page_key) if False else json.loads(layout)}, "已恢复历史版本")
