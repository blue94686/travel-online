import json
import os
import re
from pathlib import Path

from app.core.config import TPT_JINGDIAN_SQL_PATH
from app.services.scenic_service import _label_area as scenic_label_area
from app.services.scenic_service import normalize_region_name
from app.services.tpt_jingdian_importer import _count_insert_lines, iter_tpt_jingdian_rows, normalize_tpt_jingdian_row

MODULE_PATH = Path(__file__).resolve()
PROJECT_ROOT = MODULE_PATH.parents[3]
BACKEND_ROOT = MODULE_PATH.parents[2]
DEFAULT_EXTERNAL_SQL_PATH = PROJECT_ROOT / "tpt_data_jingdian.sql"


def resolve_sql_path(sql_path=None):
    if sql_path:
        path = Path(sql_path)
        if path.exists() and path.is_file():
            return path

    candidates = [
        os.environ.get("TPT_JINGDIAN_SQL_PATH", ""),
        DEFAULT_EXTERNAL_SQL_PATH,
        BACKEND_ROOT / "tpt_data_jingdian.sql",
        TPT_JINGDIAN_SQL_PATH,
        Path.cwd() / "tpt_data_jingdian.sql",
        Path.cwd().parent / "tpt_data_jingdian.sql",
        Path("/Users/shaoyuhao/Desktop/sk/旅游景区/scenic-online/tpt_data_jingdian.sql"),
        Path("/Users/shaoyuhao/Desktop/sk/旅游景区/UI图片/tpt_data_jingdian.sql"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(candidate)
        if path.exists() and path.is_file():
            return path
    return Path(sql_path or DEFAULT_EXTERNAL_SQL_PATH)


def _label_area(code: str, size: int):
    if not code:
        return ""
    return scenic_label_area(code, size)


def _slugify(value: str, source_id: int):
    text = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", value or "").strip("-").lower()
    return f"sql-{source_id}-{text[:40]}" if text else f"sql-{source_id}"


def _clean_import_address(address: str, province: str, city: str, district: str, areaid: str):
    address = (address or "").strip()
    if areaid:
        for source, target in (
            (f"{areaid[:2]}省级区域", province),
            (f"{areaid[:4]}地区", city),
            (f"{areaid[:6]}区县", district),
        ):
            if source and target:
                address = address.replace(source, target)
    if not address or re.search(r"\d+(省级区域|地区|区县)", address):
        address = f"{province}{city}{district}".strip() or "地址待补充"
    return address


def _to_scenic_payload(row: dict):
    item = normalize_tpt_jingdian_row(row)
    province = _label_area(item["province_code"], 2)
    city = _label_area(item["city_code"], 4)
    district = _label_area(item["district_code"], 6)
    province = item.get("province") or province
    city = item.get("city") or city
    district = item.get("district") or district
    raw_tags = []
    for value in (item.get("tags"), item.get("theme_names"), item.get("main_category"), item.get("category_path")):
        raw_tags.extend(part.strip() for part in re.split(r"[,，;；|/]", value or "") if part.strip())
    tags = []
    for tag in raw_tags:
        if tag and tag not in tags:
            tags.append(tag)
    if item.get("official_level"):
        for tag in (f"{item['official_level']}景区", "国家A级景区"):
            if tag not in tags:
                tags.append(tag)
    summary = item.get("summary") or f"{item['category_path'] or '全国旅游景点'} · 来自本地 SQL 数据源"
    address = _clean_import_address(item["address"], province, city, district, item["areaid"])
    if (not address or address == "地址待补充") and item.get("web_address"):
        address = item["web_address"]
    description = item.get("description") or f"{item['name']} 是本地全国旅游景点 SQL 数据源中的目的地，适合纳入景区检索、路线规划和资料补全流程。"
    longitude = item["longitude"] if item["longitude"] is not None else item.get("web_longitude")
    latitude = item["latitude"] if item["latitude"] is not None else item.get("web_latitude")
    quality_score = item.get("quality_score") or 0
    try:
        rating = max(3.8, min(4.8, 3.8 + (float(quality_score) / 100)))
    except (TypeError, ValueError):
        rating = 4.3
    return {
        "slug": _slugify(item["name"], item["source_id"]),
        "name": item["name"],
        "province": province,
        "city": city,
        "district": district,
        "normalized_province": province,
        "normalized_city": city,
        "normalized_district": district,
        "level": item.get("official_level") or item.get("main_category") or item["category"] or "全国景点",
        "rating": rating,
        "address": address,
        "latitude": latitude,
        "longitude": longitude,
        "summary": summary,
        "description": description,
        "tags": tags[-4:] if tags else ["全国景点", "数据导入"],
        "ticket_price": "以景区公示为准",
        "opening_hours": "以景区公示为准",
        "best_season": item.get("best_season") or "四季皆宜",
        "cover_image_url": "",
        "gallery": [],
        "weather": {"city": city.replace("市", "") or city, "temp": 22, "condition": "多云", "air": "良 46"},
        "map_point": {"lat": latitude, "lng": longitude},
        "nearby_pois": [],
        "recommended_routes": [item.get("route_idea") or "规则推荐路线"],
        "source_url": item.get("level_source_url") or f"local-sql:tpt_data_jingdian:{item['source_id']}",
        "suitable_groups": [part.strip() for part in re.split(r"[、,，]", item.get("audience") or "") if part.strip()],
        "recommended_duration": item.get("recommended_duration") or "",
        "completeness_score": int(quality_score or 0),
    }


def inspect_sql_file(sql_path=None, sample_size=8):
    path = resolve_sql_path(sql_path)
    if not path.exists():
        return {
            "file_exists": False,
            "path": str(path),
            "checked_paths": [str(p) for p in [
                DEFAULT_EXTERNAL_SQL_PATH,
                BACKEND_ROOT / "tpt_data_jingdian.sql",
                TPT_JINGDIAN_SQL_PATH,
            ]],
            "file_size_bytes": 0,
            "total_rows": 0,
            "sample": [],
            "message": "未检测到 tpt_data_jingdian.sql，请放置到指定路径或通过后台上传导入",
        }
    sample = []
    missing = 0
    total = _count_insert_lines(path)
    for row in iter_tpt_jingdian_rows(path):
        payload = _to_scenic_payload(row)
        if not payload["name"] or not payload["province"] or not payload["city"]:
            missing += 1
        if len(sample) < sample_size:
            sample.append(payload)
        if len(sample) >= sample_size:
            break
    return {
        "file_exists": True,
        "path": str(path),
        "checked_paths": [],
        "file_size_bytes": path.stat().st_size,
        "total_rows": total,
        "missing_field_rows": missing,
        "sample": sample,
        "message": "已检测到本地全国旅游景点 SQL 文件",
    }


def preview_scenic_sql_import(db, sql_path=None, sample_limit=5000, province_filter="", offset=0):
    province_filter = normalize_region_name(province_filter)
    path = resolve_sql_path(sql_path)
    info = inspect_sql_file(path)
    if not info["file_exists"]:
        return info | {"importable_rows": 0, "duplicate_rows": 0}
    existing = {
        (row["name"], row["province"], row["city"])
        for row in db.execute("SELECT name, province, city FROM scenic_spots").fetchall()
    }
    importable = 0
    duplicate = 0
    missing = 0
    scanned = 0
    matched = 0
    filtered_sample = []
    for row in iter_tpt_jingdian_rows(path):
        if scanned >= sample_limit:
            break
        payload = _to_scenic_payload(row)
        if province_filter and payload["province"] != province_filter:
            continue
        if matched < offset:
            matched += 1
            continue
        matched += 1
        scanned += 1
        if len(filtered_sample) < 8:
            filtered_sample.append(payload)
        key = (payload["name"], payload["province"], payload["city"])
        if not payload["name"] or not payload["province"] or not payload["city"]:
            missing += 1
        elif key in existing:
            duplicate += 1
        else:
            importable += 1
    return info | {
        "preview_limit": sample_limit,
        "preview_offset": offset,
        "province_filter": province_filter,
        "preview_scanned_rows": scanned,
        "preview_importable_rows": importable,
        "preview_duplicate_rows": duplicate,
        "preview_missing_field_rows": missing,
        "sample": filtered_sample,
    }


def import_scenic_sql(db, sql_path=None, limit=None, province_filter="", offset=0, batch_size=1000, task_id=None):
    province_filter = normalize_region_name(province_filter)
    path = resolve_sql_path(sql_path)
    info = inspect_sql_file(path)
    if not info["file_exists"]:
        return info | {"imported_count": 0, "duplicate_rows": 0, "missing_field_rows": 0, "errors": []}
    existing = {
        (row["name"], row["province"], row["city"])
        for row in db.execute("SELECT name, province, city FROM scenic_spots").fetchall()
    }
    fields = [
        "slug", "name", "province", "city", "district", "normalized_province", "normalized_city", "normalized_district", "level", "rating", "address", "latitude", "longitude",
        "summary", "description", "tags", "ticket_price", "opening_hours", "best_season", "cover_image_url",
        "gallery", "weather", "map_point", "nearby_pois", "recommended_routes", "source_url",
        "suitable_groups", "recommended_duration", "completeness_score",
    ]
    inserted = 0
    duplicate = 0
    missing = 0
    errors = []
    batch = []
    if task_id is None:
        task_id = _create_import_task(db, path, info["total_rows"], offset, batch_size, province_filter)
    matched = 0
    consumed = 0
    for row_number, row in enumerate(iter_tpt_jingdian_rows(path), start=1):
        payload = _to_scenic_payload(row)
        if province_filter and payload["province"] != province_filter:
            continue
        if matched < offset:
            matched += 1
            continue
        matched += 1
        consumed += 1
        key = (payload["name"], payload["province"], payload["city"])
        if not payload["name"] or not payload["province"] or not payload["city"]:
            missing += 1
            _record_import_error(db, task_id, row_number, row, "缺少名称、省份或城市")
            continue
        if key in existing:
            duplicate += 1
            continue
        existing.add(key)
        batch.append(tuple(json.dumps(payload[field], ensure_ascii=False) if isinstance(payload[field], (list, dict)) else payload[field] for field in fields))
        if len(batch) >= max(1, int(batch_size or 1000)):
            inserted += _flush(db, fields, batch, errors)
            batch.clear()
        if limit and inserted + len(batch) >= limit:
            break
    if batch:
        inserted += _flush(db, fields, batch, errors)
    status = "finished" if limit is None else "paused"
    db.execute(
        """
        UPDATE scenic_import_tasks
        SET status=?, imported_rows=?, duplicate_rows=?, failed_rows=?, current_offset=?, finished_at=CASE WHEN ?='finished' THEN CURRENT_TIMESTAMP ELSE finished_at END,
            message=?
        WHERE id=?
        """,
        (status, inserted, duplicate, missing + len(errors), offset + consumed, status, "导入完成" if status == "finished" else "批次导入完成，可继续", task_id),
    )
    return info | {
        "task_id": task_id,
        "imported_count": inserted,
        "duplicate_rows": duplicate,
        "missing_field_rows": missing,
        "current_offset": offset + consumed,
        "batch_size": batch_size,
        "province_filter": province_filter,
        "errors": errors[:20],
    }


def _create_import_task(db, sql_path, total_rows, offset, batch_size, province_filter):
    cur = db.execute(
        """
        INSERT INTO scenic_import_tasks (file_path,status,total_rows,current_offset,batch_size,province_filter,message)
        VALUES (?,?,?,?,?,?,?)
        """,
        (str(sql_path), "running", total_rows, offset, batch_size, province_filter, "正在导入"),
    )
    return cur.lastrowid


def _record_import_error(db, task_id, row_number, row, error_message):
    db.execute(
        "INSERT INTO scenic_import_errors (task_id,row_number,raw_text,error_message) VALUES (?,?,?,?)",
        (task_id, row_number, json.dumps(row, ensure_ascii=False)[:1000], error_message),
    )


def _flush(db, fields, batch, errors):
    try:
        db.executemany(
            f"INSERT OR IGNORE INTO scenic_spots ({','.join(fields)}) VALUES ({','.join(['?'] * len(fields))})",
            batch,
        )
        return len(batch)
    except Exception as exc:
        errors.append(str(exc))
        return 0
