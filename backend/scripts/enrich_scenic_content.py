#!/usr/bin/env python3
import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.scenic_external_enrichment_service import external_enrich_profile_batch  # noqa: E402
from app.services.scenic_profile_batch_enrichment_service import profile_completion_stats  # noqa: E402


DEFAULT_SQL_FILE = ROOT / "app" / "data" / "tpt_data_jingdian.sql"


def analyze_sql_source(sql_file=DEFAULT_SQL_FILE):
    path = Path(sql_file)
    if not path.exists():
        return {"exists": False, "path": str(path), "table": "", "columns": [], "insert_rows": 0}

    text = path.read_text(encoding="utf-8", errors="ignore")
    table_match = re.search(r"CREATE TABLE `([^`]+)`\s*\((.*?)\)\s*(?:ENGINE=|;)", text, re.S)
    columns = []
    table = ""
    if table_match:
        table = table_match.group(1)
        columns = re.findall(r"^\s*`([^`]+)`\s+", table_match.group(2), re.M)
    insert_rows = len(re.findall(r"INSERT INTO `tpt_data_jingdian` VALUES", text))
    return {
        "exists": True,
        "path": str(path),
        "table": table,
        "columns": columns,
        "insert_rows": insert_rows,
        "size_mb": round(path.stat().st_size / 1024 / 1024, 2),
    }


def run_batch(
    limit=20,
    offset=0,
    province="",
    city="",
    include_public_sources=True,
    sleep_seconds=0.9,
):
    result = external_enrich_profile_batch(
        limit=limit,
        offset=offset,
        province=province,
        city=city,
        only_missing_media=True,
        include_public_sources=include_public_sources,
        sleep_seconds=sleep_seconds,
    )
    return {"batch": result, "completion": profile_completion_stats()}


def main(argv=None):
    parser = argparse.ArgumentParser(description="自动读取全国景区 SQL 源文件，并分批联网采集景区介绍和图片候选。")
    parser.add_argument("--sql-file", default=str(DEFAULT_SQL_FILE), help="全国景区 SQL 源文件路径")
    parser.add_argument("--limit", type=int, default=20, help="本批次处理条数，建议 5-50")
    parser.add_argument("--offset", type=int, default=0, help="本批次起始偏移")
    parser.add_argument("--province", default="", help="只处理指定省份")
    parser.add_argument("--city", default="", help="只处理指定城市")
    parser.add_argument("--no-public-sources", action="store_true", help="关闭 Wikipedia/Commons 公开来源")
    parser.add_argument("--sleep", type=float, default=0.9, help="每条景区之间的等待秒数，避免公开来源限流")
    parser.add_argument("--analyze-only", action="store_true", help="只读取 SQL 文件结构，不执行联网采集")
    args = parser.parse_args(argv)

    source = analyze_sql_source(args.sql_file)
    output = {"source": source}
    if not args.analyze_only:
        output.update(
            run_batch(
                limit=args.limit,
                offset=args.offset,
                province=args.province,
                city=args.city,
                include_public_sources=not args.no_public_sources,
                sleep_seconds=args.sleep,
            )
        )
    print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
