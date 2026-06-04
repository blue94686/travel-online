# Admin Crawler Enrichment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a backend-managed crawler completion workflow that writes external descriptions, image links, nearby food POI, and hiking POI into a reviewable candidate pool, then lets admins batch-approve low-risk image and POI candidates while improving admin data presentation.

**Architecture:** Add a focused crawler enrichment service that reuses existing public-source fetchers, scenic candidate tables, image candidate tables, and sync task status storage. Expose the service through admin enrichment routes, then render a compact crawler control panel in the existing admin data/enrichment page with polling and low-risk approval actions.

**Tech Stack:** FastAPI, SQLite/Postgres adapter, Python unittest, React/Vite, lucide-react, Node assert-based frontend tests.

---

## File Structure

- Create `backend/app/services/scenic_crawler_enrichment_service.py`
  Owns crawler batch selection, candidate creation, low-risk approval, task process lifecycle, status aggregation, POI normalization, and JSON merge helpers.
- Modify `backend/app/routers/admin_enrichment.py`
  Adds five admin endpoints under `/admin/enrichment/crawler/*`.
- Modify `frontend/src/api/admin.js`
  Adds API wrappers for crawler status, batch, start, stop, and low-risk approval.
- Modify `frontend/src/pages/admin/AdminDataPage.jsx`
  Adds crawler state, polling, crawler actions, and a compact data presentation for enrichment metrics.
- Create `backend/tests/test_scenic_crawler_enrichment_unittest.py`
  Covers candidate insertion, low-risk approval, JSON merge dedupe, and status stats.
- Create `frontend/tests/adminCrawlerEnrichment.test.mjs`
  Static test for page/API wiring, visible admin labels, polling, and no random metrics.

## Task 1: Backend Service Tests

**Files:**
- Create: `backend/tests/test_scenic_crawler_enrichment_unittest.py`
- Read: `backend/tests/test_scenic_external_enrichment_unittest.py`
- Read: `backend/app/core/database.py`

- [ ] **Step 1: Write the failing backend unit tests**

```python
import json
import sqlite3
import unittest
from contextlib import contextmanager
from unittest.mock import patch

from app.core.database import SCHEMA, migrate_db
from app.services import scenic_crawler_enrichment_service as crawler


class ScenicCrawlerEnrichmentTest(unittest.TestCase):
    def make_db(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA)
        migrate_db(conn)
        conn.execute(
            """
            INSERT INTO scenic_spots (
              id, slug, name, province, city, district, level, rating, address,
              latitude, longitude, summary, description, tags, cover_image_url,
              gallery, nearby_food, nearby_pois, recommended_routes
            ) VALUES (
              1, 'test-mountain', '测试山景区', '浙江省', '杭州市', '西湖区',
              '4A', 4.6, '浙江省杭州市西湖区', 30.24, 120.14, '', '',
              '["山岳"]', '', '[]', '[]', '[]', '[]'
            )
            """
        )
        return conn

    def run_with_db(self, callback):
        conn = self.make_db()

        @contextmanager
        def fake_db():
            yield conn
            conn.commit()

        try:
            with patch.object(crawler, "get_db", fake_db):
                return callback(conn)
        finally:
            conn.close()

    def test_batch_writes_profile_image_food_and_hiking_candidates(self):
        def fake_public_bundle(scenic, include_osm=True):
            return (
                [
                    {
                        "scenic_id": scenic["id"],
                        "candidate_type": "summary",
                        "title": "测试山景区介绍",
                        "content": "测试山景区是适合轻徒步和城市近郊观景的山岳型景区。",
                        "source_url": "https://zh.wikipedia.org/wiki/test",
                        "source_name": "维基百科",
                        "source_type": "wikipedia",
                        "confidence": 82,
                        "risk_level": "medium",
                    }
                ],
                [
                    {
                        "scenic_id": scenic["id"],
                        "image_url": "https://img.example.test/mountain.jpg",
                        "thumbnail_url": "https://img.example.test/mountain-thumb.jpg",
                        "source_url": "https://commons.wikimedia.org/wiki/File:test.jpg",
                        "source_name": "Wikimedia Commons",
                        "source_type": "wikimedia_commons",
                        "license": "CC BY-SA",
                        "attribution": "Tester",
                        "provider": "wikimedia_commons",
                        "risk_level": "low",
                        "confidence": 88,
                        "title": "测试山景区",
                    }
                ],
                [],
            )

        def fake_pois(scenic, include_food=True, include_hiking=True, include_paid_providers=False):
            return [
                {
                    "type": "nearby_food",
                    "name": "测试山脚面馆",
                    "address": "景区入口旁",
                    "distance_text": "约 0.8 km",
                    "source_url": "https://map.example.test/food",
                    "source_name": "高德 POI",
                    "risk_level": "low",
                    "confidence": 76,
                },
                {
                    "type": "hiking_poi",
                    "name": "测试山观景步道",
                    "address": "景区北侧",
                    "distance_text": "约 1.2 km",
                    "source_url": "https://www.openstreetmap.org/way/1",
                    "source_name": "OpenStreetMap",
                    "risk_level": "low",
                    "confidence": 81,
                },
            ]

        def assertions(conn):
            with patch.object(crawler, "public_source_bundle_detailed", fake_public_bundle), patch.object(crawler, "_collect_poi_candidates", fake_pois):
                result = crawler.run_crawler_batch(limit=1, include_pois=True)

            self.assertEqual(result["read"], 1)
            self.assertEqual(result["profileCandidates"], 3)
            self.assertEqual(result["imageCandidates"], 1)
            self.assertEqual(result["lowRiskCandidates"], 3)

            profile_types = [
                row["candidate_type"]
                for row in conn.execute("SELECT candidate_type FROM scenic_profile_candidates ORDER BY id").fetchall()
            ]
            self.assertEqual(profile_types, ["summary", "nearby_food", "hiking_poi"])

            image = conn.execute("SELECT image_url, risk_level FROM scenic_image_candidates").fetchone()
            self.assertEqual(image["image_url"], "https://img.example.test/mountain.jpg")
            self.assertEqual(image["risk_level"], "low")

        self.run_with_db(assertions)

    def test_approve_low_risk_merges_image_food_and_hiking_without_duplicates(self):
        def assertions(conn):
            conn.execute(
                """
                INSERT INTO scenic_image_candidates (
                  id, scenic_id, image_url, thumbnail_url, source_url, source_name,
                  source_type, license, attribution, provider, risk_level, status,
                  review_status, confidence
                ) VALUES (
                  10, 1, 'https://img.example.test/mountain.jpg', '', 'https://commons.test/file',
                  'Commons', 'wikimedia_commons', 'CC BY', 'Tester', 'commons',
                  'low', 'pending', 'pending', 88
                )
                """
            )
            food = [{"name": "测试山脚面馆", "address": "景区入口旁", "source": "高德 POI"}]
            hiking = [{"name": "测试山观景步道", "address": "景区北侧", "source": "OpenStreetMap"}]
            for idx, (kind, payload) in enumerate((("nearby_food", food), ("hiking_poi", hiking)), start=20):
                conn.execute(
                    """
                    INSERT INTO scenic_profile_candidates (
                      id, scenic_id, candidate_type, title, content, source_url,
                      source_name, source_type, confidence, risk_level, status
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?)
                    """,
                    (
                        idx,
                        1,
                        kind,
                        kind,
                        json.dumps(payload, ensure_ascii=False),
                        "https://source.test",
                        "source",
                        "crawler_poi",
                        80,
                        "low",
                        "pending",
                    ),
                )

            result = crawler.approve_low_risk_candidates(limit=10)
            self.assertEqual(result["approvedImages"], 1)
            self.assertEqual(result["approvedPois"], 2)

            scenic = conn.execute("SELECT cover_image_url, nearby_food, nearby_pois, recommended_routes FROM scenic_spots WHERE id=1").fetchone()
            self.assertEqual(scenic["cover_image_url"], "https://img.example.test/mountain.jpg")
            self.assertEqual(json.loads(scenic["nearby_food"])[0]["name"], "测试山脚面馆")
            self.assertEqual(json.loads(scenic["nearby_pois"])[0]["name"], "测试山观景步道")
            self.assertIn("测试山观景步道", json.loads(scenic["recommended_routes"])[0])

            self.assertEqual(conn.execute("SELECT status FROM scenic_image_candidates WHERE id=10").fetchone()["status"], "approved")
            self.assertEqual(conn.execute("SELECT status FROM scenic_profile_candidates WHERE id=20").fetchone()["status"], "merged")

        self.run_with_db(assertions)

    def test_status_reports_missing_images_and_low_risk_candidates(self):
        def assertions(conn):
            conn.execute(
                "INSERT INTO scenic_image_candidates (scenic_id, image_url, risk_level, status, review_status) VALUES (1, 'https://img.test/a.jpg', 'low', 'pending', 'pending')"
            )
            conn.execute(
                """
                INSERT INTO scenic_profile_candidates (
                  scenic_id, candidate_type, title, content, source_url, source_type,
                  risk_level, status
                ) VALUES (
                  1, 'nearby_food', '美食', '[{"name":"店"}]', 'https://source.test',
                  'crawler_poi', 'low', 'pending'
                )
                """
            )

            status = crawler.crawler_status()
            self.assertEqual(status["stats"]["missingImages"], 1)
            self.assertEqual(status["stats"]["pendingProfileCandidates"], 1)
            self.assertEqual(status["stats"]["pendingImageCandidates"], 1)
            self.assertEqual(status["stats"]["lowRiskCandidates"], 2)

        self.run_with_db(assertions)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `PYTHONPATH=backend python3 -m unittest backend.tests.test_scenic_crawler_enrichment_unittest -v`

Expected: FAIL with `ImportError` because `scenic_crawler_enrichment_service` does not exist.

## Task 2: Backend Crawler Service

**Files:**
- Create: `backend/app/services/scenic_crawler_enrichment_service.py`
- Read: `backend/app/services/scenic_external_enrichment_service.py`
- Read: `backend/app/services/scenic_content_merge_service.py`
- Read: `backend/app/services/tpt_media_job_service.py`

- [ ] **Step 1: Implement the service public API**

Create `backend/app/services/scenic_crawler_enrichment_service.py` with these public functions and helpers:

```python
import json
import subprocess
import sys
import threading
import time
from datetime import datetime

from app.core.database import get_db, row_to_dict, rows_to_list
from app.services.audit_service import write_audit
from app.services.provider_config_service import get_secret
from app.services.scenic_external_enrichment_service import public_source_bundle_detailed, public_sources_blocked_seconds


JOB_NAME = "scenic_crawler_enrichment"
_lock = threading.Lock()
_process: subprocess.Popen | None = None
_stop_requested = False


def run_crawler_batch(limit: int = 10, province: str = "", city: str = "", only_missing: bool = True, include_public_sources: bool = True, include_pois: bool = True, include_paid_providers: bool = False, include_osm: bool = True, sleep_seconds: float = 0.8) -> dict:
    return {"read": 0, "searched": 0, "profileCandidates": 0, "imageCandidates": 0, "lowRiskCandidates": 0, "failures": [], "providerFailures": []}


def start_crawler_job(batch_size: int = 5, max_total: int = 2528, province: str = "", city: str = "", only_missing: bool = True, include_public_sources: bool = True, include_pois: bool = True, include_paid_providers: bool = False, include_osm: bool = True, sleep_seconds: float = 1.5) -> dict:
    payload = {"batchSize": batch_size, "maxTotal": max_total, "province": province, "city": city, "onlyMissing": only_missing, "includePublicSources": include_public_sources, "includePois": include_pois, "includePaidProviders": include_paid_providers, "includeOsm": include_osm, "sleepSeconds": sleep_seconds}
    return {"name": JOB_NAME, "status": "idle", "running": False, "payload": payload}


def stop_crawler_job() -> dict:
    return {"name": JOB_NAME, "status": "stopping", "running": False}


def crawler_status() -> dict:
    return {"name": JOB_NAME, "status": "idle", "running": False, "stats": {}}


def approve_low_risk_candidates(limit: int = 200) -> dict:
    return {"approvedImages": 0, "approvedPois": 0, "skipped": 0}
```

Implementation notes:

- Replace the stub returns above with the complete implementation before running the test.
- Use `sync_tasks.name = JOB_NAME` and JSON payload in `message`, matching `tpt_media_job_service`.
- Insert profile POI candidates into `scenic_profile_candidates` with `candidate_type` `nearby_food`, `hiking_poi`, or `nearby_poi`.
- Insert image candidates into `scenic_image_candidates`.
- For dedupe, use `INSERT OR IGNORE` for SQLite-compatible unique constraints where available and catch duplicate exceptions for Postgres adapter compatibility if needed.
- Use `_json_list`, `_merge_items`, `_candidate_content_list`, `_image_exists`, `_write_task`, `_parse_payload`, `_now`, `_risk_for_poi`, and `_collect_poi_candidates` as private helpers.
- `_collect_poi_candidates` may return rule-based non-merchant placeholders only for hiking routes; do not fabricate restaurant names when no map provider is configured.

- [ ] **Step 2: Run backend service tests**

Run: `PYTHONPATH=backend python3 -m unittest backend.tests.test_scenic_crawler_enrichment_unittest -v`

Expected: PASS.

## Task 3: Crawler Worker Entrypoint

**Files:**
- Create: `backend/app/scripts/scenic_crawler_worker.py`
- Modify: `backend/app/services/scenic_crawler_enrichment_service.py`
- Test: `backend/tests/test_scenic_crawler_enrichment_unittest.py`

- [ ] **Step 1: Add worker entrypoint**

Create `backend/app/scripts/scenic_crawler_worker.py`:

```python
import json
import sys

from app.services.scenic_crawler_enrichment_service import _run_job


def main():
    payload = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    _run_job(payload)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Wire process spawn in service**

In `_start_worker_process`, use:

```python
args = [sys.executable, "-m", "app.scripts.scenic_crawler_worker", json.dumps(payload, ensure_ascii=False)]
_process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
```

- [ ] **Step 3: Run the focused backend tests**

Run: `PYTHONPATH=backend python3 -m unittest backend.tests.test_scenic_crawler_enrichment_unittest -v`

Expected: PASS.

## Task 4: Admin Enrichment Routes

**Files:**
- Modify: `backend/app/routers/admin_enrichment.py`
- Test: `backend/tests/test_scenic_crawler_enrichment_unittest.py`

- [ ] **Step 1: Import the service functions**

Add:

```python
from app.services.scenic_crawler_enrichment_service import (
    approve_low_risk_candidates,
    crawler_status,
    run_crawler_batch,
    start_crawler_job,
    stop_crawler_job,
)
```

- [ ] **Step 2: Add endpoints**

Add these route functions near the existing TPT media job endpoints:

```python
@router.post("/admin/enrichment/crawler/batch")
def crawler_batch(
    limit: int = Query(10, ge=1, le=100),
    province: str | None = None,
    city: str | None = None,
    only_missing: bool = True,
    include_public_sources: bool = True,
    include_pois: bool = True,
    include_paid_providers: bool = False,
    include_osm: bool = True,
    sleep_seconds: float = Query(0.8, ge=0, le=3),
):
    return ok(
        run_crawler_batch(
            limit=limit,
            province=province or "",
            city=city or "",
            only_missing=only_missing,
            include_public_sources=include_public_sources,
            include_pois=include_pois,
            include_paid_providers=include_paid_providers,
            include_osm=include_osm,
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
    include_public_sources: bool = True,
    include_pois: bool = True,
    include_paid_providers: bool = False,
    include_osm: bool = True,
    sleep_seconds: float = Query(1.5, ge=0.5, le=5),
):
    return ok(
        start_crawler_job(
            batch_size=batch_size,
            max_total=max_total,
            province=province or "",
            city=city or "",
            only_missing=only_missing,
            include_public_sources=include_public_sources,
            include_pois=include_pois,
            include_paid_providers=include_paid_providers,
            include_osm=include_osm,
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
def crawler_approve_low_risk(limit: int = Query(200, ge=1, le=1000)):
    return ok(approve_low_risk_candidates(limit=limit), "低风险图片和 POI 候选已批量通过")
```

- [ ] **Step 3: Run import-focused tests**

Run: `PYTHONPATH=backend python3 -m unittest backend.tests.test_scenic_crawler_enrichment_unittest -v`

Expected: PASS.

## Task 5: Frontend API Wrappers

**Files:**
- Modify: `frontend/src/api/admin.js`
- Test: `frontend/tests/adminCrawlerEnrichment.test.mjs`

- [ ] **Step 1: Add URLSearchParams helper if absent**

Add a local helper near the enrichment functions:

```javascript
const toQuery = (extra = {}) => {
  const query = new URLSearchParams()
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  return query.toString()
}
```

- [ ] **Step 2: Add crawler API wrappers**

Add:

```javascript
export const runCrawlerEnrichmentBatch = (extra = {}) => {
  const query = toQuery(extra)
  return request(`/api/admin/enrichment/crawler/batch${query ? `?${query}` : ''}`, { method: 'POST' }, null)
}
export const startCrawlerEnrichmentJob = (extra = {}) => {
  const query = toQuery(extra)
  return request(`/api/admin/enrichment/crawler/start${query ? `?${query}` : ''}`, { method: 'POST' }, null)
}
export const getCrawlerEnrichmentStatus = () => request('/api/admin/enrichment/crawler/status', {}, null)
export const stopCrawlerEnrichmentJob = () => request('/api/admin/enrichment/crawler/stop', { method: 'POST' }, null)
export const approveLowRiskCrawlerCandidates = (extra = {}) => {
  const query = toQuery(extra)
  return request(`/api/admin/enrichment/crawler/approve-low-risk${query ? `?${query}` : ''}`, { method: 'POST' }, null)
}
```

- [ ] **Step 3: Run a static API smoke check**

Run: `node frontend/tests/adminCrawlerEnrichment.test.mjs`

Expected: initially FAIL until Task 6 creates the test and page wiring; after Task 6, PASS.

## Task 6: Backend Admin Page UI and Data Presentation

**Files:**
- Modify: `frontend/src/pages/admin/AdminDataPage.jsx`
- Test: `frontend/tests/adminCrawlerEnrichment.test.mjs`

- [ ] **Step 1: Write the frontend static test**

Create `frontend/tests/adminCrawlerEnrichment.test.mjs`:

```javascript
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const page = fs.readFileSync(path.resolve('src/pages/admin/AdminDataPage.jsx'), 'utf8')
const api = fs.readFileSync(path.resolve('src/api/admin.js'), 'utf8')

assert.match(api, /getCrawlerEnrichmentStatus/)
assert.match(api, /startCrawlerEnrichmentJob/)
assert.match(api, /approveLowRiskCrawlerCandidates/)
assert.match(page, /爬虫补全/)
assert.match(page, /剩余缺图/)
assert.match(page, /低风险可通过/)
assert.match(page, /批量通过低风险/)
assert.match(page, /setInterval/)
assert.match(page, /getCrawlerEnrichmentStatus/)
assert.equal(page.includes('Math.random'), false, 'admin crawler metrics must come from API state')
```

- [ ] **Step 2: Import API functions and icons**

Extend the imports in `AdminDataPage.jsx`:

```javascript
import { CheckCircle2, TimerReset } from 'lucide-react'
import {
  approveLowRiskCrawlerCandidates,
  getCrawlerEnrichmentStatus,
  runCrawlerEnrichmentBatch,
  startCrawlerEnrichmentJob,
  stopCrawlerEnrichmentJob,
} from '../../api/admin.js'
```

Keep existing imports and merge icons into the existing lucide import instead of duplicating import statements.

- [ ] **Step 3: Add crawler state and polling**

Inside `AdminDataPage`, add:

```javascript
const [crawlerStatus, setCrawlerStatus] = useState(null)
const [crawlerRunning, setCrawlerRunning] = useState('')

const refreshCrawler = async () => {
  const status = await getCrawlerEnrichmentStatus()
  setCrawlerStatus(status || null)
  return status
}

useEffect(() => {
  refreshCrawler().catch(() => {})
}, [])

useEffect(() => {
  if (!crawlerStatus?.running) return undefined
  const timer = setInterval(() => {
    refreshCrawler().catch(() => {})
  }, 5000)
  return () => clearInterval(timer)
}, [crawlerStatus?.running])
```

- [ ] **Step 4: Add crawler actions to `runAutomation`**

Inside `runAutomation`, add cases:

```javascript
if (type === 'crawler-batch') {
  setCrawlerRunning('batch')
  setNotice('正在试跑一批爬虫补全：候选默认进入审核池。')
  const result = await runCrawlerEnrichmentBatch({ limit: 5, include_pois: true, include_public_sources: true, include_osm: true })
  setExternalResult(result)
  await refreshCrawler()
  setCrawlerRunning('')
  setNotice(`试跑完成：资料候选 ${result?.profileCandidates || 0} 条，图片候选 ${result?.imageCandidates || 0} 条，低风险 ${result?.lowRiskCandidates || 0} 条。`)
}
if (type === 'crawler-start') {
  setCrawlerRunning('start')
  setNotice('已启动爬虫补全慢任务：默认进入候选池，低风险图片和 POI 可批量通过。')
  await startCrawlerEnrichmentJob({ batch_size: 5, max_total: 2528, include_pois: true, include_public_sources: true, include_osm: true, sleep_seconds: 1.5 })
  await refreshCrawler()
  setCrawlerRunning('')
}
if (type === 'crawler-stop') {
  setNotice('正在请求停止爬虫补全任务。')
  await stopCrawlerEnrichmentJob()
  await refreshCrawler()
  setNotice('已发送停止请求，当前批次完成后会停止。')
}
if (type === 'crawler-refresh') {
  const status = await refreshCrawler()
  setNotice(`爬虫补全状态：${status?.status || 'idle'}。`)
}
if (type === 'crawler-approve-low-risk') {
  setCrawlerRunning('approve')
  setNotice('正在批量通过低风险图片外链和 POI 候选。')
  const result = await approveLowRiskCrawlerCandidates({ limit: 200 })
  await refreshCrawler()
  setCrawlerRunning('')
  setNotice(`批量通过完成：图片 ${result?.approvedImages || 0} 条，POI ${result?.approvedPois || 0} 条，跳过 ${result?.skipped || 0} 条。`)
}
```

- [ ] **Step 5: Render compact crawler card**

Add a new `<article className="admin-panel">` inside the enrichment status grid with:

```jsx
<h3>爬虫补全</h3>
<span>剩余缺图</span>
<strong>{crawlerStatus?.stats?.missingImages ?? tptStats?.missing_cover ?? 0}</strong>
<span>候选总数</span>
<strong>{crawlerStatus?.stats?.pendingCandidates ?? 0}</strong>
<span>低风险可通过</span>
<strong>{crawlerStatus?.stats?.lowRiskCandidates ?? 0}</strong>
<button onClick={() => runAutomation('crawler-start')}>开始慢速补全</button>
<button onClick={() => runAutomation('crawler-batch')}>试跑一批</button>
<button onClick={() => runAutomation('crawler-refresh')}>刷新</button>
<button onClick={() => runAutomation('crawler-stop')}>停止</button>
<button onClick={() => runAutomation('crawler-approve-low-risk')}>批量通过低风险</button>
```

Use existing button classes, status badges, and inline grid patterns already present in the file. Keep text compact and avoid marketing-style explanatory blocks.

- [ ] **Step 6: Run frontend static test**

Run: `cd frontend && node tests/adminCrawlerEnrichment.test.mjs`

Expected: PASS.

## Task 7: Route Smoke and Regression Tests

**Files:**
- Test existing backend and frontend tests.

- [ ] **Step 1: Run backend focused tests**

Run:

```bash
PYTHONPATH=backend python3 -m unittest \
  backend.tests.test_scenic_crawler_enrichment_unittest \
  backend.tests.test_scenic_external_enrichment_unittest \
  backend.tests.test_scenic_media_pipeline_unittest \
  backend.tests.test_admin_dashboard_unittest -v
```

Expected: PASS.

- [ ] **Step 2: Run frontend tests**

Run:

```bash
cd frontend && node tests/adminCrawlerEnrichment.test.mjs && node tests/adminOperationsPage.test.mjs && node tests/adminBackendUi.test.mjs
```

Expected: PASS.

- [ ] **Step 3: Run API smoke if local dependencies are ready**

Run: `./scripts/api_smoke.sh`

Expected: PASS. If the command cannot start because dependencies are missing, record the exact failure in the final response.

## Task 8: Final Review

**Files:**
- Review: `backend/app/services/scenic_crawler_enrichment_service.py`
- Review: `backend/app/routers/admin_enrichment.py`
- Review: `frontend/src/pages/admin/AdminDataPage.jsx`
- Review: `frontend/src/api/admin.js`

- [ ] **Step 1: Inspect git diff**

Run: `git diff -- backend/app/services/scenic_crawler_enrichment_service.py backend/app/routers/admin_enrichment.py frontend/src/pages/admin/AdminDataPage.jsx frontend/src/api/admin.js backend/tests/test_scenic_crawler_enrichment_unittest.py frontend/tests/adminCrawlerEnrichment.test.mjs`

Expected: Diff only includes crawler enrichment, admin UI data presentation, and tests.

- [ ] **Step 2: Check for placeholders**

Run: `rg "pass #|NotImplemented" backend/app/services/scenic_crawler_enrichment_service.py frontend/src/pages/admin/AdminDataPage.jsx backend/tests/test_scenic_crawler_enrichment_unittest.py`

Expected: no placeholder matches.

- [ ] **Step 3: Summarize**

Final response should include:

- Backend crawler endpoints added.
- Candidate-pool behavior and low-risk batch approval behavior.
- Admin data presentation changes.
- Tests run and any tests not run.
