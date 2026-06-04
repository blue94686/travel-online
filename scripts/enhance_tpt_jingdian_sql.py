#!/usr/bin/env python3
import argparse
import csv
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.region_utils import label_area  # noqa: E402
from app.services.theme_catalog import THEME_CATALOG  # noqa: E402


DEFAULT_SQL = ROOT / "tpt_data_jingdian.sql"
DEFAULT_MIRROR_SQL = ROOT / "backend" / "app" / "data" / "tpt_data_jingdian.sql"
DEFAULT_REPORT = ROOT / "docs" / "tpt_data_jingdian_enhance_report.json"
DEFAULT_BACKUP_DIR = ROOT / "backend" / "app" / "data" / "backups"

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

INSERT_PREFIX = "INSERT INTO `tpt_data_jingdian` VALUES ("
SPACE_RE = re.compile(r"\s+")
PUNCT_RE = re.compile(r"[\s·•,，.。;；:：、'\"“”‘’\-—_/\\]+")
PAREN_RE = re.compile(r"[（(].*?[）)]")

SCENIC_TYPE_RE = re.compile(r"(风景名胜|公园广场|博物馆|展览馆|度假村|自然地物|旅游景点|世界遗产|国家级景点|省级景点)")
STRONG_SCENIC_RE = re.compile(r"(世界遗产|国家级景点|省级景点|寺庙道观|博物馆|纪念馆|森林公园|湿地公园|国家公园|地质公园|动物园|植物园|水族馆|风景区|旅游区|度假区)")
KEEP_DESTINATION_TITLE_RE = re.compile(r"(古镇|古村|水乡|公园|花港|大观园|生态园|本草园|风景区|景区|旅游区|度假区|森林|湿地|植物园|动物园|博物馆|纪念馆)$")
LOW_VALUE_TITLE_RE = re.compile(
    r"(?:"
    r"入口|出口|出入口|停车场|售票处|售票点|检票口|游客中心|服务中心|管理处|卫生间|洗手间"
    r"|提示牌|告示牌|投诉处|办公室|委员会|售楼处|接待处|咨询处|服务处|收费处"
    r"|观光车|摆渡车|小火车|游船售票|售票亭|游客须知|讲解服务"
    r"|社区广场|文体广场|健身广场|文化广场|人口文化园|活动广场|职工之家|老年活动"
    r"|培训中心|会议中心|棋牌|茶楼|招待所|餐厅|饭店|农家乐|购物点|投诉点"
    r"|房地产|住宅|小区|公寓|商业街区|公交站|地铁站"
    r")"
)
LOW_VALUE_CATEGORY_RE = re.compile(r"(住宅小区|购物中心|中餐厅|普通地名|商务住宅|公司企业|政府机构)")
LANDMARK_SQUARE_RE = re.compile(r"(天安门广场|五四广场|星海广场|泉城广场|朝天门广场|人民广场|市民广场|奥林匹克公园|大雁塔北广场|音乐广场)")

THEME_RULES = {
    "hiking": re.compile(r"(徒步|登山|步道|栈道|爬山|山脊|山|峰|岭|峡|谷|森林|长城|古道| trail)", re.I),
    "heritage": re.compile(r"(古|遗址|故居|纪念|博物馆|美术馆|寺|庙|观|宫|殿|塔|陵|祠|书院|会馆|城墙|古城|牌坊|石窟|文物|历史|文化)"),
    "photo": re.compile(r"(摄影|打卡|观景|日出|日落|云海|花海|玻璃|天空|地标|观景台|观景点)"),
    "nature": re.compile(r"(自然|山水|湖|河|江|海|岛|湾|森林|湿地|瀑|峡|谷|草原|地质|国家公园|风景区|公园|自然保护区)"),
    "food": re.compile(r"(美食|小吃|老街|街区|夜市|古镇|民俗|市集)"),
    "drive": re.compile(r"(自驾|公路|环线|景观大道|湖岸|草原天路|独库|川藏|滇藏|青藏|服务区)"),
    "family": re.compile(r"(亲子|儿童|乐园|动物园|植物园|水族馆|海洋|游乐|公园|科普|科技馆)"),
    "summer": re.compile(r"(避暑|清凉|漂流|峡谷|森林|瀑|湖|山|水上|溶洞|洞|溪)"),
    "flower": re.compile(r"(赏花|花海|花|樱|梅|桃|荷|油菜|牡丹|菊|湿地|踏青|园艺)"),
    "snow": re.compile(r"(冰雪|滑雪|雪|冰|温泉|冰瀑|冬季|雪山)"),
}


def parse_args():
    parser = argparse.ArgumentParser(description="Enhance tpt_data_jingdian.sql with website theme fields and stricter cleanup.")
    parser.add_argument("--input", type=Path, default=DEFAULT_SQL)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--mirror", type=Path, default=DEFAULT_MIRROR_SQL)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUP_DIR)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def clean_text(value):
    return SPACE_RE.sub(" ", str(value or "").strip())


def normalize(value):
    return PUNCT_RE.sub("", clean_text(value).lower())


def normalize_title(value):
    return normalize(PAREN_RE.sub("", clean_text(value)))


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


def parse_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def valid_coordinate(lon, lat):
    lon = parse_float(lon)
    lat = parse_float(lat)
    return lon is not None and lat is not None and 73 <= lon <= 136 and 3 <= lat <= 54


def read_rows(path):
    rows = []
    parse_errors = []
    columns = BASE_COLUMNS + ENHANCED_COLUMNS
    with path.open("r", encoding="utf-8", newline="", errors="ignore") as stream:
        for line_no, line in enumerate(stream, start=1):
            values = parse_insert_values(line)
            if not values:
                continue
            if len(values) < len(BASE_COLUMNS):
                parse_errors.append({"line": line_no, "error": f"expected at least 11 values, got {len(values)}"})
                continue
            padded = values[:len(columns)] + [""] * max(0, len(columns) - len(values))
            row = dict(zip(columns, padded))
            try:
                row["id"] = int(row["id"])
            except (TypeError, ValueError):
                parse_errors.append({"line": line_no, "error": f"invalid id {row.get('id')}"})
                continue
            for key in columns:
                if key != "id":
                    row[key] = clean_text(row.get(key, ""))
            rows.append(row)
    return rows, parse_errors


def category_parts(value):
    parts = []
    for group in clean_text(value).split("|"):
        for part in group.split(";"):
            part = part.strip()
            if part and part not in parts:
                parts.append(part)
    return parts


def main_category(row):
    parts = category_parts(row["type"])
    for part in reversed(parts):
        if part and part != "风景名胜":
            return part
    return parts[-1] if parts else "全国景点"


def area_labels(areaid):
    areaid = clean_text(areaid)
    province = label_area(areaid[:2], 2) if len(areaid) >= 2 else ""
    city = label_area(areaid[:4], 4) if len(areaid) >= 4 else ""
    district = label_area(areaid[:6], 6) if len(areaid) >= 6 else ""
    return province, city, district


def remove_reason(row):
    title = row["title"]
    type_desc = row["type"]
    if not title:
        return "empty_title"
    if len(normalize_title(title)) <= 1:
        return "too_short_title"
    if not row["areaid"]:
        return "empty_areaid"
    if not valid_coordinate(row["gpsx"], row["gpsy"]):
        return "invalid_coordinate"
    if not SCENIC_TYPE_RE.search(type_desc):
        return "non_scenic_type"
    if LOW_VALUE_CATEGORY_RE.search(type_desc) and not STRONG_SCENIC_RE.search(type_desc + title) and not KEEP_DESTINATION_TITLE_RE.search(title):
        return "low_value_category"
    if "城市广场" in type_desc and title.endswith("广场") and not LANDMARK_SQUARE_RE.search(title):
        return "low_value_city_square"
    if LOW_VALUE_TITLE_RE.search(title) and not STRONG_SCENIC_RE.search(type_desc + title):
        return "low_value_facility"
    if re.search(r"(东|西|南|北|东北|西北|东南|西南)?[一二三四五六七八九十0-9]*门$", title) and not STRONG_SCENIC_RE.search(type_desc):
        return "gate_or_entrance"
    return ""


def quality_score(row, themes):
    score = 50
    title = row["title"]
    type_desc = row["type"]
    if row["add"]:
        score += 8
    if row["tel"]:
        score += 4
    if row["poiid"]:
        score += 4
    if "世界遗产" in type_desc or "国家级景点" in type_desc or "5A" in title:
        score += 16
    if "省级景点" in type_desc:
        score += 8
    if STRONG_SCENIC_RE.search(type_desc + title):
        score += 12
    if themes:
        score += min(len(themes), 4) * 3
    if not row["add"]:
        score -= 8
    if "附近" in row["add"]:
        score -= 4
    return max(0, min(100, score))


def classify_themes(row):
    text = " ".join([row["title"], row["type"], row["add"]])
    scored = []
    catalog_by_slug = {item["slug"]: item for item in THEME_CATALOG}
    for item in THEME_CATALOG:
        score = 0
        for keyword in item["keywords"]:
            if keyword and keyword in text:
                score += 3
        regex = THEME_RULES.get(item["slug"])
        if regex and regex.search(text):
            score += 4
        if score >= 4:
            scored.append((score, item["sort_order"], item["slug"]))
    if not scored:
        scored.append((1, catalog_by_slug["nature"]["sort_order"], "nature"))
    scored.sort(key=lambda item: (-item[0], item[1]))
    slugs = []
    for _, _, slug in scored:
        if slug not in slugs:
            slugs.append(slug)
        if len(slugs) >= 4:
            break
    return [catalog_by_slug[slug] for slug in slugs]


def recommended_duration(themes, category):
    slugs = {item["slug"] for item in themes}
    if "hiking" in slugs:
        return "半日-1天"
    if "heritage" in slugs and category in ("博物馆", "纪念馆", "寺庙道观"):
        return "1-3小时"
    if "family" in slugs:
        return "2-4小时"
    if "nature" in slugs:
        return "2-6小时"
    return "1-4小时"


def deduplicate(rows):
    removed = {}
    reasons = Counter()
    samples = defaultdict(list)
    kept = []
    for row in rows:
        reason = remove_reason(row)
        if reason:
            removed[row["id"]] = reason
            reasons[reason] += 1
            if len(samples[reason]) < 20:
                samples[reason].append(sample_row(row))
        else:
            kept.append(row)

    groups = defaultdict(list)
    for row in kept:
        title_key = normalize_title(row["title"])
        addr_key = normalize(row["add"])
        coord_key = (round(parse_float(row["gpsx"]) or 0, 5), round(parse_float(row["gpsy"]) or 0, 5))
        key = (title_key, row["areaid"], addr_key or coord_key)
        groups[key].append(row)

    for group_rows in groups.values():
        if len(group_rows) <= 1:
            continue
        best = max(group_rows, key=lambda item: (bool(item["add"]), bool(item["tel"]), -item["id"]))
        for row in group_rows:
            if row["id"] != best["id"]:
                removed[row["id"]] = "duplicate_same_title_location"
                reasons["duplicate_same_title_location"] += 1
                if len(samples["duplicate_same_title_location"]) < 20:
                    samples["duplicate_same_title_location"].append(sample_row(row))

    result = [row for row in kept if row["id"] not in removed]
    result.sort(key=lambda item: item["id"])
    return result, removed, reasons, samples


def sample_row(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "add": row["add"],
        "type": row["type"],
        "areaid": row["areaid"],
    }


def unique(values):
    result = []
    for value in values:
        value = clean_text(value)
        if value and value not in result:
            result.append(value)
    return result


def enhance_row(row):
    province, city, district = area_labels(row["areaid"])
    category = main_category(row)
    themes = classify_themes(row)
    theme_slugs = [item["slug"] for item in themes]
    theme_names = [item["name"] for item in themes]
    tags = unique(category_parts(row["type"])[-4:] + theme_names + ["全国景点"])
    location = "".join(part for part in (province, city, district) if part)
    if not location:
        location = row["add"] or "中国"
    season = unique(item["season"] for item in themes)[:3]
    audiences = unique(item["audience"] for item in themes)[:3]
    route = themes[0]["route_idea"] if themes else "景区入口 - 核心游览点 - 周边补给"
    summary = f"{row['title']}是{location}的{category or '旅游景点'}，适合{','.join(theme_names[:3])}等旅行方式。"
    description = (
        f"{row['title']}位于{location}，地址为{row['add'] or '待补充'}。"
        f"根据景点名称、原始分类和坐标信息，系统将其归入{','.join(theme_names)}主题，"
        "可用于景区检索、主题推荐、路线规划和后续人工资料补全。"
        "出行前建议核对官方开放时间、门票政策、天气和交通管制信息。"
    )
    row.update({
        "province": province,
        "city": city,
        "district": district,
        "main_category": category,
        "theme_slugs": ",".join(theme_slugs),
        "theme_names": ",".join(theme_names),
        "tags": ",".join(tags),
        "summary": summary,
        "description": description,
        "best_season": "、".join(season) or "四季皆宜",
        "audience": "、".join(audiences) or "普通游客",
        "recommended_duration": recommended_duration(themes, category),
        "route_idea": route,
        "quality_score": str(quality_score(row, themes)),
        "data_version": "2026-theme-v1",
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })
    return row


def sql_quote(value):
    return "'" + str(value or "").replace("\\", "\\\\").replace("'", "\\'") + "'"


def row_to_insert(row):
    values = [row[column] for column in BASE_COLUMNS + ENHANCED_COLUMNS]
    return f"INSERT INTO `tpt_data_jingdian` VALUES ({', '.join(sql_quote(value) for value in values)});\n"


def write_sql(path, rows):
    max_id = max((row["id"] for row in rows), default=0)
    header = f"""SET FOREIGN_KEY_CHECKS=0;

-- Enhanced by scripts/enhance_tpt_jingdian_sql.py at {datetime.now().isoformat(timespec='seconds')}
-- Rows kept: {len(rows)}
-- Data version: 2026-theme-v1

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
  PRIMARY KEY (`id`),
  KEY `idx_areaid` (`areaid`),
  KEY `idx_poiid` (`poiid`),
  KEY `idx_region` (`province`,`city`,`district`),
  KEY `idx_main_category` (`main_category`),
  KEY `idx_theme_slugs` (`theme_slugs`),
  KEY `idx_quality_score` (`quality_score`)
) ENGINE=InnoDB AUTO_INCREMENT={max_id + 1} DEFAULT CHARSET=utf8mb4;

"""
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(header)
        for row in rows:
            handle.write(row_to_insert(row))


def backup(path, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target = backup_dir / f"{path.stem}-before-enhance-{stamp}{path.suffix}"
    shutil.copy2(path, target)
    return target


def main():
    args = parse_args()
    output_path = args.output or args.input
    rows, parse_errors = read_rows(args.input)
    kept, removed, reasons, samples = deduplicate(rows)
    enhanced = [enhance_row(row) for row in kept]
    theme_counts = Counter()
    category_counts = Counter()
    for row in enhanced:
        category_counts[row["main_category"]] += 1
        for slug in row["theme_slugs"].split(","):
            if slug:
                theme_counts[slug] += 1

    report = {
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "input": str(args.input),
        "originalRows": len(rows),
        "keptRows": len(enhanced),
        "removedRows": len(removed),
        "removedByReason": dict(reasons),
        "removedSamples": {key: value for key, value in samples.items()},
        "parseErrors": parse_errors[:20],
        "themeCounts": dict(theme_counts),
        "topCategories": dict(category_counts.most_common(40)),
        "schema": list(BASE_COLUMNS + ENHANCED_COLUMNS),
        "dryRun": args.dry_run,
    }

    if not args.dry_run:
        if output_path.exists():
            report["rootSqlBackup"] = str(backup(output_path, args.backup_dir))
        write_sql(output_path, enhanced)
        if args.mirror:
            args.mirror.parent.mkdir(parents=True, exist_ok=True)
            if args.mirror.exists():
                report["mirrorSqlBackup"] = str(backup(args.mirror, args.backup_dir))
            write_sql(args.mirror, enhanced)
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "originalRows": len(rows),
        "keptRows": len(enhanced),
        "removedRows": len(removed),
        "removedByReason": dict(reasons),
        "themeCounts": dict(theme_counts),
        "report": str(args.report),
        "dryRun": args.dry_run,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
