from fastapi import APIRouter, Query

from app.core.config import DATA_DIR
from app.core.response import ok
from app.scripts.export_tpt_jingdian_sql import export_sql
from app.services.nearby_recommendation_service import generate_nearby, get_nearby
from app.services.admin_web_enrichment_service import (
    web_enrichment_candidates,
    web_enrichment_overview,
)
from app.services.scenic_profile_batch_enrichment_service import (
    enrich_profile_all,
    enrich_profile_batch,
    profile_completion_stats,
)
from app.services.scenic_poi_index_service import backfill_theme_poi_index, poi_index_stats
from app.services.tpt_profile_enrichment_service import (
    enrich_tpt_media_all,
    enrich_tpt_media_batch,
    enrich_tpt_profiles_all,
    enrich_tpt_profiles_batch,
    tpt_enrichment_stats,
)
from app.services.tpt_media_job_service import start_tpt_media_job, status_tpt_media_job, stop_tpt_media_job
from app.services.scenic_external_enrichment_service import (
    external_enrich_profile_all,
    external_enrich_profile_batch,
    external_enrichment_readiness,
)
from app.services.scenic_crawler_enrichment_service import (
    approve_low_risk_candidates,
    backfill_public_source_links,
    crawler_status,
    merge_profile_candidates_direct,
    run_crawler_batch,
    start_crawler_job,
    stop_crawler_job,
)
from app.services.scenic_enrichment_service import (
    apply_result,
    approve_image_candidate,
    approve_profile_candidate,
    bulk_profile_search,
    enrichment_overview,
    missing_scenic,
    merge_profile_candidates,
    profile_candidates,
    profile_diff,
    profile_overview,
    reject_profile_candidate,
    reject_image_candidate,
    results,
    run_enrichment,
    run_profile_search,
    tasks,
    update_result_status,
)

router = APIRouter()


@router.get("/admin/web-enrichment/overview")
def web_enrichment_overview_endpoint():
    return ok(web_enrichment_overview())


@router.get("/admin/web-enrichment/candidates")
def web_enrichment_candidates_endpoint(
    type: str = Query("all", pattern="^(all|image|profile|food|hiking|nearby)$"),
    risk: str = Query("all", pattern="^(all|low|medium|high)$"),
    status: str = Query("pending"),
    province: str | None = None,
    city: str | None = None,
    limit: int = Query(50, ge=1, le=200),
):
    return ok(
        web_enrichment_candidates(
            candidate_type=type,
            risk=risk,
            status=status,
            province=province or "",
            city=city or "",
            limit=limit,
        )
    )


@router.get("/admin/enrichment/overview")
def overview():
    return ok(enrichment_overview())


@router.get("/admin/enrichment/profile/overview")
def profile_overview_endpoint():
    return ok(profile_overview())


@router.get("/admin/enrichment/profile/completion-stats")
def profile_completion_stats_endpoint():
    return ok(profile_completion_stats())


@router.get("/admin/enrichment/poi-index/stats")
def poi_index_stats_endpoint():
    return ok(poi_index_stats())


@router.post("/admin/enrichment/poi-index/backfill")
def poi_index_backfill_endpoint(
    limit: int = Query(1000, ge=1, le=50000),
    province: str | None = None,
    city: str | None = None,
    force: bool = False,
):
    return ok(backfill_theme_poi_index(limit=limit, province=province or "", city=city or "", force=force), "主题 POI 索引已补全")


@router.get("/admin/enrichment/tpt/stats")
def tpt_profile_stats_endpoint():
    return ok(tpt_enrichment_stats())


@router.post("/admin/enrichment/tpt/local-batch")
def tpt_local_batch(
    limit: int = Query(5000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    province: str | None = None,
    a_level_only: bool = True,
    force: bool = False,
):
    return ok(
        enrich_tpt_profiles_batch(
            limit=limit,
            offset=offset,
            province=province or "",
            a_level_only=a_level_only,
            force=force,
        ),
        "全国源表资料补齐批次已完成",
    )


@router.post("/admin/enrichment/tpt/local-all")
def tpt_local_all(
    batch_size: int = Query(10000, ge=1000, le=50000),
    province: str | None = None,
    a_level_only: bool = True,
    force: bool = False,
):
    return ok(
        enrich_tpt_profiles_all(
            batch_size=batch_size,
            province=province or "",
            a_level_only=a_level_only,
            force=force,
        ),
        "全国源表资料补齐已完成",
    )


@router.post("/admin/enrichment/tpt/media-batch")
def tpt_media_batch(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    province: str | None = None,
    a_level_only: bool = True,
    only_missing: bool = True,
    sleep_seconds: float = Query(1.0, ge=0, le=5),
    include_public_sources: bool = True,
    use_amap: bool = False,
    include_osm: bool = False,
):
    return ok(
        enrich_tpt_media_batch(
            limit=limit,
            offset=offset,
            province=province or "",
            a_level_only=a_level_only,
            only_missing=only_missing,
            sleep_seconds=sleep_seconds,
            include_public_sources=include_public_sources,
            use_amap=use_amap,
            include_osm=include_osm,
        ),
        "全国源表公开图片采集批次已完成",
    )


@router.post("/admin/enrichment/tpt/media-all")
def tpt_media_all(
    batch_size: int = Query(50, ge=1, le=200),
    max_total: int = Query(500, ge=1, le=10000),
    province: str | None = None,
    a_level_only: bool = True,
    only_missing: bool = True,
    sleep_seconds: float = Query(1.0, ge=0, le=5),
    include_public_sources: bool = True,
    use_amap: bool = False,
    include_osm: bool = False,
):
    return ok(
        enrich_tpt_media_all(
            batch_size=batch_size,
            max_total=max_total,
            province=province or "",
            a_level_only=a_level_only,
            only_missing=only_missing,
            sleep_seconds=sleep_seconds,
            include_public_sources=include_public_sources,
            use_amap=use_amap,
            include_osm=include_osm,
        ),
        "全国源表公开图片限量采集已完成",
    )


@router.post("/admin/enrichment/tpt/media-job/start")
def tpt_media_job_start(
    batch_size: int = Query(3, ge=1, le=50),
    max_total: int = Query(3978, ge=1, le=268594),
    province: str | None = None,
    a_level_only: bool = True,
    only_missing: bool = True,
    sleep_seconds: float = Query(2.0, ge=0.5, le=5),
    include_public_sources: bool = True,
    use_amap: bool = False,
    include_osm: bool = False,
):
    return ok(
        start_tpt_media_job(
            batch_size=batch_size,
            max_total=max_total,
            province=province or "",
            a_level_only=a_level_only,
            only_missing=only_missing,
            sleep_seconds=sleep_seconds,
            include_public_sources=include_public_sources,
            use_amap=use_amap,
            include_osm=include_osm,
        ),
        "全国源表图片全量补全任务已启动",
    )


@router.get("/admin/enrichment/tpt/media-job/status")
def tpt_media_job_status():
    return ok(status_tpt_media_job())


@router.post("/admin/enrichment/tpt/media-job/stop")
def tpt_media_job_stop():
    return ok(stop_tpt_media_job(), "全国源表图片全量补全任务已请求停止")


@router.post("/admin/enrichment/tpt/export-sql")
def tpt_export_sql():
    output_path = DATA_DIR / "tpt_data_jingdian-export.sql"
    return ok(export_sql(output_path), "当前 A 级源表已导出为轻量媒体 SQL")


@router.post("/admin/enrichment/crawler/batch")
def crawler_batch(
    limit: int = Query(10, ge=1, le=100),
    province: str | None = None,
    city: str | None = None,
    only_missing: bool = True,
    target_image_count: int = Query(4, ge=1, le=8),
    include_public_sources: bool = True,
    include_pois: bool = True,
    include_paid_providers: bool = False,
    include_osm: bool = True,
    direct_merge_profiles: bool = False,
    sleep_seconds: float = Query(0.8, ge=0, le=3),
):
    return ok(
        run_crawler_batch(
            limit=limit,
            province=province or "",
            city=city or "",
            only_missing=only_missing,
            target_image_count=target_image_count,
            include_public_sources=include_public_sources,
            include_pois=include_pois,
            include_paid_providers=include_paid_providers,
            include_osm=include_osm,
            direct_merge_profiles=direct_merge_profiles,
            sleep_seconds=sleep_seconds,
        ),
        "爬虫补全批次已完成",
    )


@router.post("/admin/enrichment/crawler/start")
def crawler_job_start(
    batch_size: int = Query(5, ge=1, le=50),
    max_total: int = Query(2528, ge=1, le=50000),
    province: str | None = None,
    city: str | None = None,
    only_missing: bool = True,
    target_image_count: int = Query(4, ge=1, le=8),
    include_public_sources: bool = True,
    include_pois: bool = True,
    include_paid_providers: bool = False,
    include_osm: bool = True,
    direct_merge_profiles: bool = False,
    sleep_seconds: float = Query(1.5, ge=0.5, le=5),
):
    return ok(
        start_crawler_job(
            batch_size=batch_size,
            max_total=max_total,
            province=province or "",
            city=city or "",
            only_missing=only_missing,
            target_image_count=target_image_count,
            include_public_sources=include_public_sources,
            include_pois=include_pois,
            include_paid_providers=include_paid_providers,
            include_osm=include_osm,
            direct_merge_profiles=direct_merge_profiles,
            sleep_seconds=sleep_seconds,
        ),
        "爬虫补全任务已启动",
    )


@router.get("/admin/enrichment/crawler/status")
def crawler_job_status():
    return ok(crawler_status())


@router.post("/admin/enrichment/crawler/stop")
def crawler_job_stop():
    return ok(stop_crawler_job(), "爬虫补全任务已请求停止")


@router.post("/admin/enrichment/crawler/approve-low-risk")
def crawler_approve_low_risk(limit: int = Query(200, ge=1, le=1000), target_image_count: int = Query(4, ge=1, le=8)):
    return ok(approve_low_risk_candidates(limit=limit, target_image_count=target_image_count), "低风险图片和 POI 候选已批量通过")


@router.post("/admin/enrichment/crawler/merge-profiles-direct")
def crawler_merge_profiles_direct(
    limit: int = Query(500, ge=1, le=5000),
    province: str | None = None,
    city: str | None = None,
):
    return ok(merge_profile_candidates_direct(limit=limit, province=province or "", city=city or ""), "公开来源景区资料已直接合并")


@router.post("/admin/enrichment/crawler/backfill-public-sources")
def crawler_backfill_public_sources(
    limit: int = Query(10000, ge=1, le=50000),
    province: str | None = None,
    city: str | None = None,
):
    return ok(backfill_public_source_links(limit=limit, province=province or "", city=city or ""), "公开来源链接已补齐")


@router.get("/admin/enrichment/profile/external-readiness")
def profile_external_readiness_endpoint():
    return ok(external_enrichment_readiness())


@router.post("/admin/enrichment/profile/local-batch")
def local_profile_batch(
    limit: int = Query(5000, ge=1, le=50000),
    offset: int = Query(0, ge=0),
    province: str | None = None,
    force: bool = False,
):
    return ok(enrich_profile_batch(limit=limit, offset=offset, province=province or "", force=force), "本地规则资料补齐批次已完成")


@router.post("/admin/enrichment/profile/local-all")
def local_profile_all(
    batch_size: int = Query(20000, ge=1000, le=50000),
    province: str | None = None,
    force: bool = False,
):
    return ok(enrich_profile_all(batch_size=batch_size, province=province or "", force=force), "本地规则资料补齐已完成")


@router.post("/admin/enrichment/profile/external-batch")
def external_profile_batch(
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    province: str | None = None,
    city: str | None = None,
    only_missing_media: bool = True,
    include_public_sources: bool = True,
    include_paid_providers: bool = False,
):
    return ok(
        external_enrich_profile_batch(
            limit=limit,
            offset=offset,
            province=province or "",
            city=city or "",
            only_missing_media=only_missing_media,
            include_public_sources=include_public_sources,
            include_paid_providers=include_paid_providers,
        ),
        "外部资料候选采集批次已完成",
    )


@router.post("/admin/enrichment/profile/external-all")
def external_profile_all(
    batch_size: int = Query(50, ge=1, le=200),
    max_total: int = Query(500, ge=1, le=1000),
    province: str | None = None,
    city: str | None = None,
    include_public_sources: bool = True,
    include_paid_providers: bool = False,
):
    return ok(
        external_enrich_profile_all(
            batch_size=batch_size,
            max_total=max_total,
            province=province or "",
            city=city or "",
            include_public_sources=include_public_sources,
            include_paid_providers=include_paid_providers,
        ),
        "外部资料候选限量采集已完成",
    )


@router.get("/admin/enrichment/missing")
def missing():
    return ok(missing_scenic())


@router.post("/admin/enrichment/scenic/{scenic_id}/run")
def run_full(scenic_id: int):
    return ok(run_enrichment(scenic_id, "full"), "资料补全任务已生成")


@router.post("/admin/enrichment/profile/{scenic_id}/search")
def search_profile(scenic_id: int):
    return ok(run_profile_search(scenic_id), "景区介绍补全候选已生成")


@router.post("/admin/enrichment/profile/bulk-search")
def bulk_search_profile(
    province: str | None = None,
    city: str | None = None,
    level: str | None = None,
    limit: int = Query(20, ge=1, le=200),
    only_missing: bool = True,
):
    return ok(bulk_profile_search({"province": province, "city": city, "level": level, "limit": limit, "only_missing": only_missing}), "批量补全任务已执行")


@router.get("/admin/enrichment/profile/{scenic_id}/candidates")
def list_profile_candidates(scenic_id: int):
    return ok(profile_candidates(scenic_id))


@router.get("/admin/enrichment/images/{scenic_id}/candidates")
def list_image_candidates(scenic_id: int):
    return ok(image_candidates(scenic_id))


@router.post("/admin/enrichment/images/candidates/{candidate_id}/approve")
def approve_image(candidate_id: int):
    return ok(approve_image_candidate(candidate_id), "图片候选已审核通过并写入轻量图片索引")


@router.post("/admin/enrichment/images/candidates/{candidate_id}/reject")
def reject_image(candidate_id: int):
    return ok(reject_image_candidate(candidate_id), "图片候选已驳回")


@router.post("/admin/enrichment/profile/candidates/{candidate_id}/approve")
def approve_candidate(candidate_id: int):
    return ok(approve_profile_candidate(candidate_id), "候选已通过，等待合并发布")


@router.post("/admin/enrichment/profile/candidates/{candidate_id}/reject")
def reject_candidate(candidate_id: int):
    return ok(reject_profile_candidate(candidate_id), "候选已驳回")


@router.post("/admin/enrichment/profile/{scenic_id}/merge")
def merge_profile(scenic_id: int):
    return ok(merge_profile_candidates(scenic_id), "已合并审核通过的候选")


@router.get("/admin/enrichment/profile/{scenic_id}/diff")
def diff_profile(scenic_id: int):
    return ok(profile_diff(scenic_id))


@router.post("/admin/enrichment/scenic/{scenic_id}/search-images")
def search_images(scenic_id: int):
    return ok(run_enrichment(scenic_id, "image"), "图片候选已生成")


@router.post("/admin/enrichment/scenic/{scenic_id}/search-info")
def search_info(scenic_id: int):
    return ok(run_enrichment(scenic_id, "info"), "资料候选已生成")


@router.get("/admin/enrichment/tasks")
def list_tasks():
    return ok(tasks())


@router.get("/admin/enrichment/results/{task_id}")
def list_results(task_id: int):
    return ok(results(task_id))


@router.post("/admin/enrichment/results/{result_id}/approve")
def approve_result(result_id: int):
    return ok(update_result_status(result_id, "approved"), "候选已通过")


@router.post("/admin/enrichment/results/{result_id}/reject")
def reject_result(result_id: int):
    return ok(update_result_status(result_id, "rejected"), "候选已驳回")


@router.post("/admin/enrichment/results/{result_id}/apply")
def apply_candidate(result_id: int):
    return ok(apply_result(result_id), "候选已应用到景区")


@router.post("/admin/enrichment/nearby/{scenic_id}/generate")
def generate_nearby_for_enrichment(scenic_id: int):
    return ok(generate_nearby(scenic_id), "附近推荐已生成")


@router.post("/admin/scenic/{scenic_id}/nearby/generate")
def generate_nearby_for_scenic(scenic_id: int):
    return ok(generate_nearby(scenic_id), "附近推荐已生成")


@router.get("/admin/scenic/{scenic_id}/nearby")
def admin_nearby(scenic_id: int):
    return ok(get_nearby(scenic_id))
    image_candidates,
