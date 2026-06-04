# Admin Web Enrichment Center Design

Date: 2026-06-04

## Goal

Add a dedicated admin subpage for whole-web scenic updates: scenic images, introductions, nearby food, nearby POI, hiking/trail POI, source labels, candidate review, and background automation.

This page should be a real management center, not a decorative dashboard. It should make existing enrichment and crawler capabilities easier to operate while adding a small backend aggregation layer for status and candidate review.

## Route And Position

- New admin route: `/admin/web-enrichment`
- Sidebar label: `全网更新`
- Topbar title: `全网更新中心`
- Relationship to existing pages:
  - Existing `/admin/enrichment` remains the data/enrichment detail area.
  - New `/admin/web-enrichment` becomes the operator-facing control room for cross-source automatic updates.

## Users

Admin users need to:

- See what scenic data is incomplete.
- Start a controlled whole-web update.
- Scope the update to nationwide, province, city, 5A, missing images, missing profiles, missing nearby POI, or hiking POI.
- Keep all crawled material in a candidate pool by default.
- Batch-approve low-risk image links and low-risk POI.
- Manually review risky or low-confidence candidates.
- Track background job status and failures in real time.

## Existing Backend Capabilities To Reuse

The first implementation should reuse these existing endpoints:

- `GET /api/admin/enrichment/crawler/status`
- `POST /api/admin/enrichment/crawler/batch`
- `POST /api/admin/enrichment/crawler/start`
- `POST /api/admin/enrichment/crawler/stop`
- `POST /api/admin/enrichment/crawler/approve-low-risk`
- `POST /api/admin/enrichment/profile/external-batch`
- `POST /api/admin/enrichment/tpt/media-batch`
- `POST /api/admin/enrichment/tpt/media-job/start`
- `GET /api/admin/enrichment/tpt/media-job/status`
- `POST /api/admin/enrichment/tpt/media-job/stop`
- `GET /api/admin/enrichment/overview`
- `GET /api/admin/enrichment/tasks`

The implementation should also reuse these existing tables and service behavior:

- `scenic_spots`
- `scenic_profile_candidates`
- `scenic_image_candidates`
- `sync_tasks`
- `scenic_crawler_enrichment_service`
- low-risk approval logic for image candidates and POI candidates

## New Backend Additions

### Overview Endpoint

Add:

- `GET /api/admin/web-enrichment/overview`

Response should aggregate:

- total scenic count
- missing image count
- missing introduction/profile count
- missing nearby food count
- missing nearby POI count
- pending image candidates
- pending profile candidates
- pending food POI candidates
- pending hiking POI candidates
- low-risk candidate count
- crawler job status
- TPT media job status
- latest sync/enrichment task summaries

### Candidate Queue Endpoint

Add:

- `GET /api/admin/web-enrichment/candidates`

Query parameters:

- `type`: `all`, `image`, `profile`, `food`, `hiking`, `nearby`
- `risk`: `all`, `low`, `medium`, `high`
- `status`: default `pending`
- `province`
- `city`
- `limit`

Response should return a normalized list with:

- `id`
- `candidate_kind`: `image` or `profile`
- `candidate_type`
- `scenic_id`
- `scenic_name`
- `province`
- `city`
- `title`
- `preview`
- `source_name`
- `source_type`
- `source_url`
- `risk_level`
- `confidence`
- `status`
- `created_at`

This endpoint should read from candidate tables. It should not crawl.

### Policy Payload

The frontend should call existing crawler endpoints with a clearly visible policy payload:

- `batch_size`
- `max_total`
- `province`
- `city`
- `only_missing`
- `include_public_sources`
- `include_pois`
- `include_paid_providers`
- `include_osm`
- `sleep_seconds`

Paid providers remain off by default.

## Admin Page Layout

The page should use the existing admin visual language: compact, restrained, operational, and data-first.

### Section 1: Command Header

Show:

- title: `全网更新中心`
- subtitle explaining that crawled items enter candidate pool by default
- job status badge
- quick actions: `刷新状态`, `试跑一批`, `启动后台更新`, `停止任务`

### Section 2: Strategy Panel

Controls:

- scope: nationwide, province, city
- target: all missing, images only, introductions only, food POI, hiking POI
- source toggles: public sources, OSM, nearby POI, paid providers
- batch size
- max total
- sleep seconds

Use native form controls and segmented buttons. Dangerous or high-cost options such as paid providers must be visually secondary and off by default.

### Section 3: Metrics Strip

Show live metrics from overview:

- missing images
- missing introductions
- missing food POI
- missing hiking/nearby POI
- pending candidates
- low-risk candidates

Do not invent values. If the API is unavailable, show `--` and a clear unavailable state.

### Section 4: Candidate Review

Tabs:

- 全部候选
- 图片外链
- 景区介绍
- 周边美食
- 徒步 POI
- 高风险

Rows/cards should show scenic name, type, risk, confidence, source, preview, and action.

Actions:

- `批量通过低风险`
- `查看来源`
- `进入景区`
- individual approve/reject only where existing endpoint support is available

Unsupported individual actions should render as unavailable, not fake success.

### Section 5: Job Timeline

Show recent task items from crawler status and enrichment tasks:

- status
- read/searched counts
- created candidates
- latest batch
- provider failures
- cooldown reason/seconds

## Data Rules

- Crawled images and POI default to candidate pool.
- Low-risk image links and low-risk food/hiking/nearby POI may be batch-approved.
- High-risk or medium-confidence material stays pending.
- Public sources and OSM are enabled by default.
- Paid providers are disabled by default.
- Do not download large images; store and review external links and attribution/source data.
- Preserve source URL, source name, risk level, and confidence in the UI.
- Never show fake operational numbers.

## Frontend Files

Likely files:

- `frontend/src/router.jsx`
- `frontend/src/components/admin/AdminSidebar.jsx`
- `frontend/src/components/admin/AdminTopbar.jsx`
- `frontend/src/api/admin.js`
- `frontend/src/pages/admin/AdminWebEnrichmentPage.jsx`
- `frontend/src/styles/pages.css`
- `frontend/tests/adminWebEnrichmentPage.test.mjs`

## Backend Files

Likely files:

- `backend/app/routers/admin_enrichment.py`
- `backend/app/services/scenic_crawler_enrichment_service.py`
- `backend/tests/test_admin_web_enrichment_unittest.py`

If service logic grows beyond a few helpers, create:

- `backend/app/services/admin_web_enrichment_service.py`

## Non-Goals

- Do not create a general-purpose unrestricted web crawler.
- Do not bypass robots/rate limits already enforced by provider services.
- Do not auto-publish high-risk content.
- Do not require a new frontend UI library.
- Do not require a heavy scheduler. The first version can reuse existing background job status in `sync_tasks`.
- Do not add paid provider crawling unless the admin explicitly enables it.

## Verification

Backend:

- focused unittest for overview aggregation and normalized candidate queue
- route table contains `/api/admin/web-enrichment/overview` and `/api/admin/web-enrichment/candidates`

Frontend:

- static test confirms route, sidebar entry, API helpers, page sections, policy controls, candidate tabs, and no fake metrics
- `npm run build`
- existing `adminCrawlerEnrichment.test.mjs`

Browser:

- open `/admin/web-enrichment` with mocked admin state if auth blocks direct local access
- confirm command header, strategy controls, candidate tabs, and low-risk bulk action render
- confirm no overlapping text at desktop width

## Acceptance Criteria

- Admin sidebar has a dedicated `全网更新` entry.
- `/admin/web-enrichment` loads as an independent admin subpage.
- Page exposes policy controls for scope, targets, sources, batch size, max total, and throttle.
- Page can start, stop, refresh, and trial-run existing crawler jobs.
- Overview metrics come from backend aggregation.
- Candidate review section can display image, profile, food POI, hiking POI, and nearby POI candidates.
- Low-risk batch approval is available and clearly labeled.
- Paid providers are off by default.
- Unsupported actions show disabled/unavailable states.
- Build and focused tests pass.
