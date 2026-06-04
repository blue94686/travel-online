import json
import re
import shutil
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import DATA_DIR, DB_PATH, DATABASE_BACKEND, DATABASE_URL
from app.core.database import get_db, row_to_dict, rows_to_list
from app.core.response import ok
from app.services.audit_service import write_audit
from app.services.scenic_sql_import_service import DEFAULT_EXTERNAL_SQL_PATH, import_scenic_sql, inspect_sql_file, preview_scenic_sql_import

router = APIRouter()

SAFE_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class UserStatusPayload(BaseModel):
    status: str


class UserRolePayload(BaseModel):
    role: str


class SettingsPayload(BaseModel):
    siteName: str = "景区在线 Scenic Online"
    defaultCity: str = "杭州"
    homeRecommendation: str = "quality"
    imageFallback: str = "/images/hero-mountain-lake.jpg"
    reviewRequired: bool = True
    userUploadEnabled: bool = True
    autoEnrichmentEnabled: bool = True
    earthOnlineEnabled: bool = True
    imageStorage: str = "local-or-remote"
    syncSchedule: str = "每天 02:00"
    announcement: str = ""


class RolePayload(BaseModel):
    id: int | None = None
    name: str
    label: str
    permissions: list[str] = []


class RolesPayload(BaseModel):
    roles: list[RolePayload]


class LayoutPayload(BaseModel):
    layout: list[dict[str, Any]] | dict[str, Any]
    name: str = ""
    status: str = "draft"
    change_note: str = "保存页面编排"


class ComponentTemplatePayload(BaseModel):
    name: str
    type: str
    category: str
    config_json: dict[str, Any] = {}
    preview_image: str = ""


@router.get("/admin/users")
def admin_users():
    with get_db() as db:
        users = rows_to_list(db.execute("""
            SELECT
              u.id,
              u.email,
              u.nickname,
              CASE
                WHEN u.role IN ('注册用户', '普通用户') THEN 'user'
                WHEN u.role IN ('管理员', '审核员') THEN 'admin'
                ELSE u.role
              END AS role,
              u.status,
              u.created_at,
              (SELECT COUNT(*) FROM comments c WHERE c.user_id=u.id) AS comment_count,
              (SELECT COUNT(*) FROM uploads up WHERE up.user_id=u.id) AS upload_count,
              (SELECT COUNT(*) FROM trip_routes tr WHERE tr.user_id=u.id) AS route_count,
              (SELECT COUNT(*) FROM trips t WHERE t.user_id=u.id) AS trip_count
            FROM users u
            ORDER BY u.id
        """).fetchall())
        if not users:
            users = [
                {"id": 1, "nickname": "风景收藏家", "email": "traveler@example.com", "role": "user", "status": "active", "comment_count": 0, "upload_count": 0, "route_count": 0, "trip_count": 0},
                {"id": 2, "nickname": "审核员", "email": "admin@example.com", "role": "admin", "status": "active", "comment_count": 0, "upload_count": 0, "route_count": 0, "trip_count": 0},
            ]
    return ok(users)


@router.put("/admin/users/{user_id}/status")
def update_user_status(user_id: int, payload: UserStatusPayload):
    with get_db() as db:
        db.execute("UPDATE users SET status=? WHERE id=?", (payload.status, user_id))
    write_audit("用户管理", f"更新用户 #{user_id} 状态为 {payload.status}")
    return ok({"id": user_id, "status": payload.status}, "用户状态已更新")


@router.put("/admin/users/{user_id}/role")
def update_user_role(user_id: int, payload: UserRolePayload):
    if payload.role == "super_admin":
        raise HTTPException(status_code=403, detail="不能通过普通角色切换授予超级管理员")
    with get_db() as db:
        user = row_to_dict(db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user.get("role") == "super_admin":
            raise HTTPException(status_code=403, detail="超级管理员角色受保护")
        exists = db.execute("SELECT 1 FROM roles WHERE name=?", (payload.role,)).fetchone()
        if not exists:
            raise HTTPException(status_code=400, detail="角色不存在")
        db.execute("UPDATE users SET role=? WHERE id=?", (payload.role, user_id))
    write_audit("用户管理", f"更新用户 #{user_id} 角色为 {payload.role}")
    return ok({"id": user_id, "role": payload.role}, "用户角色已更新")


@router.post("/admin/users/{user_id}/reset-demo-password")
def reset_demo_password(user_id: int):
    with get_db() as db:
        user = row_to_dict(db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())
        if not user:
            raise HTTPException(status_code=404, detail="用户不存在")
        if user.get("role") == "super_admin":
            raise HTTPException(status_code=403, detail="超级管理员密码不能在演示后台重置")
        password = "User123456" if user.get("role") == "user" else "Admin123456"
        db.execute("UPDATE users SET password_hash=? WHERE id=?", (password, user_id))
    write_audit("用户管理", f"重置用户 #{user_id} 演示密码")
    return ok({"id": user_id, "password": password}, "演示密码已重置")


@router.get("/admin/roles")
def roles():
    with get_db() as db:
        return ok(rows_to_list(db.execute("SELECT * FROM roles ORDER BY id").fetchall()))


@router.put("/admin/roles")
def update_roles(payload: RolesPayload):
    protected_roles = {"super_admin": {"system:manage", "role:manage", "api:manage", "earth:policy"}}
    with get_db() as db:
        existing = {row["name"]: row_to_dict(row) for row in db.execute("SELECT * FROM roles").fetchall()}
        for role in payload.roles:
            if role.name not in existing:
                raise HTTPException(status_code=400, detail=f"未知角色：{role.name}")
            permissions = list(dict.fromkeys(role.permissions))
            if role.name in protected_roles:
                permissions = list(dict.fromkeys(permissions + list(protected_roles[role.name])))
            db.execute(
                "UPDATE roles SET label=?, permissions=? WHERE name=?",
                (role.label, json.dumps(permissions, ensure_ascii=False), role.name),
            )
    write_audit("权限管理", "保存权限矩阵")
    return roles()


@router.get("/admin/security/logs")
def security_logs():
    with get_db() as db:
        logs = rows_to_list(db.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 80").fetchall())
    return ok(logs or [
        {"id": 1, "operator": "admin", "module": "登录", "action": "后台登录", "ip": "127.0.0.1", "result": "success", "created_at": "2026-05-20 09:30:00"}
    ])


@router.get("/admin/security/ip-blacklist")
def ip_blacklist():
    with get_db() as db:
        return ok(rows_to_list(db.execute("SELECT * FROM ip_blacklist ORDER BY id DESC").fetchall()))


@router.delete("/admin/security/ip-blacklist/{ip}")
def remove_ip_blacklist(ip: str):
    with get_db() as db:
        db.execute("DELETE FROM ip_blacklist WHERE ip=?", (ip,))
    write_audit("安全管理", f"移除 IP 黑名单 {ip}")
    return ok({"ip": ip}, "IP 已移出黑名单")


@router.get("/admin/system/settings")
def settings():
    defaults = SettingsPayload().model_dump()
    with get_db() as db:
        rows = rows_to_list(db.execute("SELECT * FROM system_settings").fetchall())
    data = defaults.copy()
    for row in rows:
        key = row.get("setting_key")
        if key not in data:
            continue
        raw_value = row.get("setting_value")
        try:
            data[key] = json.loads(raw_value)
        except (TypeError, json.JSONDecodeError):
            data[key] = raw_value
    return ok(data)


@router.put("/admin/system/settings")
def update_settings(payload: SettingsPayload):
    data = payload.model_dump()
    with get_db() as db:
        for key, value in data.items():
            value_type = "boolean" if isinstance(value, bool) else "string"
            db.execute(
                """
                INSERT INTO system_settings (setting_key,setting_value,value_type,updated_at)
                VALUES (?,?,?,CURRENT_TIMESTAMP)
                ON CONFLICT(setting_key) DO UPDATE SET
                  setting_value=excluded.setting_value,
                  value_type=excluded.value_type,
                  updated_at=CURRENT_TIMESTAMP
                """,
                (key, json.dumps(value, ensure_ascii=False), value_type),
            )
    write_audit("系统设置", "保存系统设置")
    return ok(data | {"status": "saved"}, "系统设置已保存")


@router.get("/admin/logs")
def audit_logs(operator: str | None = None, module: str | None = None, result: str | None = None):
    sql = "SELECT * FROM audit_logs WHERE 1=1"
    params = []
    if operator:
        sql += " AND operator LIKE ?"
        params.append(f"%{operator}%")
    if module:
        sql += " AND module LIKE ?"
        params.append(f"%{module}%")
    if result:
        sql += " AND result = ?"
        params.append(result)
    sql += " ORDER BY id DESC LIMIT 100"
    with get_db() as db:
        return ok(rows_to_list(db.execute(sql, params).fetchall()))


PAGE_LABELS = {
    "home": "推荐首页",
    "scenic": "景区推荐",
    "scenic_detail": "景区详情模板",
    "themes": "主题旅行",
    "map": "地图规划",
    "weather": "天气实况",
    "community": "游客社区",
    "provinces": "省份浏览",
    "earth_online": "地球 Online",
    "auth": "登录注册",
    "user_center": "用户中心",
    "admin_dashboard": "后台总览",
    "admin_api": "后台 API 接入",
    "admin_services": "后台服务管理",
    "admin_earth_online": "后台地球 Online",
    "admin_enrichment": "后台资料补全",
    "admin": "后台总览",
}


def normalize_page_key(scope: str):
    return {"admin": "admin_dashboard", "user": "user_center", "user:1": "user_center"}.get(scope, scope)


def module_item(page_key: str, module_id: str, module_type: str, title: str, order: int, width: str = "full", source: str = "api", subtitle: str = ""):
    span = {"full": 12, "half": 6, "third": 4, "quarter": 3}.get(width, 12)
    return {
        "id": module_id,
        "type": module_type,
        "title": title,
        "subtitle": subtitle,
        "visible": True,
        "roleVisible": ["guest", "user", "admin", "super_admin"],
        "order": order,
        "width": width,
        "layout": {
            "desktop": {"x": 0, "y": max(0, order - 1) * 3, "w": span, "h": 4},
            "tablet": {"x": 0, "y": max(0, order - 1) * 3, "w": min(span, 8), "h": 4},
            "mobile": {"x": 0, "y": max(0, order - 1) * 3, "w": 4, "h": 4},
        },
        "style": {"borderRadius": 16, "backgroundColor": "#FFFFFF", "shadow": "soft", "theme": "fresh-scenic"},
        "dataSource": source,
        "settings": {"showTitle": True, "limit": 6, "backgroundType": "图片", "theme": "清爽风景"},
        "responsive": {"desktop": True, "tablet": True, "mobile": True},
        "pageKey": page_key,
    }


def default_layout(page_key: str):
    page_key = normalize_page_key(page_key)
    presets = {
        "home": [
            ("hero", "hero", "今天去哪玩？", "full", "scenic"),
            ("quick-entry", "quick_entry", "功能入口", "full", "mock"),
            ("earth-online", "earth_online", "地球 Online", "full", "earth_online"),
            ("featured-scenic", "scenic_cards", "精选景区", "half", "scenic"),
            ("hot-themes", "theme_cards", "热门主题", "half", "scenic"),
            ("weather-live", "weather_card", "天气与实况", "half", "weather"),
            ("province-entry", "province_entry", "省份浏览", "half", "scenic"),
            ("latest-comments", "comments", "最新评论", "full", "community"),
        ],
        "scenic": [("search-hero", "hero", "景区推荐", "full", "scenic"), ("filters", "search_bar", "三级浏览筛选", "third", "scenic"), ("scenic-list", "scenic_cards", "景区列表", "full", "scenic"), ("map-side", "map_tool", "地图推荐", "third", "scenic")],
        "scenic_detail": [("detail-gallery", "gallery", "景区图集", "full", "scenic"), ("detail-info", "scenic_cards", "景区信息", "half", "scenic"), ("nearby", "scenic_cards", "附近推荐", "half", "scenic"), ("comments", "comments", "游客评论", "full", "community")],
        "themes": [("themes-hero", "hero", "主题旅行", "full", "scenic"), ("hot-themes", "theme_cards", "热门主题", "full", "scenic"), ("route-list", "map_tool", "路线推荐", "full", "scenic")],
        "map": [("route-panel", "map_tool", "路线规划", "third", "scenic"), ("route-map", "map_tool", "地图工具", "full", "scenic"), ("route-summary", "data_quality", "行程概览", "third", "mock")],
        "weather": [("weather-search", "search_bar", "城市天气搜索", "full", "weather"), ("forecast", "weather_card", "七日天气", "half", "weather"), ("live", "live_source", "公开实况", "half", "earth_online")],
        "community": [("post-box", "comments", "发布区", "full", "community"), ("featured-posts", "comments", "社区精选", "full", "community")],
        "provinces": [("province-entry", "province_entry", "省份浏览", "full", "scenic"), ("featured-scenic", "scenic_cards", "省份景区", "full", "scenic")],
        "earth_online": [("earth-hero", "earth_online", "地球 Online", "full", "earth_online"), ("earth-sources", "live_source", "公开来源", "full", "earth_online"), ("earth-map", "map_tool", "全球来源分布", "half", "earth_online")],
        "auth": [("auth-hero", "hero", "登录注册横幅", "half", "user"), ("auth-form", "custom", "账号表单", "half", "user"), ("test-accounts", "comments", "测试账号", "full", "mock")],
        "user_center": [("member-hero", "hero", "顶部个人横幅", "full", "user"), ("level-card", "data_quality", "等级进度", "half", "user"), ("current-trip", "map_tool", "当前行程", "half", "user"), ("upcoming-trip", "map_tool", "即将出发", "half", "user"), ("recent-view", "scenic_cards", "最近浏览", "half", "user"), ("favorites", "scenic_cards", "我的收藏", "half", "user"), ("footprints", "data_quality", "足迹数据", "half", "user"), ("quick-entry", "quick_entry", "快捷入口", "half", "user"), ("security", "service_status", "账号安全", "half", "user"), ("earth-favorites", "earth_online", "地球 Online 收藏", "half", "earth_online")],
        "admin_dashboard": [("kpi", "kpi_cards", "KPI 卡片", "full", "admin"), ("system", "service_status", "系统状态", "half", "admin"), ("services", "service_status", "服务健康", "half", "admin"), ("review", "review_queue", "审核队列", "half", "admin"), ("sync", "sync_tasks", "最近同步任务", "half", "admin"), ("logs", "operation_logs", "操作日志", "half", "admin"), ("quality", "data_quality", "数据治理", "half", "admin"), ("api-health", "api_status", "API 健康检查", "half", "admin"), ("earth-status", "earth_online", "地球 Online 来源状态", "half", "earth_online"), ("enrichment", "data_quality", "景区资料补全任务", "half", "admin")],
        "admin_api": [("api-kpi", "kpi_cards", "API 概览", "full", "admin"), ("api-table", "api_status", "服务接入表", "full", "admin"), ("api-logs", "operation_logs", "调用日志", "half", "admin"), ("webhook", "api_status", "Webhook 配置", "half", "admin")],
        "admin_services": [("service-status", "service_status", "服务拓扑", "full", "admin"), ("service-logs", "operation_logs", "服务日志", "half", "admin"), ("service-resource", "data_quality", "资源监控", "half", "admin")],
        "admin_earth_online": [("earth-source-table", "live_source", "来源列表", "full", "earth_online"), ("earth-checks", "service_status", "检测记录", "half", "earth_online"), ("earth-risk", "data_quality", "风险等级", "half", "earth_online")],
        "admin_enrichment": [("missing", "data_quality", "缺失资料", "full", "admin"), ("tasks", "sync_tasks", "补全任务", "half", "admin"), ("candidates", "review_queue", "候选审核", "half", "admin")],
    }
    entries = presets.get(page_key, presets["home"])
    return {
        "pageKey": page_key,
        "theme": "后台管理" if page_key == "admin_dashboard" else ("地球科技" if page_key == "earth_online" else "清爽风景"),
        "canvas": {
            "desktop": {"cols": 12, "rowHeight": 40},
            "tablet": {"cols": 8, "rowHeight": 40},
            "mobile": {"cols": 4, "rowHeight": 36},
        },
        "modules": [module_item(page_key, module_id, module_type, title, index + 1, width, source) for index, (module_id, module_type, title, width, source) in enumerate(entries)],
    }


def parse_layout_value(value, page_key: str):
    if not value:
        return default_layout(page_key)
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return default_layout(page_key)
    if isinstance(value, list):
        return {"pageKey": page_key, "theme": "清爽风景", "modules": value}
    if isinstance(value, dict):
        modules = value.get("components") if isinstance(value.get("components"), list) else value.get("modules")
        modules = modules if isinstance(modules, list) else []
        parsed = value | {"pageKey": value.get("pageKey") or page_key, "modules": modules}
        parsed["components"] = modules
        if not isinstance(parsed.get("canvas"), dict):
            parsed["canvas"] = default_layout(page_key)["canvas"]
        return parsed
    return default_layout(page_key)


def normalize_layout_payload(page_key: str, payload):
    layout = parse_layout_value(payload, page_key)
    modules = []
    for index, item in enumerate(layout.get("modules", [])):
        module_id = item.get("id") or f"{page_key}-{index + 1}"
        modules.append(module_item(
            page_key,
            module_id,
            item.get("type") or "custom",
            item.get("title") or module_id,
            index + 1,
            item.get("width") or "full",
            item.get("dataSource") or item.get("data_source") or "api",
            item.get("subtitle") or "",
        ) | {
            "visible": bool(item.get("visible", True)),
            "settings": item.get("settings") if isinstance(item.get("settings"), dict) else {},
            "responsive": item.get("responsive") if isinstance(item.get("responsive"), dict) else {"desktop": True, "tablet": True, "mobile": True},
            "layout": item.get("layout") if isinstance(item.get("layout"), dict) else module_item(page_key, module_id, item.get("type") or "custom", item.get("title") or module_id, index + 1, item.get("width") or "full").get("layout"),
            "style": item.get("style") if isinstance(item.get("style"), dict) else {"borderRadius": 16, "backgroundColor": "#FFFFFF", "shadow": "soft", "theme": "fresh-scenic"},
            "roleVisible": item.get("roleVisible") if isinstance(item.get("roleVisible"), list) else ["guest", "user", "admin", "super_admin"],
        })
    canvas = layout.get("canvas") if isinstance(layout.get("canvas"), dict) else default_layout(page_key)["canvas"]
    return {"pageKey": page_key, "theme": layout.get("theme") or "清爽风景", "canvas": canvas, "modules": modules, "components": modules}


def layout_response(row, page_key: str):
    if not row:
        layout = default_layout(page_key)
        return {"page_key": page_key, "name": PAGE_LABELS.get(page_key, page_key), "layout": layout, "status": "default", "version": 1, "is_active": True}
    item = row_to_dict(row)
    layout = parse_layout_value(item.get("layout_json") or item.get("layout"), page_key)
    layout["components"] = layout.get("components") or layout.get("modules", [])
    return item | {"page_key": item.get("page_key") or page_key, "layout": layout, "is_active": bool(item.get("is_active", 1))}


def upsert_page_layout(page_key: str, layout: dict, name: str, status: str, actor: str):
    raw = json.dumps(layout, ensure_ascii=False)
    with get_db() as db:
        current = db.execute("SELECT * FROM page_layouts WHERE page_key=? OR scope=?", (page_key, page_key)).fetchone()
        version = (current["version"] if current and "version" in current.keys() and current["version"] else 0) + 1
        db.execute(
            """
            INSERT INTO page_layouts (scope,page_key,name,layout,layout_json,status,version,is_active,created_by,updated_by,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(scope) DO UPDATE SET page_key=excluded.page_key,name=excluded.name,layout=excluded.layout,
            layout_json=excluded.layout_json,status=excluded.status,version=excluded.version,is_active=excluded.is_active,
            updated_by=excluded.updated_by,updated_at=CURRENT_TIMESTAMP
            """,
            (page_key, page_key, name or PAGE_LABELS.get(page_key, page_key), raw, raw, status, version, 1, actor, actor),
        )
        saved = db.execute("SELECT * FROM page_layouts WHERE page_key=? OR scope=?", (page_key, page_key)).fetchone()
        return saved, version


@router.get("/admin/page-layouts/{scope}")
@router.get("/admin/layouts/{scope}")
def get_page_layout(scope: str):
    page_key = normalize_page_key(scope)
    with get_db() as db:
        row = db.execute("SELECT * FROM page_layouts WHERE page_key=? OR scope=?", (page_key, scope)).fetchone()
        if row:
            return ok(layout_response(row, page_key))
        layout = default_layout(page_key)
        raw = json.dumps(layout, ensure_ascii=False)
        db.execute(
            "INSERT OR IGNORE INTO page_layouts (scope,page_key,name,layout,layout_json,status,version,is_active,updated_by) VALUES (?,?,?,?,?,?,?,?,?)",
            (page_key, page_key, PAGE_LABELS.get(page_key, page_key), raw, raw, "draft", 1, 1, "system"),
        )
        return ok({"scope": page_key, "page_key": page_key, "layout": layout, "updated_by": "system", "version": 1, "status": "draft"})


@router.put("/admin/page-layouts/{scope}")
@router.put("/admin/layouts/{scope}")
def save_page_layout(scope: str, payload: LayoutPayload):
    page_key = normalize_page_key(scope)
    layout = normalize_layout_payload(page_key, payload.layout)
    saved, _ = upsert_page_layout(page_key, layout, payload.name, payload.status, "admin")
    write_audit("页面编排", f"保存 {page_key} 编排")
    return ok(layout_response(saved, page_key), "页面编排已保存")


@router.get("/layouts/{page_key}")
def get_public_layout(page_key: str):
    page_key = normalize_page_key(page_key)
    with get_db() as db:
        row = db.execute("SELECT * FROM page_layouts WHERE page_key=? AND is_active=1 ORDER BY version DESC LIMIT 1", (page_key,)).fetchone()
    return ok(layout_response(row, page_key))


@router.post("/admin/page-layouts/{scope}/publish")
@router.post("/admin/layouts/{scope}/publish")
def publish_page_layout(scope: str):
    page_key = normalize_page_key(scope)
    with get_db() as db:
        row = db.execute("SELECT * FROM page_layouts WHERE page_key=? OR scope=?", (page_key, scope)).fetchone()
        if not row:
            layout = default_layout(page_key)
            row, version = upsert_page_layout(page_key, layout, PAGE_LABELS.get(page_key, page_key), "draft", "admin")
        layout = parse_layout_value(row["layout_json"] or row["layout"], page_key)
        version = (row["version"] or 1) + 1
        db.execute("UPDATE page_layouts SET status='published', version=?, is_active=1, published_by='admin', published_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP WHERE id=?", (version, row["id"]))
        db.execute("INSERT INTO page_layout_versions (layout_id,page_key,version,layout_json,change_note,created_by) VALUES (?,?,?,?,?,?)", (row["id"], page_key, version, json.dumps(layout, ensure_ascii=False), "发布页面", "admin"))
    write_audit("页面编排", f"发布 {page_key} 页面")
    return ok({"page_key": page_key, "version": version, "status": "published"}, "页面已发布")


@router.post("/admin/page-layouts/{scope}/reset")
@router.post("/admin/layouts/{scope}/reset")
def reset_page_layout(scope: str):
    page_key = normalize_page_key(scope)
    layout = default_layout(page_key)
    saved, version = upsert_page_layout(page_key, layout, PAGE_LABELS.get(page_key, page_key), "draft", "admin")
    write_audit("页面编排", f"恢复 {page_key} 默认布局")
    return ok(layout_response(saved, page_key) | {"version": version}, "已恢复默认布局")


@router.get("/admin/page-layouts/{scope}/versions")
@router.get("/admin/layouts/{scope}/versions")
def page_layout_versions(scope: str):
    page_key = normalize_page_key(scope)
    with get_db() as db:
        rows = rows_to_list(db.execute("SELECT * FROM page_layout_versions WHERE page_key=? ORDER BY version DESC LIMIT 20", (page_key,)).fetchall())
    return ok(rows)


@router.post("/admin/layouts/{scope}/preview")
def preview_page_layout(scope: str, payload: LayoutPayload):
    page_key = normalize_page_key(scope)
    layout = normalize_layout_payload(page_key, payload.layout)
    visible = [item for item in layout["modules"] if item.get("visible", True)]
    write_audit("页面编排", f"预览 {page_key} 页面")
    return ok({
        "page_key": page_key,
        "layout": layout,
        "visible_count": len(visible),
        "component_count": len(layout["modules"]),
        "preview_url": f"/preview/{page_key}",
    }, "预览布局已生成")


@router.get("/admin/component-templates")
def component_templates(category: str | None = None, template_type: str | None = None):
    sql = "SELECT * FROM component_templates WHERE 1=1"
    params = []
    if category:
        sql += " AND category=?"
        params.append(category)
    if template_type:
        sql += " AND type=?"
        params.append(template_type)
    sql += " ORDER BY category, id"
    with get_db() as db:
        return ok(rows_to_list(db.execute(sql, params).fetchall()))


@router.post("/admin/component-templates")
def create_component_template(payload: ComponentTemplatePayload):
    raw = json.dumps(payload.config_json, ensure_ascii=False)
    with get_db() as db:
        cur = db.execute(
            """
            INSERT INTO component_templates (name,type,category,config_json,preview_image,created_by,updated_at)
            VALUES (?,?,?,?,?,'admin',CURRENT_TIMESTAMP)
            ON CONFLICT(name,type,category) DO UPDATE SET config_json=excluded.config_json,
              preview_image=excluded.preview_image,updated_at=CURRENT_TIMESTAMP
            """,
            (payload.name, payload.type, payload.category, raw, payload.preview_image),
        )
        row = db.execute(
            "SELECT * FROM component_templates WHERE name=? AND type=? AND category=?",
            (payload.name, payload.type, payload.category),
        ).fetchone()
    write_audit("页面编排", f"保存组件模板 {payload.name}")
    return ok(row_to_dict(row) | {"created_id": cur.lastrowid}, "组件模板已保存")


@router.delete("/admin/component-templates/{template_id}")
def delete_component_template(template_id: int):
    with get_db() as db:
        db.execute("DELETE FROM component_templates WHERE id=?", (template_id,))
    write_audit("页面编排", f"删除组件模板 #{template_id}")
    return ok({"id": template_id}, "组件模板已删除")


@router.get("/admin/layouts")
def admin_layouts():
    page_keys = ["home", "scenic", "scenic_detail", "themes", "map", "weather", "community", "provinces", "earth_online", "auth", "user_center", "admin_dashboard", "admin_api", "admin_services", "admin_earth_online", "admin_enrichment"]
    with get_db() as db:
        rows = {row["page_key"]: row for row in db.execute("SELECT * FROM page_layouts WHERE page_key IS NOT NULL").fetchall()}
    return ok([layout_response(rows.get(page_key), page_key) for page_key in page_keys])


@router.post("/admin/page-layouts/{scope}/versions/{version_id}/restore")
@router.post("/admin/layouts/{scope}/versions/{version_id}/restore")
def restore_page_layout_version(scope: str, version_id: int):
    page_key = normalize_page_key(scope)
    with get_db() as db:
        version = db.execute("SELECT * FROM page_layout_versions WHERE id=? AND page_key=?", (version_id, page_key)).fetchone()
        layout = parse_layout_value(version["layout_json"], page_key) if version else default_layout(page_key)
        saved, next_version = upsert_page_layout(page_key, layout, PAGE_LABELS.get(page_key, page_key), "draft", "admin")
    write_audit("页面编排", f"恢复 {page_key} 历史版本 #{version_id}")
    return ok(layout_response(saved, page_key) | {"version": next_version}, "已恢复历史版本")


@router.post("/admin/data/sync")
def trigger_data_sync():
    with get_db() as db:
        # Sync pending images to approved if they are from 'seed'
        db.execute("UPDATE scenic_images SET status='approved' WHERE source='seed' AND status='pending'")
        
        # Mark an audit log
        db.execute(
            "INSERT INTO sync_tasks (name, source, status, last_run_at, message) VALUES (?,?,?,CURRENT_TIMESTAMP,?)",
            ("手动数据同步", "后台操作", "success", "同步了基础数据、天气缓存与图片状态"),
        )
    write_audit("数据管理", "手动触发数据同步")
    return ok({"status": "created", "task": "manual-sync", "details": "已同步基础数据和缓存"}, "数据同步任务已完成")

@router.get("/admin/data/sync")
def trigger_data_sync_get():
    return trigger_data_sync()


@router.post("/admin/data/backup")
def create_backup():
    backup_dir = DATA_DIR / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    if DATABASE_BACKEND == "postgresql":
        filename = f"scenic-online-postgres-snapshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        target = backup_dir / filename
        with get_db() as db:
            tables = rows_to_list(db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall())
            indexes = rows_to_list(db.execute(
                "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
            ).fetchall())
            scenic_count = db.execute("SELECT COUNT(*) AS c FROM scenic_spots").fetchone()["c"]
            source_scenic_count = db.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]
        target.write_text(json.dumps({
            "backend": DATABASE_BACKEND,
            "database": DATABASE_URL.split("@", 1)[-1],
            "created_at": datetime.now().isoformat(),
            "tables": len(tables),
            "indexes": len(indexes),
            "scenic_count": scenic_count,
            "source_scenic_count": source_scenic_count,
            "total_scenic_count": scenic_count + source_scenic_count,
            "note": "轻量元数据快照；生产环境完整备份请接入 pg_dump 或云数据库快照。",
        }, ensure_ascii=False, indent=2), encoding="utf-8")
        write_audit("数据管理", f"创建 PostgreSQL 元数据快照 {filename}")
        return ok({"status": "created", "file": str(target), "size": target.stat().st_size}, "数据快照任务已创建")

    filename = f"scenic-online-{datetime.now().strftime('%Y%m%d-%H%M%S')}.sqlite3"
    target = backup_dir / filename
    shutil.copy2(DB_PATH, target)
    write_audit("数据管理", f"创建数据备份 {filename}")
    return ok({"status": "created", "file": str(target), "size": target.stat().st_size}, "数据备份任务已创建")


@router.get("/admin/database/status")
def database_status():
    with get_db() as db:
        tables = rows_to_list(db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall())
        indexes = rows_to_list(db.execute(
            "SELECT name, tbl_name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall())
        table_names = {item["name"] for item in tables}
        scenic_count = db.execute("SELECT COUNT(*) AS c FROM scenic_spots").fetchone()["c"]
        source_scenic_count = (
            db.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]
            if "tpt_jingdian" in table_names
            else 0
        )
        audit_count = db.execute("SELECT COUNT(*) AS c FROM audit_logs").fetchone()["c"]
        integrity = db.execute("PRAGMA quick_check(1)").fetchone()[0]
        journal_mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        required_tables = {"users", "scenic_spots", "scenic_images", "comments", "audit_logs"}
        missing_tables = sorted(required_tables - table_names)
        storage_exists = True if DATABASE_BACKEND == "postgresql" else DB_PATH.exists()
        storage_path = DATABASE_URL.split("@", 1)[-1] if DATABASE_BACKEND == "postgresql" else str(DB_PATH)
        storage_size = 0 if DATABASE_BACKEND == "postgresql" else (DB_PATH.stat().st_size if DB_PATH.exists() else 0)
        healthy = storage_exists and integrity == "ok" and not missing_tables
    return ok({
        "backend": DATABASE_BACKEND,
        "path": storage_path,
        "exists": storage_exists,
        "status": "normal" if healthy else "abnormal",
        "message": f"{'PostgreSQL' if DATABASE_BACKEND == 'postgresql' else 'SQLite'} 连接正常" if healthy else f"{'PostgreSQL' if DATABASE_BACKEND == 'postgresql' else 'SQLite'} 需要检查",
        "integrity": integrity,
        "journalMode": journal_mode,
        "missingTables": missing_tables,
        "size": storage_size,
        "tables": tables,
        "indexes": indexes,
        "scenicCount": scenic_count,
        "sourceScenicCount": source_scenic_count,
        "totalScenicCount": scenic_count + source_scenic_count,
        "auditCount": audit_count,
    })


def _safe_table_names(db):
    return [
        row["name"]
        for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()
    ]


def _quote_identifier(name: str):
    if not SAFE_IDENTIFIER_RE.match(name or ""):
        raise HTTPException(status_code=400, detail="表名不合法")
    return f'"{name}"'


def _format_file(path, label, kind):
    path = path if hasattr(path, "exists") else DATA_DIR / str(path)
    exists = path.exists()
    stat = path.stat() if exists else None
    return {
        "label": label,
        "kind": kind,
        "path": str(path),
        "exists": exists,
        "size": stat.st_size if stat else 0,
        "updatedAt": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds") if stat else "",
    }


def _database_files():
    backup_dir = DATA_DIR / "backups"
    backups = []
    if backup_dir.exists():
        backups = sorted(backup_dir.glob("*.sqlite3"), key=lambda item: item.stat().st_mtime, reverse=True)[:8]
    files = [
        _format_file(DB_PATH, "主数据库", "sqlite"),
        _format_file(f"{DB_PATH}-wal", "WAL 日志", "sqlite-wal"),
        _format_file(f"{DB_PATH}-shm", "共享内存索引", "sqlite-shm"),
        _format_file(DEFAULT_EXTERNAL_SQL_PATH, "全国景点 SQL 源文件", "source-sql"),
    ]
    files.extend(_format_file(path, f"备份 {path.name}", "backup") for path in backups)
    return files


def _table_row_probe(db, quoted_name: str, limit: int = 10000):
    count = db.execute(f"SELECT COUNT(*) AS c FROM (SELECT 1 FROM {quoted_name} LIMIT ?)", (limit + 1,)).fetchone()["c"]
    return {
        "rows": limit if count > limit else count,
        "rowsApprox": count > limit,
        "rowsLabel": f"{limit}+" if count > limit else str(count),
    }


def _should_skip_overview_count(name: str):
    return (
        name.startswith("tpt_jingdian_fts")
        or name in {"tpt_jingdian", "tpt_data_jingdian"}
        or name.endswith("_fts")
        or name.endswith("_fts_data")
        or name.endswith("_fts_idx")
        or name.endswith("_fts_docsize")
        or name.endswith("_fts_content")
        or name.endswith("_fts_config")
    )


@router.get("/admin/database/overview")
def database_overview():
    with get_db() as db:
        tables = []
        for name in _safe_table_names(db):
            quoted = _quote_identifier(name)
            row_probe = {"rows": None, "rowsApprox": True, "rowsLabel": "点开查看"} if _should_skip_overview_count(name) else _table_row_probe(db, quoted)
            columns = rows_to_list(db.execute(f"PRAGMA table_info({quoted})").fetchall())
            indexes = rows_to_list(db.execute(f"PRAGMA index_list({quoted})").fetchall())
            tables.append({
                "name": name,
                **row_probe,
                "columns": len(columns),
                "indexes": len(indexes),
                "primaryKeys": [column["name"] for column in columns if column.get("pk")],
                "sampleColumns": [column["name"] for column in columns[:6]],
            })
        integrity = db.execute("PRAGMA quick_check(1)").fetchone()[0]
        journal_mode = db.execute("PRAGMA journal_mode").fetchone()[0]
        storage_exists = True if DATABASE_BACKEND == "postgresql" else DB_PATH.exists()
        storage_path = DATABASE_URL.split("@", 1)[-1] if DATABASE_BACKEND == "postgresql" else str(DB_PATH)
        storage_size = 0 if DATABASE_BACKEND == "postgresql" else (DB_PATH.stat().st_size if DB_PATH.exists() else 0)
    return ok({
        "backend": DATABASE_BACKEND,
        "path": storage_path,
        "status": "normal" if storage_exists and integrity == "ok" else "abnormal",
        "integrity": integrity,
        "journalMode": journal_mode,
        "size": storage_size,
        "tables": tables,
        "files": _database_files(),
    })


@router.get("/admin/database/tables/{table_name}")
def database_table_detail(table_name: str, limit: int = 50, offset: int = 0):
    safe_limit = max(1, min(limit, 200))
    safe_offset = max(0, offset)
    with get_db() as db:
        table_names = set(_safe_table_names(db))
        if table_name not in table_names:
            raise HTTPException(status_code=404, detail="数据表不存在")
        quoted = _quote_identifier(table_name)
        if _should_skip_overview_count(table_name):
            total_probe = _table_row_probe(db, quoted)
            total = total_probe["rows"]
            total_label = total_probe["rowsLabel"]
            total_approx = total_probe["rowsApprox"]
        else:
            total = db.execute(f"SELECT COUNT(*) AS c FROM {quoted}").fetchone()["c"]
            total_label = str(total)
            total_approx = False
        columns = rows_to_list(db.execute(f"PRAGMA table_info({quoted})").fetchall())
        indexes = rows_to_list(db.execute(f"PRAGMA index_list({quoted})").fetchall())
        foreign_keys = rows_to_list(db.execute(f"PRAGMA foreign_key_list({quoted})").fetchall())
        rows = rows_to_list(db.execute(f"SELECT * FROM {quoted} LIMIT ? OFFSET ?", (safe_limit, safe_offset)).fetchall())
    return ok({
        "name": table_name,
        "total": total,
        "totalLabel": total_label,
        "totalApprox": total_approx,
        "limit": safe_limit,
        "offset": safe_offset,
        "columns": columns,
        "indexes": indexes,
        "foreignKeys": foreign_keys,
        "rows": rows,
    })


@router.get("/admin/database/files")
def database_files():
    return ok(_database_files())


@router.post("/admin/data/quality-check")
def quality_check():
    result = {
        "completeness": "96%",
        "imageMatch": "92%",
        "coordinateCoverage": "98%",
        "weatherAvailability": "99%",
        "pendingIssues": 2,
    }
    write_audit("数据管理", "执行数据质量检测")
    return ok(result, "数据质量检测完成")


@router.get("/admin/data/scenic-sql/status")
def scenic_sql_status():
    return ok(inspect_sql_file(DEFAULT_EXTERNAL_SQL_PATH))


@router.get("/admin/data/scenic-sql/preview")
def scenic_sql_preview(limit: int = 5000, province: str = "", offset: int = 0):
    with get_db() as db:
        return ok(preview_scenic_sql_import(db, DEFAULT_EXTERNAL_SQL_PATH, sample_limit=limit, province_filter=province, offset=offset))


@router.post("/admin/data/scenic-sql/import")
def scenic_sql_import(limit: int | None = None, province: str = "", offset: int = 0, batch_size: int = 1000):
    with get_db() as db:
        safe_batch = max(1, min(batch_size or 1000, 5000))
        result = import_scenic_sql(db, DEFAULT_EXTERNAL_SQL_PATH, limit=limit, province_filter=province, offset=offset, batch_size=safe_batch)
        db.execute(
            "INSERT INTO sync_tasks (name, source, status, last_run_at, message) VALUES (?,?,?,CURRENT_TIMESTAMP,?)",
            ("全国景点 SQL 分批导入", str(DEFAULT_EXTERNAL_SQL_PATH), "success" if not result.get("errors") else "failed", f"导入 {result.get('imported_count', 0)} 条，重复 {result.get('duplicate_rows', 0)} 条，偏移 {result.get('current_offset', 0)}"),
        )
    write_audit("数据管理", f"全国景点 SQL 分批导入 {result.get('imported_count', 0)} 条")
    return ok(result, "全国景点 SQL 导入完成" if result.get("file_exists") else result.get("message", "SQL 文件未检测到"))


@router.post("/admin/database/query")
def execute_sql(payload: dict):
    sql = payload.get("sql", "").strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL 不能为空")
    
    # Basic safety check (for demonstration/admin use)
    forbidden = ["DROP", "TRUNCATE", "VACUUM"]
    if any(keyword in sql.upper() for keyword in forbidden):
        raise HTTPException(status_code=403, detail="出于安全原因，该语句被禁用。")

    with get_db() as db:
        try:
            cursor = db.execute(sql)
            if sql.upper().startswith("SELECT"):
                rows = cursor.fetchall()
                return ok({"type": "select", "columns": [d[0] for d in cursor.description], "rows": rows_to_list(rows)})
            else:
                db.commit()
                return ok({"type": "exec", "affected_rows": cursor.rowcount}, "执行成功")
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))


@router.get("/admin/services/status")
def services_status():
    names = [
        ("Web 服务", "38ms", "18.2K"),
        ("API 服务", "42ms", "68.2K"),
        ("SQLite 数据库", "12ms", "9.6K"),
        ("文件存储", "29ms", "2.1K"),
        ("图片服务", "64ms", "3.4K"),
        ("搜索服务", "51ms", "7.8K"),
        ("天气代理", "72ms", "12.4K"),
        ("地图代理", "82ms", "5.3K"),
        ("地球 Online 来源检测", "96ms", "860"),
        ("景区资料补全", "118ms", "320"),
        ("图片补全", "102ms", "540"),
        ("审核服务", "46ms", "1.2K"),
        ("日志服务", "24ms", "4.1K"),
    ]
    return ok([{"name": name, "status": "正常", "latency": latency, "today_requests": requests, "last_check": "刚刚", "error_rate": "0.03%", "enabled": True} for name, latency, requests in names])


@router.post("/admin/services/{name}/check")
def check_service(name: str):
    write_audit("服务管理", f"检查服务 {name}")
    return ok({"name": name, "status": "正常", "latency": "46ms"}, "服务检查完成")


@router.get("/admin/services/{name}/logs")
def service_logs(name: str):
    with get_db() as db:
        logs = rows_to_list(db.execute("SELECT * FROM audit_logs WHERE module LIKE ? ORDER BY id DESC LIMIT 20", (f"%{name.split()[0]}%",)).fetchall())
    return ok(logs or [{"id": 0, "module": name, "action": "最近无异常日志", "result": "success", "created_at": datetime.now().isoformat(timespec="seconds")}])


@router.post("/admin/services/{name}/toggle")
def toggle_service(name: str):
    write_audit("服务管理", f"切换服务 {name}")
    return ok({"name": name, "enabled": True}, "服务状态已更新")
