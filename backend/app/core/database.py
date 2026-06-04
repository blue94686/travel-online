import json
import re
import sqlite3
from contextlib import contextmanager

from app.core.config import DATA_DIR, DB_PATH
from app.core.database_adapters import PostgresConnection, is_postgres_enabled
from app.core.region_utils import is_fallback_area_label, label_area, region_group_for_province


DATA_DIR.mkdir(parents=True, exist_ok=True)


@contextmanager
def get_db():
    if is_postgres_enabled():
        conn = PostgresConnection()
    else:
        conn = sqlite3.connect(DB_PATH, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        if hasattr(conn, "rollback"):
            conn.rollback()
        raise
    finally:
        conn.close()


def row_to_dict(row):
    if row is None:
        return None
    item = dict(row)
    for key in ("tags", "gallery", "weather", "map_point", "nearby_pois", "recommended_routes", "suitable_groups", "must_see_spots", "recommended_itinerary", "photo_spots", "travel_tips", "nearby_food", "nearby_hotels", "linked_scenic_recommendations", "permissions", "payload", "images", "stops", "layout", "layout_json", "config_json", "settings_json", "weather_json", "forecast_json", "live_json", "raw_payload_json", "diff_json"):
        if key in item and isinstance(item[key], str):
            try:
                item[key] = json.loads(item[key])
            except json.JSONDecodeError:
                pass
    return item


def rows_to_list(rows):
    return [row_to_dict(row) for row in rows]


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT UNIQUE NOT NULL,
  password_hash TEXT DEFAULT '',
  nickname TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'user',
  status TEXT NOT NULL DEFAULT 'active',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scenic_spots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  province TEXT NOT NULL,
  city TEXT NOT NULL,
  district TEXT NOT NULL,
  normalized_province TEXT DEFAULT '',
  normalized_city TEXT DEFAULT '',
  normalized_district TEXT DEFAULT '',
  level TEXT,
  rating REAL,
  address TEXT,
  latitude REAL,
  longitude REAL,
  summary TEXT,
  description TEXT,
  tags TEXT,
  ticket_price TEXT,
  opening_hours TEXT,
  best_season TEXT,
  cover_image_url TEXT,
  gallery TEXT,
  weather TEXT,
  map_point TEXT,
  nearby_pois TEXT,
  recommended_routes TEXT,
  slogan TEXT DEFAULT '',
  suitable_groups TEXT DEFAULT '[]',
  recommended_duration TEXT DEFAULT '',
  history_culture TEXT DEFAULT '',
  highlights TEXT DEFAULT '',
  traffic_info TEXT DEFAULT '',
  parking_info TEXT DEFAULT '',
  public_transport TEXT DEFAULT '',
  self_driving_route TEXT DEFAULT '',
  accessibility_tips TEXT DEFAULT '',
  must_see_spots TEXT DEFAULT '[]',
  recommended_itinerary TEXT DEFAULT '[]',
  photo_spots TEXT DEFAULT '[]',
  travel_tips TEXT DEFAULT '[]',
  nearby_food TEXT DEFAULT '[]',
  nearby_hotels TEXT DEFAULT '[]',
  linked_scenic_recommendations TEXT DEFAULT '[]',
  phone TEXT DEFAULT '',
  completeness_score INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scenic_images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenic_id INTEGER,
  url TEXT NOT NULL,
  thumbnail_url TEXT DEFAULT '',
  status TEXT DEFAULT 'pending',
  is_cover INTEGER DEFAULT 0,
  source TEXT DEFAULT 'seed',
  source_url TEXT DEFAULT '',
  license TEXT DEFAULT '',
  attribution TEXT DEFAULT '',
  provider TEXT DEFAULT '',
  quality_score INTEGER DEFAULT 0,
  last_checked_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS comments (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenic_id INTEGER,
  user_id INTEGER,
  nickname TEXT,
  content TEXT NOT NULL,
  rating REAL DEFAULT 5,
  images TEXT DEFAULT '[]',
  status TEXT DEFAULT 'pending',
  ip TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS favorites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  scenic_id INTEGER,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS trips (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  title TEXT NOT NULL,
  start_date TEXT,
  end_date TEXT,
  status TEXT DEFAULT 'draft',
  payload TEXT DEFAULT '{}',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS trip_routes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  trip_id INTEGER,
  user_id INTEGER,
  title TEXT NOT NULL,
  transport TEXT,
  stops TEXT DEFAULT '[]',
  distance_km REAL DEFAULT 0,
  duration_hours REAL DEFAULT 0,
  payload TEXT DEFAULT '{}',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS uploads (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER,
  scenic_id INTEGER,
  file_url TEXT NOT NULL,
  file_type TEXT DEFAULT 'image',
  status TEXT DEFAULT 'pending',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS api_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL,
  enabled INTEGER DEFAULT 0,
  endpoint TEXT DEFAULT '',
  api_key_masked TEXT DEFAULT '',
  api_key_secret TEXT DEFAULT '',
  settings_json TEXT DEFAULT '{}',
  status TEXT DEFAULT 'not_configured',
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scenic_themes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT UNIQUE NOT NULL,
  name TEXT UNIQUE NOT NULL,
  description TEXT DEFAULT '',
  guide TEXT DEFAULT '',
  image_url TEXT DEFAULT '',
  icon TEXT DEFAULT '',
  keywords_json TEXT DEFAULT '[]',
  season TEXT DEFAULT '',
  audience TEXT DEFAULT '',
  route_idea TEXT DEFAULT '',
  sort_order INTEGER DEFAULT 100,
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS api_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  endpoint TEXT NOT NULL,
  status_code INTEGER,
  latency_ms INTEGER,
  result TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  operator TEXT NOT NULL,
  module TEXT NOT NULL,
  action TEXT NOT NULL,
  ip TEXT DEFAULT '',
  result TEXT DEFAULT 'success',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sync_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT DEFAULT 'idle',
  last_run_at TEXT,
  message TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS roles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL,
  permissions TEXT DEFAULT '[]'
);
CREATE TABLE IF NOT EXISTS system_settings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  setting_key TEXT UNIQUE NOT NULL,
  setting_value TEXT DEFAULT '',
  value_type TEXT DEFAULT 'string',
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS permissions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  code TEXT UNIQUE NOT NULL,
  label TEXT NOT NULL,
  module TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS ip_blacklist (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ip TEXT UNIQUE NOT NULL,
  reason TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS regions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  province TEXT NOT NULL,
  city TEXT NOT NULL DEFAULT '',
  district TEXT NOT NULL DEFAULT '',
  region_group TEXT NOT NULL DEFAULT '',
  sort_order INTEGER DEFAULT 0,
  UNIQUE(province, city, district)
);
CREATE TABLE IF NOT EXISTS community_posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER DEFAULT 1,
  scenic_id INTEGER DEFAULT 1,
  nickname TEXT DEFAULT '游客',
  category TEXT DEFAULT '点评',
  title TEXT DEFAULT '',
  content TEXT NOT NULL,
  images TEXT DEFAULT '[]',
  status TEXT DEFAULT 'pending',
  likes INTEGER DEFAULT 0,
  reports INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS page_layouts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scope TEXT UNIQUE NOT NULL,
  page_key TEXT,
  name TEXT DEFAULT '',
  layout TEXT NOT NULL DEFAULT '[]',
  layout_json TEXT,
  status TEXT DEFAULT 'draft',
  version INTEGER DEFAULT 1,
  is_active INTEGER DEFAULT 1,
  created_by TEXT DEFAULT 'system',
  updated_by TEXT DEFAULT 'system',
  published_by TEXT DEFAULT '',
  published_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS page_layout_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  layout_id INTEGER,
  page_key TEXT NOT NULL,
  version INTEGER NOT NULL,
  layout_json TEXT NOT NULL,
  change_note TEXT DEFAULT '',
  created_by TEXT DEFAULT 'admin',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS component_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  category TEXT NOT NULL,
  config_json TEXT NOT NULL DEFAULT '{}',
  preview_image TEXT DEFAULT '',
  created_by TEXT DEFAULT 'admin',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(name, type, category)
);
CREATE TABLE IF NOT EXISTS user_layouts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  page_key TEXT NOT NULL,
  layout_json TEXT NOT NULL DEFAULT '[]',
  version INTEGER DEFAULT 1,
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, page_key)
);
CREATE TABLE IF NOT EXISTS user_layout_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_layout_id INTEGER,
  user_id INTEGER NOT NULL,
  page_key TEXT NOT NULL,
  version INTEGER NOT NULL,
  layout_json TEXT NOT NULL,
  change_note TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS earth_online_sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  slug TEXT UNIQUE NOT NULL,
  category TEXT NOT NULL,
  country TEXT DEFAULT '',
  province TEXT DEFAULT '',
  city TEXT DEFAULT '',
  linked_scenic_id INTEGER,
  source_platform TEXT NOT NULL,
  source_url TEXT NOT NULL,
  embed_url TEXT DEFAULT '',
  thumbnail_url TEXT DEFAULT '',
  description TEXT DEFAULT '',
  is_live INTEGER DEFAULT 0,
  is_embeddable INTEGER DEFAULT 0,
  authorization_note TEXT DEFAULT '',
  license_note TEXT DEFAULT '',
  review_status TEXT DEFAULT 'candidate',
  availability_status TEXT DEFAULT 'unknown',
  last_checked_at TEXT,
  failure_count INTEGER DEFAULT 0,
  risk_level TEXT DEFAULT 'low',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS earth_online_checks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_id INTEGER NOT NULL,
  check_type TEXT DEFAULT 'manual',
  status TEXT NOT NULL,
  http_status INTEGER,
  message TEXT DEFAULT '',
  checked_at TEXT DEFAULT CURRENT_TIMESTAMP,
  response_ms INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS earth_online_favorites (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  source_id INTEGER NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(user_id, source_id)
);
CREATE TABLE IF NOT EXISTS enrichment_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenic_id INTEGER NOT NULL,
  keyword TEXT NOT NULL,
  task_type TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  started_at TEXT DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  message TEXT DEFAULT '',
  created_by TEXT DEFAULT 'admin'
);
CREATE TABLE IF NOT EXISTS enrichment_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER NOT NULL,
  scenic_id INTEGER NOT NULL,
  result_type TEXT NOT NULL,
  title TEXT NOT NULL,
  url TEXT DEFAULT '',
  thumbnail_url TEXT DEFAULT '',
  source_name TEXT DEFAULT '',
  snippet TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  status TEXT DEFAULT 'pending',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scenic_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenic_id INTEGER NOT NULL,
  field_name TEXT NOT NULL,
  candidate_value TEXT NOT NULL,
  source_url TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  review_status TEXT DEFAULT 'pending',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scenic_profile_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenic_id INTEGER NOT NULL,
  candidate_type TEXT NOT NULL,
  title TEXT DEFAULT '',
  content TEXT NOT NULL,
  source_url TEXT NOT NULL,
  source_name TEXT DEFAULT '',
  source_type TEXT NOT NULL DEFAULT 'generated_draft',
  confidence INTEGER DEFAULT 0,
  risk_level TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'pending',
  raw_payload_json TEXT DEFAULT '{}',
  diff_json TEXT DEFAULT '{}',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TEXT,
  reviewed_by TEXT DEFAULT '',
  UNIQUE(scenic_id, candidate_type, source_url, content)
);
CREATE TABLE IF NOT EXISTS scenic_image_candidates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenic_id INTEGER NOT NULL,
  image_url TEXT NOT NULL,
  thumbnail_url TEXT DEFAULT '',
  source_url TEXT DEFAULT '',
  source_name TEXT DEFAULT '',
  source_type TEXT DEFAULT 'bing',
  license TEXT DEFAULT '',
  attribution TEXT DEFAULT '',
  provider TEXT DEFAULT '',
  risk_level TEXT DEFAULT 'medium',
  status TEXT DEFAULT 'pending',
  raw_payload_json TEXT DEFAULT '{}',
  title TEXT DEFAULT '',
  confidence REAL DEFAULT 0,
  quality_score INTEGER DEFAULT 0,
  availability_status TEXT DEFAULT 'unchecked',
  failure_count INTEGER DEFAULT 0,
  last_checked_at TEXT,
  review_status TEXT DEFAULT 'pending',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS nearby_recommendations (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scenic_id INTEGER NOT NULL,
  recommended_scenic_id INTEGER NOT NULL,
  reason TEXT DEFAULT '',
  distance_text TEXT DEFAULT '',
  score REAL DEFAULT 0,
  source TEXT DEFAULT 'rule',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(scenic_id, recommended_scenic_id)
);
CREATE TABLE IF NOT EXISTS weather_cache (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  city TEXT NOT NULL,
  provider TEXT DEFAULT '',
  weather_json TEXT DEFAULT '{}',
  forecast_json TEXT DEFAULT '[]',
  live_json TEXT DEFAULT '[]',
  source TEXT DEFAULT 'fallback',
  expires_at TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(city, provider)
);
CREATE TABLE IF NOT EXISTS map_request_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider TEXT NOT NULL,
  request_type TEXT NOT NULL,
  request_params TEXT DEFAULT '{}',
  status TEXT DEFAULT '',
  response_ms INTEGER DEFAULT 0,
  message TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS scenic_import_tasks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL,
  status TEXT DEFAULT 'pending',
  total_rows INTEGER DEFAULT 0,
  imported_rows INTEGER DEFAULT 0,
  duplicate_rows INTEGER DEFAULT 0,
  failed_rows INTEGER DEFAULT 0,
  current_offset INTEGER DEFAULT 0,
  batch_size INTEGER DEFAULT 1000,
  province_filter TEXT DEFAULT '',
  started_at TEXT DEFAULT CURRENT_TIMESTAMP,
  finished_at TEXT,
  message TEXT DEFAULT '',
  created_by TEXT DEFAULT 'admin'
);
CREATE TABLE IF NOT EXISTS scenic_import_errors (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  task_id INTEGER,
  row_number INTEGER,
  raw_text TEXT DEFAULT '',
  error_message TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
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
  search_text TEXT DEFAULT '',
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS banners (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  image_url TEXT NOT NULL,
  link_url TEXT DEFAULT '',
  order_index INTEGER DEFAULT 0,
  is_active INTEGER DEFAULT 1,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS articles (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  content TEXT NOT NULL,
  author TEXT DEFAULT '管理员',
  category TEXT DEFAULT '攻略',
  cover_image TEXT DEFAULT '',
  is_published INTEGER DEFAULT 1,
  view_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS auth_codes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL,
  code TEXT NOT NULL,
  purpose TEXT DEFAULT 'login',
  expires_at TEXT NOT NULL,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS search_history (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id INTEGER NOT NULL,
  keyword TEXT NOT NULL,
  result_count INTEGER DEFAULT 0,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS hot_searches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  keyword TEXT UNIQUE NOT NULL,
  category TEXT DEFAULT 'scenic',
  search_count INTEGER DEFAULT 1,
  is_manual INTEGER DEFAULT 0,
  updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_banners_active ON banners(is_active);
CREATE INDEX IF NOT EXISTS idx_articles_published ON articles(is_published);
CREATE INDEX IF NOT EXISTS idx_articles_category ON articles(category);
CREATE INDEX IF NOT EXISTS idx_scenic_region ON scenic_spots(province, city, district);
CREATE INDEX IF NOT EXISTS idx_scenic_province ON scenic_spots(province);
CREATE INDEX IF NOT EXISTS idx_scenic_city ON scenic_spots(city);
CREATE INDEX IF NOT EXISTS idx_scenic_district ON scenic_spots(district);
CREATE INDEX IF NOT EXISTS idx_scenic_name ON scenic_spots(name);
CREATE INDEX IF NOT EXISTS idx_scenic_level ON scenic_spots(level);
CREATE INDEX IF NOT EXISTS idx_scenic_tags ON scenic_spots(tags);
CREATE INDEX IF NOT EXISTS idx_scenic_slug ON scenic_spots(slug);
CREATE INDEX IF NOT EXISTS idx_scenic_images_status ON scenic_images(status);
CREATE INDEX IF NOT EXISTS idx_comments_status ON comments(status);
CREATE INDEX IF NOT EXISTS idx_regions_province ON regions(province);
CREATE INDEX IF NOT EXISTS idx_regions_city ON regions(province, city);
CREATE INDEX IF NOT EXISTS idx_community_posts_status ON community_posts(status);
CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_sync_tasks_last_run ON sync_tasks(last_run_at);
CREATE INDEX IF NOT EXISTS idx_earth_sources_category ON earth_online_sources(category);
CREATE INDEX IF NOT EXISTS idx_earth_sources_review_status ON earth_online_sources(review_status);
CREATE INDEX IF NOT EXISTS idx_earth_sources_availability ON earth_online_sources(availability_status);
CREATE INDEX IF NOT EXISTS idx_earth_sources_platform ON earth_online_sources(source_platform);
CREATE INDEX IF NOT EXISTS idx_earth_checks_source_id ON earth_online_checks(source_id);
CREATE INDEX IF NOT EXISTS idx_earth_favorites_user_id ON earth_online_favorites(user_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_tasks_scenic_id ON enrichment_tasks(scenic_id);
CREATE INDEX IF NOT EXISTS idx_enrichment_results_task_id ON enrichment_results(task_id);
CREATE INDEX IF NOT EXISTS idx_scenic_candidates_scenic_id ON scenic_candidates(scenic_id);
CREATE INDEX IF NOT EXISTS idx_scenic_profile_candidates_scenic_id ON scenic_profile_candidates(scenic_id);
CREATE INDEX IF NOT EXISTS idx_scenic_profile_candidates_status ON scenic_profile_candidates(status);
CREATE INDEX IF NOT EXISTS idx_scenic_image_candidates_scenic_id ON scenic_image_candidates(scenic_id);
CREATE INDEX IF NOT EXISTS idx_nearby_recommendations_scenic_id ON nearby_recommendations(scenic_id);
CREATE INDEX IF NOT EXISTS idx_page_layout_versions_page_key ON page_layout_versions(page_key);
CREATE INDEX IF NOT EXISTS idx_component_templates_type ON component_templates(type);
CREATE INDEX IF NOT EXISTS idx_component_templates_category ON component_templates(category);
CREATE INDEX IF NOT EXISTS idx_user_layouts_user_id ON user_layouts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_layouts_page_key ON user_layouts(page_key);
CREATE INDEX IF NOT EXISTS idx_user_layout_versions_user_id ON user_layout_versions(user_id);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_name ON tpt_jingdian(name);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_areaid ON tpt_jingdian(areaid);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_category ON tpt_jingdian(category);
CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_location ON tpt_jingdian(longitude, latitude);
CREATE INDEX IF NOT EXISTS idx_weather_cache_city ON weather_cache(city, provider);
CREATE INDEX IF NOT EXISTS idx_map_request_logs_created_at ON map_request_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_scenic_import_tasks_status ON scenic_import_tasks(status);
CREATE INDEX IF NOT EXISTS idx_scenic_import_errors_task_id ON scenic_import_errors(task_id);
CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
CREATE INDEX IF NOT EXISTS idx_search_history_keyword ON search_history(keyword);
CREATE INDEX IF NOT EXISTS idx_hot_searches_category ON hot_searches(category);
CREATE INDEX IF NOT EXISTS idx_hot_searches_count ON hot_searches(search_count DESC);
"""


def init_db():
    with get_db() as db:
        db.executescript(SCHEMA)
        migrate_db(db)


def _area_labels(areaid):
    areaid = (areaid or "").strip()
    if len(areaid) < 2:
        return "", "", ""
    province = label_area(areaid[:2], 2)
    city = label_area(areaid[:4], 4) if len(areaid) >= 4 else ""
    district = label_area(areaid[:6], 6) if len(areaid) >= 6 else ""
    return province, city, district


def _contains_fallback_area_label(value):
    return bool(re.search(r"\d+(省级区域|地区|区县)", value or ""))


def _clean_imported_address(address, province, city, district, areaid):
    address = (address or "").strip()
    if areaid:
        replacements = (
            (f"{areaid[:2]}省级区域", province),
            (f"{areaid[:4]}地区", city),
            (f"{areaid[:6]}区县", district),
        )
        for source, target in replacements:
            if source and target:
                address = address.replace(source, target)
    if not address or _contains_fallback_area_label(address):
        address = f"{province}{city}{district}".strip() or "地址待补充"
    return address


def _clean_imported_weather(weather, city):
    try:
        payload = json.loads(weather) if isinstance(weather, str) and weather else {}
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    weather_city = payload.get("city") or ""
    if not weather_city or _contains_fallback_area_label(weather_city):
        payload["city"] = (city or "").replace("市", "") or city or "目的地"
    return json.dumps(payload, ensure_ascii=False)


def _backfill_tpt_region_labels(db):
    needs_backfill = db.execute(
        """
        SELECT 1
        FROM tpt_jingdian
        WHERE areaid!=''
          AND (
            province='' OR city='' OR district=''
            OR province GLOB '[0-9]*省级区域'
            OR city GLOB '[0-9]*地区'
            OR district GLOB '[0-9]*区县'
          )
        LIMIT 1
        """
    ).fetchone()
    if not needs_backfill:
        return
    rows = db.execute(
        """
        SELECT substr(areaid,1,2) AS province_code,
               substr(areaid,1,4) AS city_code,
               substr(areaid,1,6) AS district_code
        FROM tpt_jingdian
        WHERE areaid!=''
        GROUP BY substr(areaid,1,2), substr(areaid,1,4), substr(areaid,1,6)
        """
    ).fetchall()
    db.execute("DROP TABLE IF EXISTS temp._area_label_backfill")
    db.execute(
        """
        CREATE TEMP TABLE _area_label_backfill (
          district_code TEXT PRIMARY KEY,
          province TEXT NOT NULL,
          city TEXT NOT NULL,
          district TEXT NOT NULL
        )
        """
    )
    db.executemany(
        """
        INSERT OR REPLACE INTO _area_label_backfill (district_code, province, city, district)
        VALUES (?,?,?,?)
        """,
        [
            (
                row["district_code"],
                label_area(row["province_code"], 2),
                label_area(row["city_code"], 4),
                label_area(row["district_code"], 6),
            )
            for row in rows
            if row["district_code"]
        ],
    )
    db.execute(
        """
        UPDATE tpt_jingdian
        SET province=(SELECT province FROM _area_label_backfill WHERE district_code=substr(tpt_jingdian.areaid,1,6)),
            city=(SELECT city FROM _area_label_backfill WHERE district_code=substr(tpt_jingdian.areaid,1,6)),
            district=(SELECT district FROM _area_label_backfill WHERE district_code=substr(tpt_jingdian.areaid,1,6))
        WHERE areaid!=''
          AND EXISTS (SELECT 1 FROM _area_label_backfill WHERE district_code=substr(tpt_jingdian.areaid,1,6))
        """
    )
    db.execute("DROP TABLE IF EXISTS temp._area_label_backfill")


def _backfill_imported_scenic_region_labels(db):
    needs_backfill = db.execute(
        """
        SELECT 1
        FROM scenic_spots
        WHERE source_url LIKE 'local-sql:tpt_data_jingdian:%'
          AND (
            province='' OR city='' OR district=''
          )
        LIMIT 1
        """
    ).fetchone()
    if not needs_backfill:
        return
    rows = db.execute(
        """
        SELECT s.id, s.address, s.weather, t.areaid
        FROM scenic_spots s
        JOIN tpt_jingdian t ON s.source_url = 'local-sql:tpt_data_jingdian:' || t.source_id
        WHERE t.areaid!=''
        """
    ).fetchall()
    updates = []
    for row in rows:
        province, city, district = _area_labels(row["areaid"])
        if province and city:
            address = _clean_imported_address(row["address"], province, city, district, row["areaid"])
            weather = _clean_imported_weather(row["weather"], city)
            updates.append((province, city, district, province, city, district, address, weather, row["id"]))
    if updates:
        db.executemany(
            """
            UPDATE scenic_spots
            SET province=?, city=?, district=?,
                normalized_province=?, normalized_city=?, normalized_district=?,
                address=?, weather=?
            WHERE id=?
            """,
            updates,
        )


def _sync_regions_from_destination_data(db):
    bad_region = db.execute(
        """
        SELECT 1
        FROM regions
        WHERE province GLOB '[0-9]*省级区域'
           OR city GLOB '[0-9]*地区'
           OR district GLOB '[0-9]*区县'
        LIMIT 1
        """
    ).fetchone()
    region_count = db.execute("SELECT COUNT(*) AS c FROM regions").fetchone()["c"]
    if not bad_region and region_count > 1000:
        return
    db.execute(
        """
        DELETE FROM regions
        WHERE province GLOB '[0-9]*省级区域'
           OR city GLOB '[0-9]*地区'
           OR district GLOB '[0-9]*区县'
        """
    )
    tpt_rows = db.execute(
        """
        SELECT province, city, district, COUNT(*) AS c
        FROM tpt_jingdian
        WHERE province!='' AND city!='' AND district!=''
        GROUP BY province, city, district
        """
    ).fetchall()
    scenic_rows = db.execute(
        """
        SELECT province, city, district, COUNT(*) AS c
        FROM scenic_spots
        WHERE province!='' AND city!='' AND district!=''
        GROUP BY province, city, district
        """
    ).fetchall()
    payload = {}
    for row in [*tpt_rows, *scenic_rows]:
        if is_fallback_area_label(row["province"]) or is_fallback_area_label(row["city"]) or is_fallback_area_label(row["district"]):
            continue
        key = (row["province"], row["city"], row["district"])
        payload[key] = payload.get(key, 0) + int(row["c"] or 0)
    if payload:
        db.executemany(
            """
            INSERT OR IGNORE INTO regions (region_group, province, city, district, sort_order)
            VALUES (?,?,?,?,?)
            """,
            [
                (region_group_for_province(province), province, city, district, min(9999, 1000 + count))
                for (province, city, district), count in payload.items()
            ],
        )


def migrate_db(db):
    columns = {row["name"] for row in db.execute("PRAGMA table_info(scenic_spots)").fetchall()}
    for name, ddl in {
        "official_website": "ALTER TABLE scenic_spots ADD COLUMN official_website TEXT DEFAULT ''",
        "source_url": "ALTER TABLE scenic_spots ADD COLUMN source_url TEXT DEFAULT ''",
        "last_enriched_at": "ALTER TABLE scenic_spots ADD COLUMN last_enriched_at TEXT",
        "normalized_province": "ALTER TABLE scenic_spots ADD COLUMN normalized_province TEXT DEFAULT ''",
        "normalized_city": "ALTER TABLE scenic_spots ADD COLUMN normalized_city TEXT DEFAULT ''",
        "normalized_district": "ALTER TABLE scenic_spots ADD COLUMN normalized_district TEXT DEFAULT ''",
        "slogan": "ALTER TABLE scenic_spots ADD COLUMN slogan TEXT DEFAULT ''",
        "suitable_groups": "ALTER TABLE scenic_spots ADD COLUMN suitable_groups TEXT DEFAULT '[]'",
        "recommended_duration": "ALTER TABLE scenic_spots ADD COLUMN recommended_duration TEXT DEFAULT ''",
        "history_culture": "ALTER TABLE scenic_spots ADD COLUMN history_culture TEXT DEFAULT ''",
        "highlights": "ALTER TABLE scenic_spots ADD COLUMN highlights TEXT DEFAULT ''",
        "traffic_info": "ALTER TABLE scenic_spots ADD COLUMN traffic_info TEXT DEFAULT ''",
        "parking_info": "ALTER TABLE scenic_spots ADD COLUMN parking_info TEXT DEFAULT ''",
        "public_transport": "ALTER TABLE scenic_spots ADD COLUMN public_transport TEXT DEFAULT ''",
        "self_driving_route": "ALTER TABLE scenic_spots ADD COLUMN self_driving_route TEXT DEFAULT ''",
        "accessibility_tips": "ALTER TABLE scenic_spots ADD COLUMN accessibility_tips TEXT DEFAULT ''",
        "must_see_spots": "ALTER TABLE scenic_spots ADD COLUMN must_see_spots TEXT DEFAULT '[]'",
        "recommended_itinerary": "ALTER TABLE scenic_spots ADD COLUMN recommended_itinerary TEXT DEFAULT '[]'",
        "photo_spots": "ALTER TABLE scenic_spots ADD COLUMN photo_spots TEXT DEFAULT '[]'",
        "travel_tips": "ALTER TABLE scenic_spots ADD COLUMN travel_tips TEXT DEFAULT '[]'",
        "nearby_food": "ALTER TABLE scenic_spots ADD COLUMN nearby_food TEXT DEFAULT '[]'",
        "nearby_hotels": "ALTER TABLE scenic_spots ADD COLUMN nearby_hotels TEXT DEFAULT '[]'",
        "linked_scenic_recommendations": "ALTER TABLE scenic_spots ADD COLUMN linked_scenic_recommendations TEXT DEFAULT '[]'",
        "phone": "ALTER TABLE scenic_spots ADD COLUMN phone TEXT DEFAULT ''",
        "completeness_score": "ALTER TABLE scenic_spots ADD COLUMN completeness_score INTEGER DEFAULT 0",
    }.items():
        if name not in columns:
            db.execute(ddl)
    image_columns = {row["name"] for row in db.execute("PRAGMA table_info(scenic_images)").fetchall()}
    for name, ddl in {
        "thumbnail_url": "ALTER TABLE scenic_images ADD COLUMN thumbnail_url TEXT DEFAULT ''",
        "source_url": "ALTER TABLE scenic_images ADD COLUMN source_url TEXT DEFAULT ''",
        "license": "ALTER TABLE scenic_images ADD COLUMN license TEXT DEFAULT ''",
        "attribution": "ALTER TABLE scenic_images ADD COLUMN attribution TEXT DEFAULT ''",
        "provider": "ALTER TABLE scenic_images ADD COLUMN provider TEXT DEFAULT ''",
        "quality_score": "ALTER TABLE scenic_images ADD COLUMN quality_score INTEGER DEFAULT 0",
        "last_checked_at": "ALTER TABLE scenic_images ADD COLUMN last_checked_at TEXT",
    }.items():
        if name not in image_columns:
            db.execute(ddl)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS scenic_themes (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          slug TEXT UNIQUE NOT NULL,
          name TEXT UNIQUE NOT NULL,
          description TEXT DEFAULT '',
          guide TEXT DEFAULT '',
          image_url TEXT DEFAULT '',
          icon TEXT DEFAULT '',
          keywords_json TEXT DEFAULT '[]',
          season TEXT DEFAULT '',
          audience TEXT DEFAULT '',
          route_idea TEXT DEFAULT '',
          sort_order INTEGER DEFAULT 100,
          is_active INTEGER DEFAULT 1,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_scenic_themes_active ON scenic_themes(is_active, sort_order)")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS scenic_profile_candidates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          scenic_id INTEGER NOT NULL,
          candidate_type TEXT NOT NULL,
          title TEXT DEFAULT '',
          content TEXT NOT NULL,
          source_url TEXT NOT NULL,
          source_name TEXT DEFAULT '',
          source_type TEXT NOT NULL DEFAULT 'generated_draft',
          confidence INTEGER DEFAULT 0,
          risk_level TEXT DEFAULT 'medium',
          status TEXT DEFAULT 'pending',
          raw_payload_json TEXT DEFAULT '{}',
          diff_json TEXT DEFAULT '{}',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          reviewed_at TEXT,
          reviewed_by TEXT DEFAULT '',
          UNIQUE(scenic_id, candidate_type, source_url, content)
        );
        CREATE INDEX IF NOT EXISTS idx_scenic_profile_candidates_scenic_id ON scenic_profile_candidates(scenic_id);
        CREATE INDEX IF NOT EXISTS idx_scenic_profile_candidates_status ON scenic_profile_candidates(status);
        """
    )
    profile_columns = {row["name"] for row in db.execute("PRAGMA table_info(scenic_profile_candidates)").fetchall()}
    for name, ddl in {
        "title": "ALTER TABLE scenic_profile_candidates ADD COLUMN title TEXT DEFAULT ''",
        "source_name": "ALTER TABLE scenic_profile_candidates ADD COLUMN source_name TEXT DEFAULT ''",
        "source_type": "ALTER TABLE scenic_profile_candidates ADD COLUMN source_type TEXT NOT NULL DEFAULT 'generated_draft'",
        "confidence": "ALTER TABLE scenic_profile_candidates ADD COLUMN confidence INTEGER DEFAULT 0",
        "risk_level": "ALTER TABLE scenic_profile_candidates ADD COLUMN risk_level TEXT DEFAULT 'medium'",
        "status": "ALTER TABLE scenic_profile_candidates ADD COLUMN status TEXT DEFAULT 'pending'",
        "raw_payload_json": "ALTER TABLE scenic_profile_candidates ADD COLUMN raw_payload_json TEXT DEFAULT '{}'",
        "diff_json": "ALTER TABLE scenic_profile_candidates ADD COLUMN diff_json TEXT DEFAULT '{}'",
        "reviewed_at": "ALTER TABLE scenic_profile_candidates ADD COLUMN reviewed_at TEXT",
        "reviewed_by": "ALTER TABLE scenic_profile_candidates ADD COLUMN reviewed_by TEXT DEFAULT ''",
    }.items():
        if name not in profile_columns:
            db.execute(ddl)
    image_candidate_columns = {row["name"] for row in db.execute("PRAGMA table_info(scenic_image_candidates)").fetchall()}
    for name, ddl in {
        "source_type": "ALTER TABLE scenic_image_candidates ADD COLUMN source_type TEXT DEFAULT 'bing'",
        "license": "ALTER TABLE scenic_image_candidates ADD COLUMN license TEXT DEFAULT ''",
        "attribution": "ALTER TABLE scenic_image_candidates ADD COLUMN attribution TEXT DEFAULT ''",
        "provider": "ALTER TABLE scenic_image_candidates ADD COLUMN provider TEXT DEFAULT ''",
        "risk_level": "ALTER TABLE scenic_image_candidates ADD COLUMN risk_level TEXT DEFAULT 'medium'",
        "status": "ALTER TABLE scenic_image_candidates ADD COLUMN status TEXT DEFAULT 'pending'",
        "raw_payload_json": "ALTER TABLE scenic_image_candidates ADD COLUMN raw_payload_json TEXT DEFAULT '{}'",
        "quality_score": "ALTER TABLE scenic_image_candidates ADD COLUMN quality_score INTEGER DEFAULT 0",
        "availability_status": "ALTER TABLE scenic_image_candidates ADD COLUMN availability_status TEXT DEFAULT 'unchecked'",
        "failure_count": "ALTER TABLE scenic_image_candidates ADD COLUMN failure_count INTEGER DEFAULT 0",
        "last_checked_at": "ALTER TABLE scenic_image_candidates ADD COLUMN last_checked_at TEXT",
    }.items():
        if name not in image_candidate_columns:
            db.execute(ddl)
    db.execute(
        """
        UPDATE scenic_spots
        SET normalized_province=COALESCE(NULLIF(normalized_province,''), province),
            normalized_city=COALESCE(NULLIF(normalized_city,''), city),
            normalized_district=COALESCE(NULLIF(normalized_district,''), district)
        """
    )
    for statement in [
        "CREATE INDEX IF NOT EXISTS idx_scenic_province ON scenic_spots(province)",
        "CREATE INDEX IF NOT EXISTS idx_scenic_city ON scenic_spots(city)",
        "CREATE INDEX IF NOT EXISTS idx_scenic_district ON scenic_spots(district)",
        "CREATE INDEX IF NOT EXISTS idx_scenic_name ON scenic_spots(name)",
        "CREATE INDEX IF NOT EXISTS idx_scenic_level ON scenic_spots(level)",
        "CREATE INDEX IF NOT EXISTS idx_scenic_tags ON scenic_spots(tags)",
        "CREATE INDEX IF NOT EXISTS idx_scenic_normalized_province ON scenic_spots(normalized_province)",
        "CREATE INDEX IF NOT EXISTS idx_scenic_normalized_city ON scenic_spots(normalized_city)",
    ]:
        db.execute(statement)
    api_columns = {row["name"] for row in db.execute("PRAGMA table_info(api_configs)").fetchall()}
    for name, ddl in {
        "api_key_secret": "ALTER TABLE api_configs ADD COLUMN api_key_secret TEXT DEFAULT ''",
        "settings_json": "ALTER TABLE api_configs ADD COLUMN settings_json TEXT DEFAULT '{}'",
    }.items():
        if name not in api_columns:
            db.execute(ddl)
    user_columns = {row["name"] for row in db.execute("PRAGMA table_info(users)").fetchall()}
    if "password_hash" not in user_columns:
        db.execute("ALTER TABLE users ADD COLUMN password_hash TEXT DEFAULT ''")
    layout_columns = {row["name"] for row in db.execute("PRAGMA table_info(page_layouts)").fetchall()}
    for name, ddl in {
        "page_key": "ALTER TABLE page_layouts ADD COLUMN page_key TEXT",
        "name": "ALTER TABLE page_layouts ADD COLUMN name TEXT DEFAULT ''",
        "layout_json": "ALTER TABLE page_layouts ADD COLUMN layout_json TEXT",
        "status": "ALTER TABLE page_layouts ADD COLUMN status TEXT DEFAULT 'draft'",
        "version": "ALTER TABLE page_layouts ADD COLUMN version INTEGER DEFAULT 1",
        "is_active": "ALTER TABLE page_layouts ADD COLUMN is_active INTEGER DEFAULT 1",
        "created_by": "ALTER TABLE page_layouts ADD COLUMN created_by TEXT DEFAULT 'system'",
        "published_by": "ALTER TABLE page_layouts ADD COLUMN published_by TEXT DEFAULT ''",
        "published_at": "ALTER TABLE page_layouts ADD COLUMN published_at TEXT",
        "created_at": "ALTER TABLE page_layouts ADD COLUMN created_at TEXT",
    }.items():
        if name not in layout_columns:
            db.execute(ddl)
    db.execute("UPDATE page_layouts SET page_key=scope WHERE page_key IS NULL OR page_key=''")
    db.execute("UPDATE page_layouts SET layout_json=layout WHERE layout_json IS NULL OR layout_json=''")
    db.execute("CREATE INDEX IF NOT EXISTS idx_page_layouts_page_key ON page_layouts(page_key)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_page_layouts_status ON page_layouts(status)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_page_layouts_active ON page_layouts(is_active)")
    tpt_columns = {row["name"] for row in db.execute("PRAGMA table_info(tpt_jingdian)").fetchall()}
    if "search_text" not in tpt_columns:
        db.execute("ALTER TABLE tpt_jingdian ADD COLUMN search_text TEXT DEFAULT ''")
    for name, ddl in {
        "province": "ALTER TABLE tpt_jingdian ADD COLUMN province TEXT DEFAULT ''",
        "city": "ALTER TABLE tpt_jingdian ADD COLUMN city TEXT DEFAULT ''",
        "district": "ALTER TABLE tpt_jingdian ADD COLUMN district TEXT DEFAULT ''",
    }.items():
        if name not in tpt_columns:
            db.execute(ddl)
    _backfill_tpt_region_labels(db)
    _backfill_imported_scenic_region_labels(db)
    _sync_regions_from_destination_data(db)
    for statement in [
        "CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_province ON tpt_jingdian(province)",
        "CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_city ON tpt_jingdian(city)",
        "CREATE INDEX IF NOT EXISTS idx_tpt_jingdian_district ON tpt_jingdian(district)",
    ]:
        db.execute(statement)
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS component_templates (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          name TEXT NOT NULL,
          type TEXT NOT NULL,
          category TEXT NOT NULL,
          config_json TEXT NOT NULL DEFAULT '{}',
          preview_image TEXT DEFAULT '',
          created_by TEXT DEFAULT 'admin',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(name, type, category)
        )
        """
    )
    db.execute("CREATE INDEX IF NOT EXISTS idx_component_templates_type ON component_templates(type)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_component_templates_category ON component_templates(category)")
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS weather_cache (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          city TEXT NOT NULL,
          provider TEXT DEFAULT '',
          weather_json TEXT DEFAULT '{}',
          forecast_json TEXT DEFAULT '[]',
          live_json TEXT DEFAULT '[]',
          source TEXT DEFAULT 'fallback',
          expires_at TEXT,
          created_at TEXT DEFAULT CURRENT_TIMESTAMP,
          updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(city, provider)
        );
        CREATE TABLE IF NOT EXISTS map_request_logs (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          provider TEXT NOT NULL,
          request_type TEXT NOT NULL,
          request_params TEXT DEFAULT '{}',
          status TEXT DEFAULT '',
          response_ms INTEGER DEFAULT 0,
          message TEXT DEFAULT '',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS scenic_import_tasks (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          file_path TEXT NOT NULL,
          status TEXT DEFAULT 'pending',
          total_rows INTEGER DEFAULT 0,
          imported_rows INTEGER DEFAULT 0,
          duplicate_rows INTEGER DEFAULT 0,
          failed_rows INTEGER DEFAULT 0,
          current_offset INTEGER DEFAULT 0,
          batch_size INTEGER DEFAULT 1000,
          province_filter TEXT DEFAULT '',
          started_at TEXT DEFAULT CURRENT_TIMESTAMP,
          finished_at TEXT,
          message TEXT DEFAULT '',
          created_by TEXT DEFAULT 'admin'
        );
        CREATE TABLE IF NOT EXISTS scenic_import_errors (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          task_id INTEGER,
          row_number INTEGER,
          raw_text TEXT DEFAULT '',
          error_message TEXT DEFAULT '',
          created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_weather_cache_city ON weather_cache(city, provider);
        CREATE INDEX IF NOT EXISTS idx_map_request_logs_created_at ON map_request_logs(created_at);
        CREATE INDEX IF NOT EXISTS idx_scenic_import_tasks_status ON scenic_import_tasks(status);
        CREATE INDEX IF NOT EXISTS idx_scenic_import_errors_task_id ON scenic_import_errors(task_id);
        """
    )
