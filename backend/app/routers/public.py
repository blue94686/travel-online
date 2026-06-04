import os
import uuid
import io
from pathlib import Path
from PIL import Image

from fastapi import APIRouter, Query, UploadFile, File, Form
from pydantic import BaseModel

from app.core.database import get_db, rows_to_list
from app.core.response import ok
from app.services.image_quality_service import check_image, check_image_url
from app.core.region_utils import region_group_for_province
from app.services.scenic_service import _label_area, get_scenic_region_options, normalize_region_name

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

router = APIRouter()


class UploadCreate(BaseModel):
    scenic_id: int = 1
    file_url: str = ""
    file_type: str = "image"


@router.get("/health")
def health():
    return ok({"status": "ok", "service": "Scenic Online"})


@router.get("/provinces")
def provinces():
    with get_db() as db:
        rows = db.execute("SELECT DISTINCT province FROM scenic_spots ORDER BY province").fetchall()
    return ok([row["province"] for row in rows])


@router.get("/regions/provinces")
def region_provinces():
    with get_db() as db:
        rows = rows_to_list(db.execute(
            """
            SELECT region_group, province, COUNT(DISTINCT city) AS city_count, MIN(sort_order) AS province_sort_order
            FROM regions
            GROUP BY region_group, province
            ORDER BY province_sort_order, province
            """
        ).fetchall())
        scenic_counts = {row["province"]: row["count"] for row in db.execute(
            "SELECT province, COUNT(*) AS count FROM scenic_spots GROUP BY province"
        ).fetchall()}
        tpt_counts = {
            _label_area(row["code"], 2): row["count"]
            for row in db.execute(
                "SELECT substr(areaid,1,2) AS code, COUNT(*) AS count FROM tpt_jingdian WHERE areaid!='' GROUP BY code"
            ).fetchall()
        }
    grouped = {}
    seen_provinces = set()
    for row in rows:
        seen_provinces.add(row["province"])
        grouped.setdefault(row["region_group"] or "其他", []).append({
            "province": row["province"],
            "city_count": row["city_count"],
            "scenic_count": scenic_counts.get(row["province"], 0) + tpt_counts.get(row["province"], 0),
        })
    for province, count in sorted(tpt_counts.items()):
        if not province or province in seen_provinces:
            continue
        group = region_group_for_province(province)
        grouped.setdefault(group, []).append({
            "province": province,
            "city_count": 0,
            "scenic_count": count,
        })
    return ok({"groups": grouped, "items": rows})


@router.get("/regions/cities")
def region_cities(province: str = Query("")):
    province = normalize_region_name(province)
    with get_db() as db:
        rows = rows_to_list(db.execute(
            """
            SELECT city, MIN(sort_order) AS city_sort_order
            FROM regions
            WHERE province=? AND city!=''
            GROUP BY city
            ORDER BY city_sort_order, city
            """,
            (province,),
        ).fetchall())
    merged = [row["city"] for row in rows]
    for city in get_scenic_region_options(province=province).get("cities", []):
        if city not in merged:
            merged.append(city)
    return ok(merged)


@router.get("/regions/districts")
def region_districts(province: str = Query(""), city: str = Query("")):
    province = normalize_region_name(province)
    city = normalize_region_name(city)
    with get_db() as db:
        rows = rows_to_list(db.execute(
            """
            SELECT district, MIN(sort_order) AS district_sort_order
            FROM regions
            WHERE province=? AND city=? AND district!=''
            GROUP BY district
            ORDER BY district_sort_order, district
            """,
            (province, city),
        ).fetchall())
    merged = [row["district"] for row in rows]
    for district in get_scenic_region_options(province=province, city=city).get("districts", []):
        if district not in merged:
            merged.append(district)
    return ok(merged)


@router.get("/routes/plan")
def route_plan(
    from_place: str = Query("杭州市"),
    to: str = Query("杭州西湖"),
    transport: str = Query("自驾"),
    theme: str = Query("风景"),
):
    stops = [from_place, "沿途服务点", to]
    distance = 18 + len(to) * 3
    duration = "半天" if transport in ("自驾", "公共交通") else "1天"
    return ok({
        "title": f"{from_place} 到 {to}",
        "transport": transport,
        "theme": theme,
        "distance_km": distance,
        "duration": duration,
        "stops": stops,
        "highlights": ["顺路景点", "天气提醒", "美食补给", "公开实况入口"],
    })


@router.get("/live")
def live():
    return ok([
        {"id": 1, "scenic": "杭州西湖", "title": "苏堤湖面实况", "status": "public", "image": "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=800&q=80"},
        {"id": 2, "scenic": "黄山风景区", "title": "山顶云海窗口", "status": "public", "image": "https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=800&q=80"},
    ])


@router.post("/uploads")
async def uploads(
    file: UploadFile = File(None),
    scenic_id: int = Form(1),
    file_type: str = Form("image"),
    file_url: str = Form(""),
):
    # Handle real file upload
    if file and file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in {'.jpg', '.jpeg', '.png', '.webp', '.gif'}:
            return ok({"status": "rejected"}, "不支持的文件格式")
            
        content = await file.read()
        if len(content) > 10 * 1024 * 1024:
            return ok({"status": "rejected"}, "文件过大 (最大 10MB)")
            
        try:
            # Process with Pillow
            img = Image.open(io.BytesIO(content))
            # Convert to RGB if necessary (for saving as WebP)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
                
            safe_name_base = uuid.uuid4().hex
            file_path_hd = UPLOAD_DIR / f"{safe_name_base}_hd.webp"
            file_path_thumb = UPLOAD_DIR / f"{safe_name_base}_thumb.webp"
            
            # Save HD (max 1920x1080)
            img.thumbnail((1920, 1080), Image.Resampling.LANCZOS)
            img.save(file_path_hd, "WEBP", quality=85)
            
            # Save Thumb (max 400x400)
            img.thumbnail((400, 400), Image.Resampling.LANCZOS)
            img.save(file_path_thumb, "WEBP", quality=75)
            
            final_url = f"/uploads/{file_path_hd.name}"
            # Let's check quality of the HD image
            quality = check_image(str(file_path_hd))
            image_status = "pending" if quality["status"] != "reject" else "rejected"
        except Exception as e:
            print("Image processing error:", e)
            return ok({"status": "rejected"}, "图片处理失败")
    else:
        final_url = file_url or "https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?auto=format&fit=crop&w=900&q=80"
        quality = check_image_url(final_url)
        image_status = "pending"

    with get_db() as db:
        cur = db.execute(
            "INSERT INTO uploads (user_id,scenic_id,file_url,file_type,status) VALUES (?,?,?,?,?)",
            (1, scenic_id, final_url, file_type, image_status),
        )
        db.execute(
            "INSERT INTO scenic_images (scenic_id,url,status,source) VALUES (?,?,?,?)",
            (scenic_id, final_url, image_status, "user_upload"),
        )
    return ok({"id": cur.lastrowid, "status": image_status, "quality": quality}, "上传已进入审核队列" if image_status == "pending" else "图片未通过质检")
