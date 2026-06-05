#!/usr/bin/env python3
import argparse
import ast
import json
import re
import shutil
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SQL = ROOT / "tpt_data_jingdian.sql"
DEFAULT_MIRROR_SQL = ROOT / "backend" / "app" / "data" / "tpt_data_jingdian.sql"
DEFAULT_DB = ROOT / "backend" / "app" / "data" / "scenic_online.sqlite3"
DEFAULT_REPORT = ROOT / "docs" / "tpt_data_jingdian_clean_report.json"
DEFAULT_KEEP_IDS = ROOT / "docs" / "tpt_data_jingdian_keep_ids.json"
DEFAULT_BACKUP_DIR = ROOT / "backend" / "app" / "data" / "backups"

INSERT_RE = re.compile(r"INSERT INTO `tpt_data_jingdian` VALUES \((.*)\);")
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
ALL_COLUMNS = BASE_COLUMNS + ENHANCED_COLUMNS + WEB_COLUMNS + MEDIA_COLUMNS
SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\s·•,，.。;；:：、'\"“”‘’\-—_/\\]+")
PAREN_RE = re.compile(r"[（(].*?[）)]")
FALLBACK_REGION_RE = re.compile(r"^(\d+)(省级区域|地区|区县)$")
DIRECT_REGION_BY_PREFIX = {
    "11": "北京市",
    "12": "天津市",
    "31": "上海市",
    "50": "重庆市",
    "81": "香港特别行政区",
    "82": "澳门特别行政区",
}
ACCESSORY_TITLE_RE = re.compile(
    r"[（(][^）)]*(?:入口|出口|出入口|停车场|售票处|售票点|检票口|游客中心|服务中心|管理处|卫生间|洗手间)[^）)]*[）)]"
    r"|"
    r"[（(](?:东|西|南|北|东北|西北|东南|西南|正|侧)?(?:[一二三四五六七八九十0-9]*门|入口|出口|出入口|停车场|售票处|售票点|检票口|游客中心|服务中心|管理处|卫生间|洗手间)[）)]"
    r"|(?:东|西|南|北|东北|西北|东南|西南|正)?(?:[一二三四五六七八九十0-9]*门|入口|出口|出入口)$"
)
ACCESSORY_WORD_RE = re.compile(
    r"(停车场|售票处|售票点|检票口|游客中心|服务中心|管理处|管理办公室|卫生间|洗手间|公园内部设施|集散中心|换乘中心|接驳中心)"
)
SCENIC_TYPE_RE = re.compile(r"(风景名胜|公园广场|博物馆|展览馆|度假村|自然地物|旅游景点|世界遗产|国家级景点|省级景点)")
HARD_NON_SCENIC_CATEGORY_RE = re.compile(r"(?:^|;)(?:中餐厅|住宅小区|热点地名|购物中心|普通地名)(?:$|;)")
STRONG_SCENIC_CATEGORY_RE = re.compile(
    r"(?:^|;)(?:世界遗产|国家级景点|省级景点|寺庙道观|博物馆|纪念馆|度假村|动物园|植物园|水族馆|森林公园|湿地公园)(?:$|;)"
)
LOW_VALUE_TITLE_RE = re.compile(
    r"(?:"
    r"提示牌|告示牌|投诉处|管理委员会|委员会|办公室|售楼处|接待处|咨询处|服务处|收费处"
    r"|游览电瓶车|电瓶车|观光车|摆渡车|小火车|游船售票|售票亭|游客须知|讲解服务"
    r"|健身乐园|健身广场|文体广场|文化广场|社区广场|社区文化|人口文化园|活动广场"
    r"|培训中心|会议中心|职工之家|老年活动|棋牌|茶楼|招待所|餐厅|饭店|农家乐"
    r"|旅游购物点|购物点|投诉点|个私分会|游船码头|观光码头|景区码头"
    r"|房地产|住宅|小区|公寓|售楼|商业街区"
    r")"
)
KNOWN_CORE_PREFIXES = (
    "故宫博物院",
    "杭州西湖",
    "黄山风景区",
    "九寨沟风景名胜区",
    "张家界国家森林公园",
    "桂林漓江风景区",
    "千岛湖风景区",
    "八达岭长城",
    "颐和园",
    "天坛公园",
)
LANDMARK_SQUARE_RE = re.compile(
    r"(天安门广场|五四广场|星海广场|泉城广场|朝天门广场|人民广场|市民广场|奥林匹克公园|大雁塔北广场|音乐广场)"
)
SUB_POI_SUFFIX_RE = re.compile(
    r"^(?:"
    r".{1,8}(?:馆|池|苑|居|亭|堂|殿|阁|楼|桥|碑|塔|洞|厅|院|轩|廊|榭|坊|台|馆内|园内)"
    r"|.{1,8}(?:动物区|混养区|展区|赏花区|赏荷区|钓鱼区|土脾区|核心区|游览区|片区)"
    r"|(?:东|西|南|北|东北|西北|东南|西南)?(?:园区|展区|片区|核心区|游览区)"
    r"|(?:东|西|南|北|东北|西北|东南|西南)区"
    r"|(?:小动物|猛兽|海兽|热带鱼|鸟|鸟类|非洲动物|美洲动物|灵长类).{0,6}"
    r")$"
)
KEEP_SUB_POI_SUFFIX_RE = re.compile(r"^(?:博物馆|纪念馆|美术馆|科技馆|文化馆|图书馆|艺术馆)$")
OFFICIAL_SCENIC_SUFFIX_RE = re.compile(r"^(?:风景区|景区|旅游区|度假区|森林公园|湿地公园|国家公园|地质公园)$")
THEME_RULES = (
    ("heritage", "人文古迹", re.compile(r"(古|遗址|故居|纪念|博物馆|寺|庙|观|宫|殿|塔|陵|祠|书院|城墙|古城|石窟|文化|世界遗产)")),
    ("hiking", "徒步登山", re.compile(r"(徒步|登山|步道|栈道|爬山|山脊|山|峰|岭|峡|谷|森林|长城|古道|草原)")),
    ("photo", "摄影打卡", re.compile(r"(摄影|打卡|观景|日出|日落|云海|花海|梯田|玻璃|天空|地标|观景台|观景点|古城|古镇)")),
    ("family", "亲子乐园", re.compile(r"(亲子|儿童|乐园|动物园|植物园|水族馆|海洋馆|游乐|公园)")),
    ("summer", "避暑胜地", re.compile(r"(避暑|森林|湿地|峡|谷|瀑|湖|漂流|草原|雪山)")),
    ("nature", "自然风光", re.compile(r"(山水|湖|河|江|海|岛|湾|森林|湿地|瀑|峡|谷|草原|地质|风景区|公园|雪山)")),
)


def parse_args():
    parser = argparse.ArgumentParser(description="Clean and deduplicate tpt_data_jingdian.sql.")
    parser.add_argument("--input", type=Path, default=DEFAULT_SQL)
    parser.add_argument("--mirror", type=Path, default=DEFAULT_MIRROR_SQL)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--keep-ids", type=Path, default=DEFAULT_KEEP_IDS)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--sync-db", action="store_true", help="Delete sql-* scenic rows from SQLite when their source SQL id was removed.")
    parser.add_argument(
        "--include-minor",
        action="store_true",
        help="Keep non-4A/5A scenic POIs. Default is major-only cleanup for a compact production source table.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def clean_text(value):
    return SPACE_RE.sub(" ", str(value or "").strip())


def normalize(value):
    value = clean_text(value).lower()
    return PUNCT_RE.sub("", value)


def normalize_title(value):
    return normalize(PAREN_RE.sub("", clean_text(value)))


def normalize_type(value):
    groups = []
    seen_groups = set()
    for group in clean_text(value).split("|"):
        parts = [part.strip() for part in group.split(";") if part.strip()]
        compact = []
        for part in parts:
            if not compact or compact[-1] != part:
                compact.append(part)
        if compact and len(set(compact)) == 1:
            compact = [compact[0]]
        normalized = ";".join(compact)
        if normalized and normalized not in seen_groups:
            seen_groups.add(normalized)
            groups.append(normalized)
    return "|".join(groups)


def category_parts(type_desc):
    parts = []
    for group in clean_text(type_desc).split("|"):
        group_parts = [part.strip() for part in group.split(";") if part.strip()]
        if group_parts:
            parts.append(group_parts[-1])
    return parts


def known_core_sub_poi_reason(title):
    title_key = normalize_title(title)
    for parent in KNOWN_CORE_PREFIXES:
        parent_key = normalize_title(parent)
        if title_key.startswith(parent_key) and title_key != parent_key:
            suffix = title_key[len(parent_key):]
            if OFFICIAL_SCENIC_SUFFIX_RE.match(suffix):
                return ""
            return "known_core_sub_poi"
    return ""


def valid_coordinate(lon, lat):
    try:
        lon = float(lon)
        lat = float(lat)
    except (TypeError, ValueError):
        return False
    return 73 <= lon <= 136 and 3 <= lat <= 54


def round_coord(value, digits):
    try:
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def coord_distance_km(a, b):
    ax = round_coord(a["gpsx"], 8)
    ay = round_coord(a["gpsy"], 8)
    bx = round_coord(b["gpsx"], 8)
    by = round_coord(b["gpsy"], 8)
    if None in (ax, ay, bx, by):
        return None
    # A lightweight local approximation is enough for deciding whether one POI
    # is an internal sub-point of a nearby parent scenic spot.
    lon_km = (ax - bx) * 85
    lat_km = (ay - by) * 111
    return (lon_km * lon_km + lat_km * lat_km) ** 0.5


def quality(row):
    score = 0
    title = row["title"]
    address = row["add"]
    type_desc = row["type"]
    if address:
        score += 12
    if row["tel"]:
        score += 4
    if row["poiid"]:
        score += 4
    if "世界遗产" in type_desc or "国家级景点" in type_desc:
        score += 16
    if row.get("official_level") == "5A":
        score += 30
    if row.get("official_level") == "4A":
        score += 22
    if "省级景点" in type_desc:
        score += 10
    if any(word in type_desc for word in ("动物园", "植物园", "水族馆", "纪念馆", "寺庙道观", "公园")):
        score += 6
    if "风景名胜相关;旅游景点" in type_desc:
        score -= 6
    if not address:
        score -= 8
    if "附近" in address:
        score -= 3
    if ACCESSORY_TITLE_RE.search(title) or ACCESSORY_WORD_RE.search(title) or ACCESSORY_WORD_RE.search(type_desc):
        score -= 60
    score += min(len(title), 20) / 10
    return score


def row_from_values(values):
    padded = list(values[: len(ALL_COLUMNS)]) + [""] * max(0, len(ALL_COLUMNS) - len(values))
    raw = dict(zip(ALL_COLUMNS, padded))
    row = {}
    for key in ALL_COLUMNS:
        row[key] = clean_text(raw.get(key, ""))
    row["id"] = int(row["id"])
    row["type"] = normalize_type(row["type"])
    if not row.get("quality_score"):
        row["quality_score"] = "0"
    ensure_enhanced_fields(row)
    return row


def ensure_enhanced_fields(row):
    normalize_region_fields(row)
    normalize_region_text_fields(row)
    text = " ".join(str(row.get(key) or "") for key in ("title", "type", "main_category", "theme_names", "tags"))
    matched = [(slug, name) for slug, name, pattern in THEME_RULES if pattern.search(text)]
    if not matched:
        matched = [("nature", "自然风光")]
    slugs = append_unique(row.get("theme_slugs"), [slug for slug, _name in matched])
    names = append_unique(row.get("theme_names"), [name for _slug, name in matched])
    if not row.get("main_category"):
        row["main_category"] = category_parts(row.get("type"))[-1] if category_parts(row.get("type")) else names[0]
    row["theme_slugs"] = ",".join(slugs[:6])
    row["theme_names"] = ",".join(names[:6])
    tags = append_unique(row.get("tags"), [row["main_category"], *names, "全国景点"])
    if row.get("official_level"):
        tags = append_unique(",".join(tags), [f"{row['official_level']}景区", "国家A级景区"])
    row["tags"] = ",".join(tags[:12])
    if not row.get("best_season"):
        row["best_season"] = best_season_for(names)
    if not row.get("audience"):
        row["audience"] = audience_for(names)
    if not row.get("recommended_duration"):
        row["recommended_duration"] = "2-6小时" if row.get("official_level") in ("4A", "5A") else "1-3小时"
    area = "".join(part for part in (row.get("province"), row.get("city"), row.get("district")) if part)
    if not row.get("summary"):
        level = f"{row.get('official_level')}旅游景区" if row.get("official_level") else row.get("main_category") or "旅游景点"
        row["summary"] = f"{row['title']}是{area or '中国'}的{level}，适合{row['theme_names']}等旅行方式。"
    if not row.get("description"):
        address = row.get("add") or row.get("web_address") or "待补充"
        row["description"] = f"{row['title']}位于{area or '中国'}，地址为{address}。站内按名称、行政区划、坐标、原始分类和A级信息归入{row['theme_names']}主题，适合景区检索、主题浏览、路线规划和后续公开来源补全。出行前请以景区官方公告或现场公示核对开放时间、门票预约、天气和交通管制信息。"
    if not row.get("route_idea"):
        row["route_idea"] = route_for(names)
    row["data_version"] = row.get("data_version") or "2026-clean-enhanced-v2"
    row["updated_at"] = row.get("updated_at") or datetime.now().isoformat(timespec="seconds")


def normalize_region_fields(row):
    for city_key, province_key in (("city", "province"), ("web_city", "web_province")):
        city = row.get(city_key) or ""
        match = FALLBACK_REGION_RE.match(city)
        if not match:
            continue
        province = row.get(province_key) or ""
        prefix = match.group(1)[:2]
        if province and DIRECT_REGION_BY_PREFIX.get(prefix) == province:
            row[city_key] = province
        elif prefix in DIRECT_REGION_BY_PREFIX:
            row[city_key] = DIRECT_REGION_BY_PREFIX[prefix]


def normalize_region_text_fields(row):
    replacements = {}
    for source_key, target_key in (("city", "web_city"), ("district", "web_district")):
        source = row.get(source_key) or ""
        target = row.get(target_key) or ""
        if FALLBACK_REGION_RE.match(source) and target and not FALLBACK_REGION_RE.match(target):
            replacements[source] = target
    if not replacements:
        return
    for field in ("summary", "description"):
        text = row.get(field) or ""
        for source, target in replacements.items():
            text = text.replace(source, target)
        row[field] = text


def append_unique(current, values):
    items = []
    for value in str(current or "").replace(";", ",").split(","):
        value = value.strip()
        if value and value not in items:
            items.append(value)
    for value in values:
        value = str(value or "").strip()
        if value and value not in items:
            items.append(value)
    return items


def best_season_for(names):
    text = ",".join(names)
    if "避暑" in text:
        return "6-9 月"
    if "徒步" in text:
        return "春秋最佳"
    if "人文" in text:
        return "四季皆宜"
    return "春夏秋皆宜"


def audience_for(names):
    text = ",".join(names)
    audiences = []
    if "人文" in text:
        audiences.append("历史文化爱好者")
    if "徒步" in text:
        audiences.append("体力较好、喜欢户外的人")
    if "摄影" in text:
        audiences.append("摄影玩家、内容创作者")
    if "亲子" in text:
        audiences.append("亲子家庭")
    if not audiences:
        audiences.append("自然爱好者、周边游游客")
    return "、".join(audiences)


def route_for(names):
    text = ",".join(names)
    if "徒步" in text:
        return "游客中心 - 核心步道 - 观景台 - 下山接驳"
    if "人文" in text:
        return "入口 - 核心展陈/古建 - 周边街区 - 城市联游"
    if "亲子" in text:
        return "主入口 - 亲子体验区 - 休息补给点 - 周边轻游"
    return "景区入口 - 核心游览点 - 周边观景点"


def read_rows(path):
    rows = []
    parse_errors = []
    for line_no, line in enumerate(path.open(encoding="utf-8", errors="ignore"), start=1):
        match = INSERT_RE.match(line.strip())
        if not match:
            continue
        try:
            values = ast.literal_eval(f"({match.group(1)})")
            if len(values) < len(BASE_COLUMNS):
                raise ValueError(f"expected at least {len(BASE_COLUMNS)} values, got {len(values)}")
            rows.append(row_from_values(values))
        except Exception as exc:
            parse_errors.append({"line": line_no, "error": str(exc), "text": line[:200]})
    return rows, parse_errors


def is_major_scenic_level(row):
    type_desc = row.get("type") or ""
    return row.get("official_level") in {"4A", "5A"} or "4A景区" in type_desc or "5A景区" in type_desc


def base_remove_reason(row, major_only=False):
    if not row["title"]:
        return "empty_title"
    if not row["areaid"] and not has_region_fallback(row):
        return "empty_areaid"
    if not valid_coordinate(row["gpsx"], row["gpsy"]) and not is_official_level_with_region(row):
        return "invalid_coordinate"
    if not SCENIC_TYPE_RE.search(row["type"]):
        return "non_scenic_type"
    categories = category_parts(row["type"])
    category_text = ";".join(categories)
    title = row["title"]
    known_core_reason = known_core_sub_poi_reason(title)
    if known_core_reason:
        return known_core_reason
    if (
        HARD_NON_SCENIC_CATEGORY_RE.search(category_text)
        and not STRONG_SCENIC_CATEGORY_RE.search(category_text)
        and not OFFICIAL_SCENIC_SUFFIX_RE.search(title)
    ):
        return "non_destination_category"
    if "城市广场" in categories and title.endswith("广场") and not LANDMARK_SQUARE_RE.search(title):
        return "low_value_city_square"
    if LOW_VALUE_TITLE_RE.search(title) and not OFFICIAL_SCENIC_SUFFIX_RE.search(title):
        return "low_value_facility_or_business"
    if ACCESSORY_WORD_RE.search(row["type"]) or ACCESSORY_WORD_RE.search(row["title"]):
        return "accessory_facility"
    if ACCESSORY_TITLE_RE.search(row["title"]):
        return "accessory_gate_or_entrance"
    if major_only and not is_major_scenic_level(row):
        return "not_major_scenic_level"
    return ""


def has_region_fallback(row):
    has_region = any(row.get(key) for key in ("province", "city", "district", "web_province", "web_city", "web_district"))
    has_level = row.get("official_level") in {"4A", "5A"}
    has_address = bool(row.get("add") or row.get("web_address"))
    return (has_level or has_region or has_address) and (valid_coordinate(row["gpsx"], row["gpsy"]) or is_official_level_with_region(row))


def is_official_level_with_region(row):
    has_region = any(row.get(key) for key in ("province", "city", "district", "web_province", "web_city", "web_district"))
    has_address = bool(row.get("add") or row.get("web_address"))
    return row.get("official_level") in {"4A", "5A"} and (has_region or has_address)


def choose_best(rows):
    return max(rows, key=lambda row: (quality(row), bool(row["add"]), -row["id"]))


def is_sub_poi_of_parent(row, parent):
    if PAREN_RE.search(parent["title"]):
        return False
    title_key = normalize_title(row["title"])
    parent_key = normalize_title(parent["title"])
    if not parent_key or title_key == parent_key or not title_key.startswith(parent_key):
        return False
    parent_category_text = ";".join(category_parts(parent["type"]))
    if len(parent_key) < 4 and not STRONG_SCENIC_CATEGORY_RE.search(parent_category_text):
        return False
    suffix = title_key[len(parent_key):]
    if len(suffix) > 10:
        return False
    if OFFICIAL_SCENIC_SUFFIX_RE.match(suffix):
        return False
    if KEEP_SUB_POI_SUFFIX_RE.match(suffix):
        return False
    row_addr = normalize(row["add"])
    parent_is_park_collection = any(word in parent["type"] for word in ("动物园", "植物园", "水族馆"))
    if not SUB_POI_SUFFIX_RE.match(suffix):
        if not (parent_is_park_collection and len(suffix) <= 8) and not (row_addr and parent_key in row_addr and len(suffix) <= 8):
            return False
    parent_addr = normalize(parent["add"])
    if row["areaid"] != parent["areaid"] and row["areaid"][:4] != parent["areaid"][:4]:
        return False
    if row_addr and parent_addr and (row_addr.startswith(parent_addr) or parent_addr.startswith(row_addr)):
        return True
    if row_addr and parent_key in row_addr:
        return True
    distance = coord_distance_km(row, parent)
    if distance is not None and distance <= 2.0:
        return True
    return False


def deduplicate(rows, major_only=False):
    removed = {}
    kept_candidates = []
    reasons = Counter()
    samples = defaultdict(list)

    for row in rows:
        reason = base_remove_reason(row, major_only=major_only)
        if reason:
            removed[row["id"]] = reason
            reasons[reason] += 1
            if len(samples[reason]) < 20:
                samples[reason].append(sample_row(row))
        else:
            kept_candidates.append(row)

    exact_groups = defaultdict(list)
    for row in kept_candidates:
        if row["id"] in removed:
            continue
        title_key = normalize_title(row["title"])
        addr_key = normalize(row["add"])
        if addr_key:
            key = ("title_area_addr", title_key, row["areaid"], addr_key)
        else:
            key = ("title_area_coord", title_key, row["areaid"], round_coord(row["gpsx"], 5), round_coord(row["gpsy"], 5))
        exact_groups[key].append(row)

    for group_rows in exact_groups.values():
        if len(group_rows) <= 1:
            continue
        best = choose_best(group_rows)
        for row in group_rows:
            if row["id"] != best["id"]:
                removed[row["id"]] = "duplicate_same_title_location"
                reasons["duplicate_same_title_location"] += 1
                if len(samples["duplicate_same_title_location"]) < 20:
                    samples["duplicate_same_title_location"].append(sample_row(row))

    coord_groups = defaultdict(list)
    for row in kept_candidates:
        if row["id"] in removed:
            continue
        key = (normalize_title(row["title"]), row["areaid"], round_coord(row["gpsx"], 4), round_coord(row["gpsy"], 4))
        coord_groups[key].append(row)

    for group_rows in coord_groups.values():
        if len(group_rows) <= 1:
            continue
        best = choose_best(group_rows)
        for row in group_rows:
            if row["id"] != best["id"]:
                removed[row["id"]] = "duplicate_near_same_title"
                reasons["duplicate_near_same_title"] += 1
                if len(samples["duplicate_near_same_title"]) < 20:
                    samples["duplicate_near_same_title"].append(sample_row(row))

    if major_only:
        region_title_groups = defaultdict(list)
        for row in kept_candidates:
            if row["id"] in removed:
                continue
            title_key = normalize_title(row["title"])
            province_key = normalize(row.get("province") or row.get("web_province") or row["areaid"][:2])
            city_key = normalize(row.get("city") or row.get("web_city") or row["areaid"][:4])
            region_title_groups[(title_key, province_key, city_key)].append(row)

        for group_rows in region_title_groups.values():
            if len(group_rows) <= 1:
                continue
            best = choose_best(group_rows)
            for row in group_rows:
                if row["id"] != best["id"]:
                    removed[row["id"]] = "duplicate_same_title_region"
                    reasons["duplicate_same_title_region"] += 1
                    if len(samples["duplicate_same_title_region"]) < 20:
                        item = sample_row(row)
                        item["kept"] = sample_row(best)
                        samples["duplicate_same_title_region"].append(item)

    area_rows = defaultdict(list)
    title_keys = {}
    for row in kept_candidates:
        if row["id"] not in removed:
            title_keys[row["id"]] = normalize_title(row["title"])
            area_rows[row["areaid"][:4]].append(row)

    for rows_in_area in area_rows.values():
        title_index = defaultdict(list)
        for row in rows_in_area:
            title_index[title_keys[row["id"]]].append(row)
        for row in rows_in_area:
            if row["id"] in removed:
                continue
            title_key = title_keys[row["id"]]
            possible_parents = []
            for prefix_len in range(min(len(title_key) - 1, 18), 3, -1):
                possible_parents.extend(title_index.get(title_key[:prefix_len], []))
            for parent in possible_parents:
                if is_sub_poi_of_parent(row, parent):
                    removed[row["id"]] = "sub_poi_under_parent"
                    reasons["sub_poi_under_parent"] += 1
                    if len(samples["sub_poi_under_parent"]) < 20:
                        item = sample_row(row)
                        item["parent"] = sample_row(parent)
                        samples["sub_poi_under_parent"].append(item)
                    break

    kept = [row for row in kept_candidates if row["id"] not in removed]
    kept.sort(key=lambda row: row["id"])
    return kept, removed, reasons, samples


def sample_row(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "add": row["add"],
        "type": row["type"],
        "areaid": row["areaid"],
        "gps": [row["gpsx"], row["gpsy"]],
    }


def sql_quote(value):
    return "'" + str(value or "").replace("\\", "\\\\").replace("'", "\\'") + "'"


def row_to_insert(row):
    quoted = [sql_quote(row.get(column, "")) for column in ALL_COLUMNS]
    return f"INSERT INTO `tpt_data_jingdian` VALUES ({', '.join(quoted)});\n"


def write_sql(path, rows):
    max_id = max((row["id"] for row in rows), default=0)
    header = f"""SET FOREIGN_KEY_CHECKS=0;

-- Optimized by scripts/clean_tpt_jingdian_sql.py at {datetime.now().isoformat(timespec='seconds')}
-- Rows kept: {len(rows)}
-- Data version: 2026-clean-enhanced-v2
-- Policy: major-only 4A/5A scenic source, keep enhanced fields, remove small POIs, facilities and duplicates.

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
  `cover_image_url` varchar(500) DEFAULT NULL,
  `gallery` text,
  `image_source` varchar(120) DEFAULT NULL,
  `image_source_url` varchar(500) DEFAULT NULL,
  `image_license` varchar(120) DEFAULT NULL,
  `image_attribution` varchar(500) DEFAULT NULL,
  `image_status` varchar(40) DEFAULT NULL,
  `media_checked_at` varchar(30) DEFAULT NULL,
  `profile_source` varchar(120) DEFAULT NULL,
  `profile_source_url` varchar(500) DEFAULT NULL,
  `profile_updated_at` varchar(30) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_areaid` (`areaid`),
  KEY `idx_poiid` (`poiid`),
  KEY `idx_region` (`province`,`city`,`district`),
  KEY `idx_main_category` (`main_category`),
  KEY `idx_theme_slugs` (`theme_slugs`),
  KEY `idx_official_level` (`official_level`),
  KEY `idx_quality_score` (`quality_score`),
  KEY `idx_image_status` (`image_status`)
) ENGINE=InnoDB AUTO_INCREMENT={max_id + 1} DEFAULT CHARSET=utf8mb4;

"""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header)
        for row in rows:
            handle.write(row_to_insert(row))


def backup(path, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{path.stem}-before-clean-{stamp}{path.suffix}"
    shutil.copy2(path, target)
    return target


def sync_sqlite(db_path, keep_ids, dry_run):
    if not db_path.exists():
        return {"enabled": True, "db_exists": False}
    backup_path = None
    if not dry_run:
        backup_path = backup(db_path, db_path.parent / "backups")
    keep_ids = set(keep_ids)
    slug_re = re.compile(r"^sql-(\d+)-")
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT id, slug FROM scenic_spots WHERE slug LIKE 'sql-%'").fetchall()
        delete_ids = []
        for row in rows:
            match = slug_re.match(row["slug"] or "")
            if match and int(match.group(1)) not in keep_ids:
                delete_ids.append(row["id"])
        if not dry_run and delete_ids:
            for table, column in (
                ("scenic_images", "scenic_id"),
                ("comments", "scenic_id"),
                ("favorites", "scenic_id"),
                ("nearby_recommendations", "scenic_id"),
                ("scenic_candidates", "scenic_id"),
                ("scenic_image_candidates", "scenic_id"),
                ("enrichment_tasks", "scenic_id"),
                ("enrichment_results", "scenic_id"),
            ):
                try:
                    conn.executemany(f"DELETE FROM {table} WHERE {column}=?", [(item,) for item in delete_ids])
                except sqlite3.OperationalError:
                    pass
            conn.executemany("DELETE FROM scenic_spots WHERE id=?", [(item,) for item in delete_ids])
            conn.commit()
        raw_count = conn.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]
        conn.execute("DROP TABLE IF EXISTS temp._tpt_keep_ids")
        conn.execute("CREATE TEMP TABLE _tpt_keep_ids (source_id INTEGER PRIMARY KEY)")
        conn.executemany("INSERT OR IGNORE INTO _tpt_keep_ids (source_id) VALUES (?)", [(item,) for item in keep_ids])
        delete_source_count = conn.execute(
            """
            SELECT COUNT(*) AS c
            FROM tpt_jingdian
            WHERE NOT EXISTS (
              SELECT 1 FROM _tpt_keep_ids k WHERE k.source_id=tpt_jingdian.source_id
            )
            """
        ).fetchone()["c"]
        if not dry_run and delete_source_count:
            conn.execute(
                """
                DELETE FROM tpt_jingdian
                WHERE NOT EXISTS (
                  SELECT 1 FROM _tpt_keep_ids k WHERE k.source_id=tpt_jingdian.source_id
                )
                """
            )
            try:
                conn.execute("DELETE FROM tpt_jingdian_fts")
                conn.execute(
                    """
                    INSERT INTO tpt_jingdian_fts (source_id,name,address,category_path,category,search_text)
                    SELECT source_id,name,address,category_path,category,search_text
                    FROM tpt_jingdian
                    """
                )
            except sqlite3.OperationalError:
                pass
            conn.commit()
        remaining = conn.execute("SELECT COUNT(*) AS c FROM scenic_spots").fetchone()["c"]
        remaining_tpt = conn.execute("SELECT COUNT(*) AS c FROM tpt_jingdian").fetchone()["c"]
    return {
        "enabled": True,
        "db_exists": True,
        "backup": str(backup_path) if backup_path else "",
        "sql_slug_rows_seen": len(rows),
        "deleted_scenic_rows": len(delete_ids),
        "raw_tpt_rows_seen": raw_count,
        "deleted_raw_tpt_rows": delete_source_count,
        "remaining_raw_tpt_rows": remaining_tpt,
        "remaining_scenic_rows": remaining,
        "dry_run": dry_run,
    }


def main():
    args = parse_args()
    rows, parse_errors = read_rows(args.input)
    major_only = not args.include_minor
    kept, removed, reasons, samples = deduplicate(rows, major_only=major_only)
    keep_ids = [row["id"] for row in kept]
    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "input": str(args.input),
        "originalRows": len(rows),
        "parseErrors": parse_errors[:20],
        "keptRows": len(kept),
        "removedRows": len(removed),
        "removedByReason": dict(reasons),
        "removedSamples": {key: value for key, value in samples.items()},
        "mode": "major-only-4A-5A" if major_only else "include-minor",
        "notes": [
            "保留原始 id，便于回溯 POI 来源。",
            "默认只保留 4A/5A 等大景区源记录，非 A 级小型 POI 从生产源表移除。",
            "删除明显门/入口/停车/售票/游客中心等附属点。",
            "删除旅游集散中心、换乘中心、服务中心、管理办公室等非游览主体。",
            "对同名同区同地址、同名同区同坐标记录保留质量分最高的一条。",
            "主景区存在时，压缩同区、同名前缀、近距离或同地址的馆/区/池/亭等子 POI。",
            "不按同地址删除不同名称，避免误删独立景区。",
        ],
    }

    if args.sync_db:
        report["sqliteSync"] = sync_sqlite(args.db, keep_ids, args.dry_run)

    if not args.dry_run:
        root_backup = backup(args.input, args.backup_dir)
        report["rootSqlBackup"] = str(root_backup)
        write_sql(args.input, kept)
        if args.mirror:
            args.mirror.parent.mkdir(parents=True, exist_ok=True)
            if args.mirror.exists():
                report["mirrorSqlBackup"] = str(backup(args.mirror, args.backup_dir))
            write_sql(args.mirror, kept)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        args.keep_ids.write_text(json.dumps(keep_ids, ensure_ascii=False), encoding="utf-8")
    else:
        print(json.dumps(report, ensure_ascii=False, indent=2))

    print(json.dumps({
        "originalRows": len(rows),
        "keptRows": len(kept),
        "removedRows": len(removed),
        "removedByReason": dict(reasons),
        "report": str(args.report),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
