import argparse
import re
from datetime import datetime
from pathlib import Path

from app.core.database import get_db, rows_to_list


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
FALLBACK_REGION_RE = re.compile(r"^(\d+)(省级区域|地区|区县)$")


def sql_quote(value):
    return "'" + str(value or "").replace("\\", "\\\\").replace("'", "\\'") + "'"


def normalized_region(primary, fallback):
    primary = str(primary or "").strip()
    fallback = str(fallback or "").strip()
    if FALLBACK_REGION_RE.match(primary) and fallback and not FALLBACK_REGION_RE.match(fallback):
        return fallback
    return primary


def clean_region_text(text, row):
    text = str(text or "")
    replacements = {
        str(row.get("city") or ""): str(row.get("web_city") or ""),
        str(row.get("district") or ""): str(row.get("web_district") or ""),
    }
    for source, target in replacements.items():
        if source and target and FALLBACK_REGION_RE.match(source) and not FALLBACK_REGION_RE.match(target):
            text = text.replace(source, target)
    return text


def row_to_sql_values(row):
    city = normalized_region(row.get("city"), row.get("web_city"))
    district = normalized_region(row.get("district"), row.get("web_district"))
    values = {
        "id": row.get("source_id"),
        "title": row.get("name"),
        "tel": row.get("phone"),
        "add": row.get("address"),
        "type": row.get("category_path"),
        "areaid": row.get("areaid"),
        "poiid": row.get("poiid"),
        "gcjx": row.get("gcj_lng"),
        "gcjy": row.get("gcj_lat"),
        "gpsx": row.get("longitude") or row.get("web_longitude"),
        "gpsy": row.get("latitude") or row.get("web_latitude"),
        "province": row.get("province") or row.get("web_province"),
        "city": city,
        "district": district,
        "main_category": row.get("main_category"),
        "theme_slugs": row.get("theme_slugs"),
        "theme_names": row.get("theme_names"),
        "tags": row.get("tags"),
        "summary": clean_region_text(row.get("summary"), row),
        "description": clean_region_text(row.get("description"), row),
        "best_season": row.get("best_season"),
        "audience": row.get("audience"),
        "recommended_duration": row.get("recommended_duration"),
        "route_idea": row.get("route_idea"),
        "quality_score": row.get("quality_score"),
        "data_version": row.get("data_version"),
        "updated_at": row.get("source_updated_at"),
        "official_level": row.get("official_level"),
        "level_source": row.get("level_source"),
        "level_source_url": row.get("level_source_url"),
        "level_verified_at": row.get("level_verified_at"),
        "a_level_year": row.get("a_level_year"),
        "web_province": row.get("web_province"),
        "web_city": row.get("web_city"),
        "web_district": row.get("web_district"),
        "web_address": row.get("web_address"),
        "web_longitude": row.get("web_longitude"),
        "web_latitude": row.get("web_latitude"),
        "web_source_confidence": row.get("web_source_confidence"),
        "web_update_note": row.get("web_update_note"),
        "cover_image_url": row.get("cover_image_url"),
        "gallery": row.get("gallery"),
        "image_source": row.get("image_source"),
        "image_source_url": row.get("image_source_url"),
        "image_license": row.get("image_license"),
        "image_attribution": row.get("image_attribution"),
        "image_status": row.get("image_status"),
        "media_checked_at": row.get("media_checked_at"),
        "profile_source": row.get("profile_source"),
        "profile_source_url": row.get("profile_source_url"),
        "profile_updated_at": row.get("profile_updated_at"),
    }
    return [values.get(column, "") for column in ALL_COLUMNS]


def create_table_sql(max_id, rows_count):
    return f"""SET FOREIGN_KEY_CHECKS=0;

-- Exported by app.scripts.export_tpt_jingdian_sql at {datetime.now().isoformat(timespec='seconds')}
-- Rows kept: {rows_count}
-- Data version: 2026-major-a-level-media-v1
-- Policy: major-only 4A/5A scenic source with lightweight media/profile URL index.

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


def export_sql(output_path):
    with get_db() as db:
        rows = rows_to_list(
            db.execute(
                """
                SELECT *
                FROM tpt_jingdian
                WHERE official_level IN ('4A','5A')
                ORDER BY source_id
                """
            ).fetchall()
        )
    output_path = Path(output_path)
    max_id = max((int(row.get("source_id") or 0) for row in rows), default=0)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(create_table_sql(max_id=max_id, rows_count=len(rows)))
        for row in rows:
            values = ", ".join(sql_quote(value) for value in row_to_sql_values(row))
            handle.write(f"INSERT INTO `tpt_data_jingdian` VALUES ({values});\n")
    return {"output": str(output_path), "rows": len(rows), "bytes": output_path.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description="Export compact A-level scenic source table from tpt_jingdian.")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(export_sql(args.output))


if __name__ == "__main__":
    main()
