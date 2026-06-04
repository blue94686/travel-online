#!/usr/bin/env python3
import argparse
import csv
import html
import json
import math
import re
import shutil
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


DEFAULT_SQL = ROOT / "tpt_data_jingdian.sql"
DEFAULT_MIRROR_SQL = ROOT / "backend" / "app" / "data" / "tpt_data_jingdian.sql"
DEFAULT_REPORT = ROOT / "docs" / "tpt_data_jingdian_web_update_report.json"
DEFAULT_BACKUP_DIR = ROOT / "backend" / "app" / "data" / "backups"
DEFAULT_CACHE_DIR = ROOT / "tmp" / "web_scenic_cache"

KCLOUD_SCENIC_URL = "https://services.kcloudtech.cn/api/geo/scenicspots"
KCLOUD_PROVINCE_CITIES_URL = "https://services.kcloudtech.cn/api/geo/province/{province_id}/cities"
KCLOUD_CITY_SCENIC_URL = "https://services.kcloudtech.cn/api/geo/city/{city_id}/scenicspots?aLevel={level}"
KCLOUD_PAGE_URL = "https://services.kcloudtech.cn/geo/scenicspots"
MCT_5A_QUERY_URL = "https://zwfw.mct.gov.cn/wycx/5ajlyjq/"
SUCHAJUN_5A_URL = "https://www.suchajun.com/lvyou/wuajingqu"

BASE_COLUMNS = (
    "id",
    "title",
    "tel",
    "add",
    "type",
    "areaid",
    "poiid",
    "gcjx",
    "gcjy",
    "gpsx",
    "gpsy",
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

ALL_COLUMNS = BASE_COLUMNS + ENHANCED_COLUMNS + WEB_COLUMNS
INSERT_PREFIX = "INSERT INTO `tpt_data_jingdian` VALUES ("

SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\s·•,，.。;；:：、'\"“”‘’\-—_/\\]+")
PAREN_RE = re.compile(r"[（(].*?[）)]")
HTML_TAG_RE = re.compile(r"<[^>]+>")
TR_RE = re.compile(r"<tr[\s\S]*?</tr>", re.I)
TD_RE = re.compile(r"<td[\s\S]*?</td>", re.I)
SCENIC_SUFFIX_RE = re.compile(
    r"(国家级旅游景区|国家旅游度假区|旅游度假区|风景名胜区|风景区|旅游景区|旅游区|景区|国家森林公园|森林公园|国家湿地公园|湿地公园)$"
)

THEME_RULES = {
    "hiking": ("徒步", re.compile(r"(徒步|登山|步道|栈道|爬山|山脊|山|峰|岭|峡|谷|森林|长城|古道|草原)", re.I)),
    "photo": ("摄影", re.compile(r"(摄影|打卡|观景|日出|日落|云海|花海|梯田|玻璃|天空|地标|观景台|观景点|古城|古镇)")),
    "heritage": ("历史文化", re.compile(r"(古|遗址|故居|纪念|博物馆|寺|庙|观|宫|殿|塔|陵|祠|书院|城墙|古城|石窟|文化|世界遗产)")),
    "nature": ("自然风光", re.compile(r"(山水|湖|河|江|海|岛|湾|森林|湿地|瀑|峡|谷|草原|地质|风景区|公园|雪山)")),
}


@dataclass(frozen=True)
class WebScenic:
    name: str
    a_level: str
    province: str = ""
    city: str = ""
    district: str = ""
    address: str = ""
    longitude: str = ""
    latitude: str = ""
    description: str = ""
    source_name: str = ""
    source_url: str = ""
    source_confidence: str = "medium"
    a_level_year: str = ""


def parse_args():
    parser = argparse.ArgumentParser(description="Update tpt_data_jingdian.sql with current 4A/5A scenic metadata from web sources.")
    parser.add_argument("--input", type=Path, default=DEFAULT_SQL)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--mirror", type=Path, default=DEFAULT_MIRROR_SQL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--include-4a", action="store_true", help="Fetch city-level 4A records from the public KCloud API.")
    parser.add_argument("--max-4a-cities", type=int, default=0, help="Limit 4A city requests for a small dry run.")
    parser.add_argument("--append-missing", action="store_true", help="Append unmatched 4A/5A records as new SQL rows.")
    parser.add_argument("--skip-suchajun", action="store_true")
    parser.add_argument("--skip-network", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def clean_text(value):
    return SPACE_RE.sub(" ", str(value or "").strip())


def normalize(value):
    return PUNCT_RE.sub("", clean_text(value).lower())


def normalize_title(value):
    text = PAREN_RE.sub("", clean_text(value))
    text = normalize(text)
    previous = None
    while previous != text:
        previous = text
        text = SCENIC_SUFFIX_RE.sub("", text)
    return text


def parse_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_insert_values(line):
    line = line.strip()
    if not line.startswith(INSERT_PREFIX):
        return None
    if line.endswith(";"):
        line = line[:-1]
    body = line[len(INSERT_PREFIX):]
    if body.endswith(")"):
        body = body[:-1]
    try:
        return next(csv.reader([body], quotechar="'", escapechar="\\", skipinitialspace=True))
    except csv.Error:
        return None


def read_rows(path):
    rows = []
    parse_errors = []
    with Path(path).open("r", encoding="utf-8", newline="", errors="ignore") as stream:
        for line_no, line in enumerate(stream, start=1):
            values = parse_insert_values(line)
            if not values:
                continue
            if len(values) < len(BASE_COLUMNS):
                parse_errors.append({"line": line_no, "error": f"expected at least 11 values, got {len(values)}"})
                continue
            padded = values[:len(ALL_COLUMNS)] + [""] * max(0, len(ALL_COLUMNS) - len(values))
            row = dict(zip(ALL_COLUMNS, padded))
            try:
                row["id"] = int(row["id"])
            except (TypeError, ValueError):
                parse_errors.append({"line": line_no, "error": f"invalid id {row.get('id')}"})
                continue
            for key in ALL_COLUMNS:
                if key != "id":
                    row[key] = clean_text(row.get(key, ""))
            rows.append(row)
    return rows, parse_errors


def cached_text(url, cache_dir, cache_name, skip_network=False, ttl_seconds=604800):
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / cache_name
    if cache_path.exists():
        age = time.time() - cache_path.stat().st_mtime
        if skip_network or age <= ttl_seconds:
            return cache_path.read_text(encoding="utf-8", errors="ignore")
    if skip_network:
        return ""
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 Codex scenic data updater"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="ignore")
    except Exception:
        if cache_path.exists():
            return cache_path.read_text(encoding="utf-8", errors="ignore")
        raise
    cache_path.write_text(body, encoding="utf-8")
    return body


def cached_json(url, cache_dir, cache_name, skip_network=False):
    body = cached_text(url, cache_dir, cache_name, skip_network=skip_network)
    if not body:
        return None
    return json.loads(body)


def scenic_from_kcloud(provinces):
    records = []
    for province in provinces or []:
        province_name = clean_text(province.get("name"))
        for spot in province.get("scenicSpots") or []:
            records.append(kcloud_spot_to_record(spot, province_name))
    return records


def kcloud_spot_to_record(spot, province_name):
    city = clean_text(spot.get("cityName"))
    district = clean_text(spot.get("districtName"))
    address = "".join(part for part in (province_name, city, district) if part)
    return WebScenic(
        name=clean_text(spot.get("name")),
        a_level=clean_text(spot.get("aLevel")).upper(),
        province=province_name,
        city=city,
        district=district,
        address=address,
        longitude=clean_text(spot.get("longitude")),
        latitude=clean_text(spot.get("latitude")),
        description=clean_text(spot.get("description")),
        source_name="KCloud全国5A/4A级景区地图",
        source_url=KCLOUD_PAGE_URL,
        source_confidence="high_auxiliary",
    )


def fetch_kcloud_records(cache_dir, include_4a=False, max_4a_cities=0, skip_network=False):
    provinces = cached_json(KCLOUD_SCENIC_URL, cache_dir, "kcloud_scenicspots.json", skip_network=skip_network) or []
    records = scenic_from_kcloud(provinces)
    city_requests = 0
    if not include_4a:
        return records, {"kcloud_provinces": len(provinces), "kcloud_4a_city_requests": city_requests}

    for province in provinces:
        province_id = province.get("id")
        if not province_id:
            continue
        cities_url = KCLOUD_PROVINCE_CITIES_URL.format(province_id=province_id)
        cities = cached_json(cities_url, cache_dir, f"kcloud_province_{province_id}_cities.json", skip_network=skip_network) or []
        for city in cities:
            if max_4a_cities and city_requests >= max_4a_cities:
                return records, {"kcloud_provinces": len(provinces), "kcloud_4a_city_requests": city_requests}
            city_id = city.get("id")
            if not city_id:
                continue
            city_requests += 1
            spots_url = KCLOUD_CITY_SCENIC_URL.format(city_id=city_id, level="4A")
            spots = cached_json(spots_url, cache_dir, f"kcloud_city_{city_id}_4a.json", skip_network=skip_network) or []
            for spot in spots:
                records.append(kcloud_spot_to_record(spot, clean_text(province.get("name"))))
    return records, {"kcloud_provinces": len(provinces), "kcloud_4a_city_requests": city_requests}


def parse_suchajun_5a_table(html_text):
    records = []
    for row in TR_RE.findall(html_text or ""):
        cells = []
        for cell in TD_RE.findall(row):
            text = html.unescape(HTML_TAG_RE.sub("", cell))
            cells.append(clean_text(text))
        if len(cells) < 4 or not cells[1]:
            continue
        records.append(WebScenic(
            name=cells[1],
            a_level="5A",
            province=cells[2],
            source_name="速查君5A景区名单",
            source_url=SUCHAJUN_5A_URL,
            source_confidence="medium_auxiliary",
            a_level_year=cells[3],
        ))
    return records


def fetch_suchajun_records(cache_dir, skip_network=False):
    records = []
    for page in range(1, 19):
        url = f"{SUCHAJUN_5A_URL}?page={page}"
        try:
            body = cached_text(url, cache_dir, f"suchajun_5a_page_{page}.html", skip_network=skip_network)
        except Exception:
            break
        page_records = parse_suchajun_5a_table(body)
        if not page_records:
            break
        records.extend(page_records)
    return records


def source_rank(record):
    level_bonus = 20 if record.a_level == "5A" else 0
    if record.source_confidence.startswith("official"):
        return 100 + level_bonus
    if record.source_confidence.startswith("high"):
        return 80 + level_bonus
    if record.source_confidence.startswith("medium"):
        return 60 + level_bonus
    return 40 + level_bonus


def dedupe_records(records):
    best = {}
    for record in records:
        if not record.name or record.a_level not in {"5A", "4A"}:
            continue
        key = (normalize_title(record.name), normalize(record.province))
        current = best.get(key)
        if not current or source_rank(record) > source_rank(current):
            best[key] = record
        elif current and not current.a_level_year and record.a_level_year:
            best[key] = WebScenic(**(asdict(current) | {"a_level_year": record.a_level_year}))
    return list(best.values())


def province_variants(row):
    values = [row.get("province"), row.get("web_province")]
    area = clean_text(row.get("add"))
    for value in values:
        if value:
            yield normalize(value)
    if area:
        yield normalize(area[:3])


def row_keys(row):
    title = row.get("title") or ""
    names = {normalize_title(title), normalize(title)}
    for suffix in ("景区", "风景区", "旅游区", "风景名胜区"):
        if not title.endswith(suffix):
            names.add(normalize_title(title + suffix))
    provinces = set(province_variants(row)) or {""}
    for province in provinces:
        for name in names:
            if name:
                yield (province, name)


def record_keys(record):
    names = {normalize_title(record.name), normalize(record.name)}
    provinces = {normalize(record.province), ""}
    for province in provinces:
        for name in names:
            if name:
                yield (province, name)


def haversine_km(lon1, lat1, lon2, lat2):
    lon1 = parse_float(lon1)
    lat1 = parse_float(lat1)
    lon2 = parse_float(lon2)
    lat2 = parse_float(lat2)
    if None in (lon1, lat1, lon2, lat2):
        return None
    radius = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def titles_related(left, right):
    left_key = normalize_title(left)
    right_key = normalize_title(right)
    if not left_key or not right_key:
        return False
    if left_key == right_key:
        return True
    shorter, longer = sorted((left_key, right_key), key=len)
    return len(shorter) >= 3 and shorter in longer


def build_row_index(rows):
    index = defaultdict(list)
    coordinate_grid = defaultdict(list)
    for idx, row in enumerate(rows):
        for key in row_keys(row):
            index[key].append(idx)
        lon = row.get("gpsx") or row.get("web_longitude")
        lat = row.get("gpsy") or row.get("web_latitude")
        lon_value = parse_float(lon)
        lat_value = parse_float(lat)
        if lon_value is not None and lat_value is not None:
            province_keys = {normalize(row.get("province")), ""}
            for province in province_keys:
                cell = (province, int(lon_value * 10), int(lat_value * 10))
                coordinate_grid[cell].append((idx, lon, lat))
    return index, coordinate_grid


def find_row(record, rows, index, coordinate_grid, claimed_rows=None):
    claimed_rows = claimed_rows or {}
    for key in record_keys(record):
        for idx in index.get(key, []):
            row = rows[idx]
            if record.province and row.get("province") and normalize(record.province) != normalize(row.get("province")):
                continue
            claimed = claimed_rows.get(idx)
            if claimed and claimed != normalize_title(record.name):
                continue
            return idx, "name_region"
    record_lon = parse_float(record.longitude)
    record_lat = parse_float(record.latitude)
    if record_lon is not None and record_lat is not None:
        province_keys = [normalize(record.province), ""]
        checked = set()
        base_x = int(record_lon * 10)
        base_y = int(record_lat * 10)
        for province in province_keys:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for idx, lon, lat in coordinate_grid.get((province, base_x + dx, base_y + dy), []):
                        if idx in checked:
                            continue
                        checked.add(idx)
                        row = rows[idx]
                        if not titles_related(row.get("title"), record.name):
                            continue
                        claimed = claimed_rows.get(idx)
                        if claimed and claimed != normalize_title(record.name):
                            continue
                        distance = haversine_km(record_lon, record_lat, lon, lat)
                        if distance is not None and distance <= 5:
                            if record.province and row.get("province") and normalize(record.province) != normalize(row.get("province")):
                                continue
                            return idx, "coordinate_5km"
    return None, ""


def split_values(value):
    return [part.strip() for part in re.split(r"[,，;；|/、]+", value or "") if part.strip()]


def append_unique(existing, additions):
    values = split_values(existing)
    for value in additions:
        value = clean_text(value)
        if value and value not in values:
            values.append(value)
    return ",".join(values)


def record_theme_additions(record):
    text = " ".join([record.name, record.description, record.address, record.city, record.district])
    slugs = []
    names = []
    for slug, (name, regex) in THEME_RULES.items():
        if regex.search(text):
            slugs.append(slug)
            names.append(name)
    return slugs, names


def update_row_with_record(row, record, match_reason):
    before_level = row.get("official_level") or ""
    row["official_level"] = record.a_level
    row["level_source"] = record.source_name
    row["level_source_url"] = record.source_url
    row["level_verified_at"] = datetime.now().date().isoformat()
    row["a_level_year"] = record.a_level_year or row.get("a_level_year", "")
    row["web_province"] = record.province or row.get("web_province", "")
    row["web_city"] = record.city or row.get("web_city", "")
    row["web_district"] = record.district or row.get("web_district", "")
    row["web_address"] = record.address or row.get("web_address", "")
    row["web_longitude"] = record.longitude or row.get("web_longitude", "")
    row["web_latitude"] = record.latitude or row.get("web_latitude", "")
    row["web_source_confidence"] = record.source_confidence
    row["web_update_note"] = f"{record.a_level}等级来源已按{match_reason}匹配；官方查询入口：{MCT_5A_QUERY_URL}"
    row["tags"] = append_unique(row.get("tags"), [f"{record.a_level}景区", "国家A级景区"])
    slugs, names = record_theme_additions(record)
    row["theme_slugs"] = append_unique(row.get("theme_slugs"), slugs)
    row["theme_names"] = append_unique(row.get("theme_names"), names)
    row["tags"] = append_unique(row.get("tags"), names)
    if record.address and (not row.get("add") or "待补充" in row.get("add")):
        row["add"] = record.address
    if record.description and len(record.description) > len(row.get("description", "")):
        row["description"] = record.description
    if record.a_level == "5A":
        try:
            row["quality_score"] = str(max(int(float(row.get("quality_score") or 0)), 96))
        except ValueError:
            row["quality_score"] = "96"
    elif record.a_level == "4A":
        try:
            row["quality_score"] = str(max(int(float(row.get("quality_score") or 0)), 88))
        except ValueError:
            row["quality_score"] = "88"
    if before_level != record.a_level:
        row["updated_at"] = datetime.now().isoformat(timespec="seconds")
    row["data_version"] = "2026-web-a-level-v1"
    return row


def make_row_from_record(record, next_id):
    now = datetime.now().isoformat(timespec="seconds")
    slugs, names = record_theme_additions(record)
    row = {column: "" for column in ALL_COLUMNS}
    row.update({
        "id": next_id,
        "title": record.name,
        "add": record.address or "".join(part for part in (record.province, record.city, record.district) if part),
        "type": f"风景名胜;国家A级景区;{record.a_level}景区",
        "gpsx": record.longitude,
        "gpsy": record.latitude,
        "province": record.province,
        "city": record.city,
        "district": record.district,
        "main_category": f"{record.a_level}景区",
        "theme_slugs": ",".join(slugs or ["nature"]),
        "theme_names": ",".join(names or ["自然风光"]),
        "tags": ",".join([f"{record.a_level}景区", "国家A级景区", *(names or [])]),
        "summary": f"{record.name}是{record.province}{record.city}{record.district}的{record.a_level}旅游景区。",
        "description": record.description or f"{record.name}为公开网页收录的{record.a_level}旅游景区，地址和开放信息出行前应以景区及文旅部门公示为准。",
        "best_season": "四季皆宜",
        "audience": "普通游客",
        "recommended_duration": "2-6小时",
        "route_idea": "景区入口 - 核心游览点 - 周边观景点",
        "quality_score": "96" if record.a_level == "5A" else "88",
        "data_version": "2026-web-a-level-v1",
        "updated_at": now,
    })
    return update_row_with_record(row, record, "web_append")


def merge_web_records(rows, records, append_missing=False):
    index, coordinates = build_row_index(rows)
    claimed_rows = {}
    matched = []
    unmatched = []
    match_counts = Counter()
    next_id = max((int(row["id"]) for row in rows), default=0) + 1
    for record in dedupe_records(records):
        idx, match_reason = find_row(record, rows, index, coordinates, claimed_rows=claimed_rows)
        if idx is None:
            if append_missing:
                row = make_row_from_record(record, next_id)
                next_id += 1
                rows.append(row)
                new_idx = len(rows) - 1
                for key in row_keys(row):
                    index[key].append(new_idx)
                claimed_rows[new_idx] = normalize_title(record.name)
                matched.append({"record": record.name, "level": record.a_level, "row_id": row["id"], "reason": "appended"})
                match_counts["appended"] += 1
            else:
                unmatched.append(record)
            continue
        rows[idx] = update_row_with_record(rows[idx], record, match_reason)
        claimed_rows[idx] = normalize_title(record.name)
        matched.append({"record": record.name, "level": record.a_level, "row_id": rows[idx]["id"], "reason": match_reason})
        match_counts[match_reason] += 1
    return {
        "rows": rows,
        "matched": matched,
        "unmatched": unmatched,
        "match_counts": dict(match_counts),
    }


def sql_quote(value):
    return "'" + str(value or "").replace("\\", "\\\\").replace("'", "\\'") + "'"


def row_to_insert(row):
    return f"INSERT INTO `tpt_data_jingdian` VALUES ({', '.join(sql_quote(row.get(column, '')) for column in ALL_COLUMNS)});\n"


def write_sql(path, rows):
    max_id = max((int(row["id"]) for row in rows), default=0)
    header = f"""SET FOREIGN_KEY_CHECKS=0;

-- Updated by scripts/update_tpt_scenic_from_web.py at {datetime.now().isoformat(timespec='seconds')}
-- Rows kept: {len(rows)}
-- Data version: 2026-web-a-level-v1
-- Source priority: official query entry first, public pages/API as auxiliary data.

DROP TABLE IF EXISTS `tpt_data_jingdian`;
CREATE TABLE `tpt_data_jingdian` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `title` varchar(120) DEFAULT NULL,
  `tel` varchar(100) DEFAULT NULL,
  `add` varchar(220) DEFAULT NULL,
  `type` varchar(280) DEFAULT NULL,
  `areaid` varchar(7) DEFAULT NULL,
  `poiid` varchar(20) DEFAULT NULL,
  `gcjx` varchar(20) DEFAULT NULL,
  `gcjy` varchar(20) DEFAULT NULL,
  `gpsx` double DEFAULT NULL,
  `gpsy` double DEFAULT NULL,
  `province` varchar(40) DEFAULT NULL,
  `city` varchar(60) DEFAULT NULL,
  `district` varchar(60) DEFAULT NULL,
  `main_category` varchar(80) DEFAULT NULL,
  `theme_slugs` varchar(240) DEFAULT NULL,
  `theme_names` varchar(240) DEFAULT NULL,
  `tags` varchar(500) DEFAULT NULL,
  `summary` varchar(500) DEFAULT NULL,
  `description` text,
  `best_season` varchar(120) DEFAULT NULL,
  `audience` varchar(220) DEFAULT NULL,
  `recommended_duration` varchar(80) DEFAULT NULL,
  `route_idea` varchar(255) DEFAULT NULL,
  `quality_score` int(11) DEFAULT 0,
  `data_version` varchar(40) DEFAULT NULL,
  `updated_at` varchar(30) DEFAULT NULL,
  `official_level` varchar(10) DEFAULT NULL,
  `level_source` varchar(120) DEFAULT NULL,
  `level_source_url` varchar(255) DEFAULT NULL,
  `level_verified_at` varchar(30) DEFAULT NULL,
  `a_level_year` varchar(20) DEFAULT NULL,
  `web_province` varchar(40) DEFAULT NULL,
  `web_city` varchar(60) DEFAULT NULL,
  `web_district` varchar(60) DEFAULT NULL,
  `web_address` varchar(220) DEFAULT NULL,
  `web_longitude` varchar(20) DEFAULT NULL,
  `web_latitude` varchar(20) DEFAULT NULL,
  `web_source_confidence` varchar(40) DEFAULT NULL,
  `web_update_note` varchar(500) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_areaid` (`areaid`),
  KEY `idx_poiid` (`poiid`),
  KEY `idx_region` (`province`,`city`,`district`),
  KEY `idx_main_category` (`main_category`),
  KEY `idx_theme_slugs` (`theme_slugs`),
  KEY `idx_official_level` (`official_level`),
  KEY `idx_quality_score` (`quality_score`)
) ENGINE=InnoDB AUTO_INCREMENT={max_id + 1} DEFAULT CHARSET=utf8mb4;

"""
    with Path(path).open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header)
        for row in rows:
            handle.write(row_to_insert(row))


def backup(path, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{path.stem}-before-web-update-{stamp}{path.suffix}"
    shutil.copy2(path, target)
    return target


def collect_records(args):
    records = []
    source_stats = {}
    kcloud_records, kcloud_stats = fetch_kcloud_records(
        args.cache_dir,
        include_4a=args.include_4a,
        max_4a_cities=args.max_4a_cities,
        skip_network=args.skip_network,
    )
    records.extend(kcloud_records)
    source_stats.update(kcloud_stats)
    if not args.skip_suchajun:
        suchajun_records = fetch_suchajun_records(args.cache_dir, skip_network=args.skip_network)
        records.extend(suchajun_records)
        source_stats["suchajun_5a_records"] = len(suchajun_records)
    return records, source_stats


def main():
    args = parse_args()
    output_path = args.output or args.input
    rows, parse_errors = read_rows(args.input)
    records, source_stats = collect_records(args)
    deduped = dedupe_records(records)
    merge_result = merge_web_records(rows, deduped, append_missing=args.append_missing)
    rows = merge_result["rows"]
    level_counts = Counter(record.a_level for record in deduped)
    confidence_counts = Counter(record.source_confidence for record in deduped)
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "input": str(args.input),
        "output": str(output_path),
        "officialReferenceUrls": [MCT_5A_QUERY_URL],
        "auxiliarySourceUrls": [KCLOUD_PAGE_URL, SUCHAJUN_5A_URL],
        "originalRows": len(rows) - merge_result["match_counts"].get("appended", 0),
        "finalRows": len(rows),
        "webRecordsFetched": len(records),
        "webRecordsDeduped": len(deduped),
        "webRecordsByLevel": dict(level_counts),
        "webRecordsByConfidence": dict(confidence_counts),
        "sourceStats": source_stats,
        "matchCounts": merge_result["match_counts"],
        "matchedSamples": merge_result["matched"][:50],
        "unmatchedCount": len(merge_result["unmatched"]),
        "unmatchedSamples": [asdict(record) for record in merge_result["unmatched"][:80]],
        "parseErrors": parse_errors[:20],
        "schema": list(ALL_COLUMNS),
        "dryRun": args.dry_run,
        "appendMissing": args.append_missing,
    }
    if not args.dry_run:
        if output_path.exists():
            report["rootSqlBackup"] = str(backup(output_path, args.backup_dir))
        write_sql(output_path, rows)
        if args.mirror:
            args.mirror.parent.mkdir(parents=True, exist_ok=True)
            if args.mirror.exists():
                report["mirrorSqlBackup"] = str(backup(args.mirror, args.backup_dir))
            write_sql(args.mirror, rows)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "originalRows": report["originalRows"],
        "finalRows": report["finalRows"],
        "webRecordsFetched": len(records),
        "webRecordsDeduped": len(deduped),
        "webRecordsByLevel": dict(level_counts),
        "sourceStats": source_stats,
        "matchCounts": merge_result["match_counts"],
        "unmatchedCount": len(merge_result["unmatched"]),
        "report": str(args.report),
        "dryRun": args.dry_run,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
