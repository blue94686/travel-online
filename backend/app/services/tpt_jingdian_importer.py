import csv
import re
from pathlib import Path

from app.core.region_utils import label_area

BASE_COLUMNS = (
    "id",
    "title",
    "tel",
    "address",
    "type",
    "areaid",
    "poiid",
    "gcjx",
    "gcjy",
    "longitude",
    "latitude",
)

ENHANCED_COLUMNS = (
    "province",
    "city",
    "district",
    "main_category",
    "theme_slugs",
    "theme_names",
    "tags",
    "summary",
    "description",
    "best_season",
    "audience",
    "recommended_duration",
    "route_idea",
    "quality_score",
    "data_version",
    "updated_at",
)

WEB_COLUMNS = (
    "official_level",
    "level_source",
    "level_source_url",
    "level_verified_at",
    "a_level_year",
    "web_province",
    "web_city",
    "web_district",
    "web_address",
    "web_longitude",
    "web_latitude",
    "web_source_confidence",
    "web_update_note",
)

MEDIA_COLUMNS = (
    "cover_image_url",
    "gallery",
    "image_source",
    "image_source_url",
    "image_license",
    "image_attribution",
    "image_status",
    "media_checked_at",
    "profile_source",
    "profile_source_url",
    "profile_updated_at",
)

COLUMNS = BASE_COLUMNS + ENHANCED_COLUMNS + WEB_COLUMNS + MEDIA_COLUMNS
INSERT_PREFIX = "INSERT INTO `tpt_data_jingdian` VALUES ("

TPT_JINGDIAN_SCHEMA = """
CREATE TABLE IF NOT EXISTS tpt_jingdian (
  source_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  phone TEXT DEFAULT '',
  address TEXT DEFAULT '',
  category_path TEXT DEFAULT '',
  category TEXT DEFAULT '',
  areaid TEXT DEFAULT '',
  province_code TEXT DEFAULT '',
  city_code TEXT DEFAULT '',
  district_code TEXT DEFAULT '',
  province TEXT DEFAULT '',
  city TEXT DEFAULT '',
  district TEXT DEFAULT '',
  poiid TEXT DEFAULT '',
  gcj_lng REAL,
  gcj_lat REAL,
  longitude REAL,
  latitude REAL,
  main_category TEXT DEFAULT '',
  theme_slugs TEXT DEFAULT '',
  theme_names TEXT DEFAULT '',
  tags TEXT DEFAULT '',
  summary TEXT DEFAULT '',
  description TEXT DEFAULT '',
  best_season TEXT DEFAULT '',
  audience TEXT DEFAULT '',
  recommended_duration TEXT DEFAULT '',
  route_idea TEXT DEFAULT '',
  quality_score INTEGER DEFAULT 0,
  data_version TEXT DEFAULT '',
  source_updated_at TEXT DEFAULT '',
  official_level TEXT DEFAULT '',
  level_source TEXT DEFAULT '',
  level_source_url TEXT DEFAULT '',
  level_verified_at TEXT DEFAULT '',
  a_level_year TEXT DEFAULT '',
  web_province TEXT DEFAULT '',
  web_city TEXT DEFAULT '',
  web_district TEXT DEFAULT '',
  web_address TEXT DEFAULT '',
  web_longitude REAL,
  web_latitude REAL,
  web_source_confidence TEXT DEFAULT '',
  web_update_note TEXT DEFAULT '',
  cover_image_url TEXT DEFAULT '',
  gallery TEXT DEFAULT '[]',
  image_source TEXT DEFAULT '',
  image_source_url TEXT DEFAULT '',
  image_license TEXT DEFAULT '',
  image_attribution TEXT DEFAULT '',
  image_status TEXT DEFAULT 'missing',
  media_checked_at TEXT,
  profile_source TEXT DEFAULT '',
  profile_source_url TEXT DEFAULT '',
  profile_updated_at TEXT,
  search_text TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_name ON tpt_jingdian(name);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_areaid ON tpt_jingdian(areaid);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_category ON tpt_jingdian(category);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_location ON tpt_jingdian(longitude, latitude);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_province ON tpt_jingdian(province);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_city ON tpt_jingdian(city);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_district ON tpt_jingdian(district);
"""

TPT_JINGDIAN_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS tpt_jingdian_fts USING fts5(
  source_id UNINDEXED,
  name,
  address,
  category_path,
  category,
  search_text,
  tokenize='trigram'
);
"""


def _parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_insert_values(line):
    line = line.strip()
    if not line.startswith(INSERT_PREFIX):
        return None
    if line.endswith(";"):
        line = line[:-1]
    body = line[len(INSERT_PREFIX) :]
    if body.endswith(")"):
        body = body[:-1]
    return next(csv.reader([body], quotechar="'", escapechar="\\", skipinitialspace=True))


def iter_tpt_jingdian_rows(sql_path):
    path = Path(sql_path)
    with path.open("r", encoding="utf-8", newline="") as stream:
        for line in stream:
            values = _parse_insert_values(line)
            if not values:
                continue
            if len(values) < len(BASE_COLUMNS):
                continue
            padded = values[:len(COLUMNS)] + [""] * max(0, len(COLUMNS) - len(values))
            row = dict(zip(COLUMNS, padded))
            yield {
                "id": int(row["id"]),
                "title": row["title"],
                "tel": row["tel"],
                "address": row["address"],
                "type": row["type"],
                "areaid": row["areaid"],
                "poiid": row["poiid"],
                "gcjx": row["gcjx"],
                "gcjy": row["gcjy"],
                "longitude": _parse_float(row["longitude"]),
                "latitude": _parse_float(row["latitude"]),
                "province": row.get("province") or "",
                "city": row.get("city") or "",
                "district": row.get("district") or "",
                "main_category": row.get("main_category") or "",
                "theme_slugs": row.get("theme_slugs") or "",
                "theme_names": row.get("theme_names") or "",
                "tags": row.get("tags") or "",
                "summary": row.get("summary") or "",
                "description": row.get("description") or "",
                "best_season": row.get("best_season") or "",
                "audience": row.get("audience") or "",
                "recommended_duration": row.get("recommended_duration") or "",
                "route_idea": row.get("route_idea") or "",
                "quality_score": int(_parse_float(row.get("quality_score")) or 0),
                "data_version": row.get("data_version") or "",
                "source_updated_at": row.get("updated_at") or "",
                "official_level": row.get("official_level") or "",
                "level_source": row.get("level_source") or "",
                "level_source_url": row.get("level_source_url") or "",
                "level_verified_at": row.get("level_verified_at") or "",
                "a_level_year": row.get("a_level_year") or "",
                "web_province": row.get("web_province") or "",
                "web_city": row.get("web_city") or "",
                "web_district": row.get("web_district") or "",
                "web_address": row.get("web_address") or "",
                "web_longitude": _parse_float(row.get("web_longitude")),
                "web_latitude": _parse_float(row.get("web_latitude")),
                "web_source_confidence": row.get("web_source_confidence") or "",
                "web_update_note": row.get("web_update_note") or "",
                "cover_image_url": row.get("cover_image_url") or "",
                "gallery": row.get("gallery") or "[]",
                "image_source": row.get("image_source") or "",
                "image_source_url": row.get("image_source_url") or "",
                "image_license": row.get("image_license") or "",
                "image_attribution": row.get("image_attribution") or "",
                "image_status": row.get("image_status") or "",
                "media_checked_at": row.get("media_checked_at") or "",
                "profile_source": row.get("profile_source") or "",
                "profile_source_url": row.get("profile_source_url") or "",
                "profile_updated_at": row.get("profile_updated_at") or "",
            }


def normalize_tpt_jingdian_row(row):
    category_parts = [part.strip() for part in (row.get("type") or "").split(";") if part.strip()]
    areaid = row.get("areaid") or ""
    enhanced_province = row.get("province") or ""
    enhanced_city = row.get("city") or ""
    enhanced_district = row.get("district") or ""
    item = {
        "source_id": row["id"],
        "name": row.get("title") or "",
        "phone": row.get("tel") or "",
        "address": row.get("address") or "",
        "category_path": row.get("type") or "",
        "category": category_parts[-1] if category_parts else "",
        "areaid": areaid,
        "province_code": areaid[:2],
        "city_code": areaid[:4],
        "district_code": areaid[:6],
        "province": enhanced_province or (label_area(areaid[:2], 2) if len(areaid) >= 2 else ""),
        "city": enhanced_city or (label_area(areaid[:4], 4) if len(areaid) >= 4 else ""),
        "district": enhanced_district or (label_area(areaid[:6], 6) if len(areaid) >= 6 else ""),
        "poiid": row.get("poiid") or "",
        "gcj_lng": _parse_float(row.get("gcjx")),
        "gcj_lat": _parse_float(row.get("gcjy")),
        "longitude": row.get("longitude"),
        "latitude": row.get("latitude"),
        "main_category": row.get("main_category") or "",
        "theme_slugs": row.get("theme_slugs") or "",
        "theme_names": row.get("theme_names") or "",
        "tags": row.get("tags") or "",
        "summary": row.get("summary") or "",
        "description": row.get("description") or "",
        "best_season": row.get("best_season") or "",
        "audience": row.get("audience") or "",
        "recommended_duration": row.get("recommended_duration") or "",
        "route_idea": row.get("route_idea") or "",
        "quality_score": int(row.get("quality_score") or 0),
        "data_version": row.get("data_version") or "",
        "source_updated_at": row.get("source_updated_at") or "",
        "official_level": row.get("official_level") or "",
        "level_source": row.get("level_source") or "",
        "level_source_url": row.get("level_source_url") or "",
        "level_verified_at": row.get("level_verified_at") or "",
        "a_level_year": row.get("a_level_year") or "",
        "web_province": row.get("web_province") or "",
        "web_city": row.get("web_city") or "",
        "web_district": row.get("web_district") or "",
        "web_address": row.get("web_address") or "",
        "web_longitude": _parse_float(row.get("web_longitude")),
        "web_latitude": _parse_float(row.get("web_latitude")),
        "web_source_confidence": row.get("web_source_confidence") or "",
        "web_update_note": row.get("web_update_note") or "",
        "cover_image_url": row.get("cover_image_url") or "",
        "gallery": row.get("gallery") or "[]",
        "image_source": row.get("image_source") or "",
        "image_source_url": row.get("image_source_url") or "",
        "image_license": row.get("image_license") or "",
        "image_attribution": row.get("image_attribution") or "",
        "image_status": row.get("image_status") or "missing",
        "media_checked_at": row.get("media_checked_at") or None,
        "profile_source": row.get("profile_source") or "",
        "profile_source_url": row.get("profile_source_url") or "",
        "profile_updated_at": row.get("profile_updated_at") or None,
    }
    item["search_text"] = " ".join(
        part for part in (
            item["name"],
            item["address"],
            item["category_path"],
            item["areaid"],
            item["poiid"],
            item["main_category"],
            item["theme_names"],
            item["tags"],
            item["summary"],
            item["description"],
            item["official_level"],
            item["level_source"],
            item["web_address"],
            item["web_update_note"],
        ) if part
    )
    return item


def ensure_tpt_jingdian_schema(db):
    db.executescript(TPT_JINGDIAN_SCHEMA)
    columns = {row["name"] for row in db.execute("PRAGMA table_info(tpt_jingdian)").fetchall()}
    if "search_text" not in columns:
        db.execute("ALTER TABLE tpt_jingdian ADD COLUMN search_text TEXT DEFAULT ''")
    migrations = {
        "main_category": "ALTER TABLE tpt_jingdian ADD COLUMN main_category TEXT DEFAULT ''",
        "theme_slugs": "ALTER TABLE tpt_jingdian ADD COLUMN theme_slugs TEXT DEFAULT ''",
        "theme_names": "ALTER TABLE tpt_jingdian ADD COLUMN theme_names TEXT DEFAULT ''",
        "tags": "ALTER TABLE tpt_jingdian ADD COLUMN tags TEXT DEFAULT ''",
        "summary": "ALTER TABLE tpt_jingdian ADD COLUMN summary TEXT DEFAULT ''",
        "description": "ALTER TABLE tpt_jingdian ADD COLUMN description TEXT DEFAULT ''",
        "best_season": "ALTER TABLE tpt_jingdian ADD COLUMN best_season TEXT DEFAULT ''",
        "audience": "ALTER TABLE tpt_jingdian ADD COLUMN audience TEXT DEFAULT ''",
        "recommended_duration": "ALTER TABLE tpt_jingdian ADD COLUMN recommended_duration TEXT DEFAULT ''",
        "route_idea": "ALTER TABLE tpt_jingdian ADD COLUMN route_idea TEXT DEFAULT ''",
        "quality_score": "ALTER TABLE tpt_jingdian ADD COLUMN quality_score INTEGER DEFAULT 0",
        "data_version": "ALTER TABLE tpt_jingdian ADD COLUMN data_version TEXT DEFAULT ''",
        "source_updated_at": "ALTER TABLE tpt_jingdian ADD COLUMN source_updated_at TEXT DEFAULT ''",
        "official_level": "ALTER TABLE tpt_jingdian ADD COLUMN official_level TEXT DEFAULT ''",
        "level_source": "ALTER TABLE tpt_jingdian ADD COLUMN level_source TEXT DEFAULT ''",
        "level_source_url": "ALTER TABLE tpt_jingdian ADD COLUMN level_source_url TEXT DEFAULT ''",
        "level_verified_at": "ALTER TABLE tpt_jingdian ADD COLUMN level_verified_at TEXT DEFAULT ''",
        "a_level_year": "ALTER TABLE tpt_jingdian ADD COLUMN a_level_year TEXT DEFAULT ''",
        "web_province": "ALTER TABLE tpt_jingdian ADD COLUMN web_province TEXT DEFAULT ''",
        "web_city": "ALTER TABLE tpt_jingdian ADD COLUMN web_city TEXT DEFAULT ''",
        "web_district": "ALTER TABLE tpt_jingdian ADD COLUMN web_district TEXT DEFAULT ''",
        "web_address": "ALTER TABLE tpt_jingdian ADD COLUMN web_address TEXT DEFAULT ''",
        "web_longitude": "ALTER TABLE tpt_jingdian ADD COLUMN web_longitude REAL",
        "web_latitude": "ALTER TABLE tpt_jingdian ADD COLUMN web_latitude REAL",
        "web_source_confidence": "ALTER TABLE tpt_jingdian ADD COLUMN web_source_confidence TEXT DEFAULT ''",
        "web_update_note": "ALTER TABLE tpt_jingdian ADD COLUMN web_update_note TEXT DEFAULT ''",
        "cover_image_url": "ALTER TABLE tpt_jingdian ADD COLUMN cover_image_url TEXT DEFAULT ''",
        "gallery": "ALTER TABLE tpt_jingdian ADD COLUMN gallery TEXT DEFAULT '[]'",
        "image_source": "ALTER TABLE tpt_jingdian ADD COLUMN image_source TEXT DEFAULT ''",
        "image_source_url": "ALTER TABLE tpt_jingdian ADD COLUMN image_source_url TEXT DEFAULT ''",
        "image_license": "ALTER TABLE tpt_jingdian ADD COLUMN image_license TEXT DEFAULT ''",
        "image_attribution": "ALTER TABLE tpt_jingdian ADD COLUMN image_attribution TEXT DEFAULT ''",
        "image_status": "ALTER TABLE tpt_jingdian ADD COLUMN image_status TEXT DEFAULT 'missing'",
        "media_checked_at": "ALTER TABLE tpt_jingdian ADD COLUMN media_checked_at TEXT",
        "profile_source": "ALTER TABLE tpt_jingdian ADD COLUMN profile_source TEXT DEFAULT ''",
        "profile_source_url": "ALTER TABLE tpt_jingdian ADD COLUMN profile_source_url TEXT DEFAULT ''",
        "profile_updated_at": "ALTER TABLE tpt_jingdian ADD COLUMN profile_updated_at TEXT",
    }
    for column, statement in migrations.items():
        if column not in columns:
            db.execute(statement)
    if is_tpt_fts_available(db):
        db.executescript(TPT_JINGDIAN_FTS_SCHEMA)


def is_tpt_fts_available(db):
    try:
        db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS tpt_jingdian_fts_probe USING fts5(value, tokenize='trigram')")
        db.execute("DROP TABLE IF EXISTS tpt_jingdian_fts_probe")
        return True
    except Exception:
        return False


def import_tpt_jingdian_sql(db, sql_path, batch_size=5000, limit=None):
    ensure_tpt_jingdian_schema(db)
    rebuild_fts = _has_fts_table(db)
    if rebuild_fts:
        db.execute("DELETE FROM tpt_jingdian_fts")
    batch = []
    imported = 0
    for row in iter_tpt_jingdian_rows(sql_path):
        item = normalize_tpt_jingdian_row(row)
        if not item["name"]:
            continue
        batch.append(
            (
                item["source_id"],
                item["name"],
                item["phone"],
                item["address"],
                item["category_path"],
                item["category"],
                item["areaid"],
                item["province_code"],
                item["city_code"],
                item["district_code"],
                item["province"],
                item["city"],
                item["district"],
                item["poiid"],
                item["gcj_lng"],
                item["gcj_lat"],
                item["longitude"],
                item["latitude"],
                item["main_category"],
                item["theme_slugs"],
                item["theme_names"],
                item["tags"],
                item["summary"],
                item["description"],
                item["best_season"],
                item["audience"],
                item["recommended_duration"],
                item["route_idea"],
                item["quality_score"],
                item["data_version"],
                item["source_updated_at"],
                item["official_level"],
                item["level_source"],
                item["level_source_url"],
                item["level_verified_at"],
                item["a_level_year"],
                item["web_province"],
                item["web_city"],
                item["web_district"],
                item["web_address"],
                item["web_longitude"],
                item["web_latitude"],
                item["web_source_confidence"],
                item["web_update_note"],
                item["cover_image_url"],
                item["gallery"],
                item["image_source"],
                item["image_source_url"],
                item["image_license"],
                item["image_attribution"],
                item["image_status"],
                item["media_checked_at"],
                item["profile_source"],
                item["profile_source_url"],
                item["profile_updated_at"],
                item["search_text"],
            )
        )
        imported += 1
        if len(batch) >= batch_size:
            _flush_batch(db, batch, sync_fts=False)
            batch.clear()
        if limit and imported >= limit:
            break
    if batch:
        _flush_batch(db, batch, sync_fts=False)
    if rebuild_fts:
        rebuild_tpt_jingdian_fts(db)
    return imported


def ensure_tpt_jingdian_loaded(db, sql_path):
    ensure_tpt_jingdian_schema(db)
    path = Path(sql_path)
    current = db.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]
    if current > 0:
        return {"imported": 0, "existing_count": current, "skipped": True, "reason": "already_loaded"}
    if not path.exists():
        return {"imported": 0, "existing_count": 0, "skipped": True, "reason": "missing_sql_file"}
    imported = import_tpt_jingdian_sql(db, path)
    return {"imported": imported, "existing_count": imported, "skipped": False, "reason": "imported"}


def _flush_batch(db, batch, sync_fts=True):
    db.executemany(
        """
        INSERT INTO tpt_jingdian (
          source_id,name,phone,address,category_path,category,areaid,province_code,city_code,district_code,
          province,city,district,poiid,gcj_lng,gcj_lat,longitude,latitude,
          main_category,theme_slugs,theme_names,tags,summary,description,best_season,audience,recommended_duration,route_idea,
          quality_score,data_version,source_updated_at,
          official_level,level_source,level_source_url,level_verified_at,a_level_year,web_province,web_city,web_district,web_address,
          web_longitude,web_latitude,web_source_confidence,web_update_note,
          cover_image_url,gallery,image_source,image_source_url,image_license,image_attribution,image_status,media_checked_at,
          profile_source,profile_source_url,profile_updated_at,search_text
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        ON CONFLICT(source_id) DO UPDATE SET
          name=excluded.name,
          phone=excluded.phone,
          address=excluded.address,
          category_path=excluded.category_path,
          category=excluded.category,
          areaid=excluded.areaid,
          province_code=excluded.province_code,
          city_code=excluded.city_code,
          district_code=excluded.district_code,
          province=excluded.province,
          city=excluded.city,
          district=excluded.district,
          poiid=excluded.poiid,
          gcj_lng=excluded.gcj_lng,
          gcj_lat=excluded.gcj_lat,
          longitude=excluded.longitude,
          latitude=excluded.latitude,
          main_category=excluded.main_category,
          theme_slugs=excluded.theme_slugs,
          theme_names=excluded.theme_names,
          tags=excluded.tags,
          summary=excluded.summary,
          description=excluded.description,
          best_season=excluded.best_season,
          audience=excluded.audience,
          recommended_duration=excluded.recommended_duration,
          route_idea=excluded.route_idea,
          quality_score=excluded.quality_score,
          data_version=excluded.data_version,
          source_updated_at=excluded.source_updated_at,
          official_level=excluded.official_level,
          level_source=excluded.level_source,
          level_source_url=excluded.level_source_url,
          level_verified_at=excluded.level_verified_at,
          a_level_year=excluded.a_level_year,
          web_province=excluded.web_province,
          web_city=excluded.web_city,
          web_district=excluded.web_district,
          web_address=excluded.web_address,
          web_longitude=excluded.web_longitude,
          web_latitude=excluded.web_latitude,
          web_source_confidence=excluded.web_source_confidence,
          web_update_note=excluded.web_update_note,
          cover_image_url=excluded.cover_image_url,
          gallery=excluded.gallery,
          image_source=excluded.image_source,
          image_source_url=excluded.image_source_url,
          image_license=excluded.image_license,
          image_attribution=excluded.image_attribution,
          image_status=excluded.image_status,
          media_checked_at=excluded.media_checked_at,
          profile_source=excluded.profile_source,
          profile_source_url=excluded.profile_source_url,
          profile_updated_at=excluded.profile_updated_at,
          search_text=excluded.search_text
        """,
        batch,
    )
    if sync_fts and _has_fts_table(db):
        db.executemany("DELETE FROM tpt_jingdian_fts WHERE source_id=?", [(row[0],) for row in batch])
        db.executemany(
            """
            INSERT INTO tpt_jingdian_fts (source_id,name,address,category_path,category,search_text)
            VALUES (?,?,?,?,?,?)
            """,
            [(row[0], row[1], row[3], row[4], row[5], row[-1]) for row in batch],
        )


def rebuild_tpt_jingdian_fts(db):
    if not _has_fts_table(db):
        return 0
    db.execute("DELETE FROM tpt_jingdian_fts")
    db.execute(
        """
        INSERT INTO tpt_jingdian_fts (source_id,name,address,category_path,category,search_text)
        SELECT source_id,name,address,category_path,category,search_text
        FROM tpt_jingdian
        """
    )
    return db.execute("SELECT COUNT(*) AS c FROM tpt_jingdian_fts").fetchone()["c"]


def _has_fts_table(db):
    row = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tpt_jingdian_fts'").fetchone()
    return row is not None


def _count_insert_lines(sql_path):
    path = Path(sql_path)
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8", newline="") as stream:
        return sum(1 for line in stream if line.startswith("INSERT INTO ") and "tpt_data_jingdian" in line)


def get_tpt_jingdian_status(db, sql_path):
    ensure_tpt_jingdian_schema(db)
    path = Path(sql_path)
    count = db.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]
    indexed = db.execute("SELECT COUNT(*) AS c FROM tpt_jingdian_fts").fetchone()["c"] if _has_fts_table(db) else 0
    return {
        "sql_path": str(path),
        "file_exists": path.exists(),
        "file_size_bytes": path.stat().st_size if path.exists() else 0,
        "source_record_count": _count_insert_lines(path),
        "imported_count": count,
        "indexed_count": indexed,
        "fts_available": _has_fts_table(db),
    }


def _split_search_terms(value):
    return [part.strip() for part in re.split(r"[\s,，、|/]+", value or "") if part.strip()]


def search_tpt_jingdian(db, keyword="", areaid="", province="", city="", district="", category="", limit=50, offset=0):
    ensure_tpt_jingdian_schema(db)
    keyword = (keyword or "").strip()
    limit = max(1, min(int(limit), 200))
    offset = max(0, int(offset))
    can_use_fts = _has_fts_table(db)
    use_fts = can_use_fts and len(keyword) >= 3
    table_expr = "tpt_jingdian"
    where = ["1=1"]
    params = []
    if use_fts:
        table_expr = "tpt_jingdian_fts f JOIN tpt_jingdian ON tpt_jingdian.source_id=f.source_id"
        where.append("tpt_jingdian_fts MATCH ?")
        params.append(_build_fts_query(keyword))
    elif keyword:
        where.append("(name LIKE ? OR address LIKE ? OR category_path LIKE ? OR search_text LIKE ?)")
        like = f"%{keyword}%"
        params.extend([like, like, like, like])
    
    if areaid:
        if len(areaid) == 2:
            where.append("province_code = ?")
            params.append(areaid)
        elif len(areaid) == 4:
            where.append("city_code = ?")
            params.append(areaid)
        elif len(areaid) == 6:
            where.append("district_code = ?")
            params.append(areaid)
        else:
            where.append("areaid LIKE ?")
            params.append(f"{areaid}%")
            
    if province:
        where.append("province = ?")
        params.append(province)
    if city:
        where.append("city = ?")
        params.append(city)
    if district:
        where.append("district = ?")
        params.append(district)
        
    category_terms = _split_search_terms(category)
    if category_terms:
        clauses = []
        for term in category_terms:
            clauses.append("(name LIKE ? OR address LIKE ? OR category_path LIKE ? OR category LIKE ? OR search_text LIKE ?)")
            like = f"%{term}%"
            params.extend([like, like, like, like, like])
        where.append("(" + " OR ".join(clauses) + ")")
    where_sql = " AND ".join(where)
    count_sql = f"SELECT COUNT(*) AS c FROM {table_expr} WHERE {where_sql}"
    total = db.execute(count_sql, params).fetchone()["c"]
    if use_fts:
        order_sql = _search_order_sql(keyword, "tpt_jingdian.", include_rank=True)
        select_sql = f"SELECT tpt_jingdian.* FROM {table_expr} WHERE {where_sql} {order_sql} LIMIT ? OFFSET ?"
    else:
        order_sql = _search_order_sql(keyword, "", include_rank=False)
        select_sql = f"SELECT * FROM {table_expr} WHERE {where_sql} {order_sql} LIMIT ? OFFSET ?"
    rows = db.execute(select_sql, [*params, limit, offset]).fetchall()
    return {
        "items": [dict(row) for row in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
        "fts_enabled": can_use_fts,
        "search_mode": "fts" if use_fts else "like",
    }


def _build_fts_query(keyword):
    return f'"{keyword.replace(chr(34), chr(34) + chr(34))}"'


def _search_order_sql(keyword, prefix="", include_rank=False):
    if not keyword:
        return f"ORDER BY {prefix}source_id ASC"
    escaped = keyword.replace("'", "''")
    rank_part = "rank, " if include_rank else ""
    return (
        "ORDER BY "
        f"CASE WHEN {prefix}name = '{escaped}' THEN 0 "
        f"WHEN {prefix}name LIKE '{escaped}%' THEN 1 "
        f"WHEN {prefix}name LIKE '%{escaped}%' THEN 2 ELSE 3 END, "
        f"{rank_part}length({prefix}name) ASC, {prefix}source_id ASC"
    )
