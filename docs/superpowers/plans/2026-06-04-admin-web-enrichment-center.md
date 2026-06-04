# Admin Web Enrichment Center Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independent `/admin/web-enrichment` page for whole-web scenic updates, candidate review, and low-risk batch approval.

**Architecture:** Add a small backend service that aggregates crawler status and normalizes candidates from existing candidate tables. Add two admin endpoints, frontend API helpers, a lazy admin route, sidebar/topbar entries, and a restrained operations-console page that reuses existing crawler start/stop/batch/approve endpoints.

**Tech Stack:** FastAPI-style routers, existing SQLite/PostgreSQL DB helpers, Python unittest, React 18, React Router, lucide-react, existing CSS files, Node static tests, Vite build.

---

## File Structure

- Create `backend/app/services/admin_web_enrichment_service.py`: overview aggregation and normalized candidate queue.
- Modify `backend/app/routers/admin_enrichment.py`: expose `/admin/web-enrichment/overview` and `/admin/web-enrichment/candidates`.
- Create `backend/tests/test_admin_web_enrichment_unittest.py`: service-level tests with a temporary SQLite database.
- Modify `frontend/src/api/admin.js`: web enrichment API helpers.
- Create `frontend/src/pages/admin/AdminWebEnrichmentPage.jsx`: independent admin subpage.
- Modify `frontend/src/router.jsx`: lazy route for `/admin/web-enrichment`.
- Modify `frontend/src/components/admin/AdminSidebar.jsx`: sidebar entry.
- Modify `frontend/src/components/admin/AdminTopbar.jsx`: title and command palette entry.
- Modify `frontend/src/styles/pages.css`: page layout and component styling.
- Create `frontend/tests/adminWebEnrichmentPage.test.mjs`: static integration test.

## Task 1: Backend Tests

**Files:**
- Create: `backend/tests/test_admin_web_enrichment_unittest.py`

- [ ] **Step 1: Write failing tests**

Write tests that initialize a temporary DB, seed `scenic_spots`, `scenic_profile_candidates`, `scenic_image_candidates`, and `sync_tasks`, then assert:

- `web_enrichment_overview()` returns missing counts and candidate counts.
- `web_enrichment_candidates(type="food")` returns normalized food POI candidate rows.
- `web_enrichment_candidates(type="image", risk="low")` returns normalized image candidate rows.

- [ ] **Step 2: Run tests and verify RED**

Run: `SCENIC_DATABASE_BACKEND=sqlite PYTHONPATH=backend backend/.venv/bin/python -m unittest backend.tests.test_admin_web_enrichment_unittest -v`

Expected: FAIL because `app.services.admin_web_enrichment_service` does not exist.

## Task 2: Backend Service And Routes

**Files:**
- Create: `backend/app/services/admin_web_enrichment_service.py`
- Modify: `backend/app/routers/admin_enrichment.py`

- [ ] **Step 1: Implement service**

Implement:

- `web_enrichment_overview()`
- `web_enrichment_candidates(candidate_type="all", risk="all", status="pending", province="", city="", limit=50)`

Use existing DB helpers. Do not crawl in these functions.

- [ ] **Step 2: Add routes**

Add:

- `GET /admin/web-enrichment/overview`
- `GET /admin/web-enrichment/candidates`

- [ ] **Step 3: Run backend tests**

Run: `SCENIC_DATABASE_BACKEND=sqlite PYTHONPATH=backend backend/.venv/bin/python -m unittest backend.tests.test_admin_web_enrichment_unittest -v`

Expected: PASS.

## Task 3: Frontend Static Test

**Files:**
- Create: `frontend/tests/adminWebEnrichmentPage.test.mjs`

- [ ] **Step 1: Write failing static test**

Assert:

- route imports and maps `AdminWebEnrichmentPage`
- sidebar includes `全网更新` and `/admin/web-enrichment`
- topbar title includes `全网更新中心`
- API helpers exist
- page includes policy controls, candidate tabs, low-risk bulk approval, start/stop/refresh/trial actions, and no `Math.random`

- [ ] **Step 2: Run frontend test and verify RED**

Run from `frontend`: `node tests/adminWebEnrichmentPage.test.mjs`

Expected: FAIL because page/API/route do not exist.

## Task 4: Frontend API, Route, Nav

**Files:**
- Modify: `frontend/src/api/admin.js`
- Modify: `frontend/src/router.jsx`
- Modify: `frontend/src/components/admin/AdminSidebar.jsx`
- Modify: `frontend/src/components/admin/AdminTopbar.jsx`

- [ ] **Step 1: Add API helpers**

Add helpers for overview, candidate queue, crawler batch/start/stop/status reuse, and low-risk approval.

- [ ] **Step 2: Add route and navigation**

Add lazy route `/admin/web-enrichment`, sidebar item, topbar title, and command palette item.

## Task 5: Frontend Page And Styles

**Files:**
- Create: `frontend/src/pages/admin/AdminWebEnrichmentPage.jsx`
- Modify: `frontend/src/styles/pages.css`

- [ ] **Step 1: Build page**

Create page sections:

- command header
- strategy panel
- metrics strip
- candidate review tabs
- job timeline

Use real API state. Use `--` when unavailable. Paid providers are off by default.

- [ ] **Step 2: Add styles**

Add admin web enrichment classes with restrained, dense control-room styling and responsive behavior.

## Task 6: Verification

**Files:**
- Test: backend and frontend focused tests

- [ ] **Step 1: Run backend focused test**

Run: `SCENIC_DATABASE_BACKEND=sqlite PYTHONPATH=backend backend/.venv/bin/python -m unittest backend.tests.test_admin_web_enrichment_unittest -v`

Expected: PASS.

- [ ] **Step 2: Run frontend focused tests**

Run from `frontend`:

- `node tests/adminWebEnrichmentPage.test.mjs`
- `node tests/adminCrawlerEnrichment.test.mjs`

Expected: PASS.

- [ ] **Step 3: Build frontend**

Run from `frontend`: `npm run build`

Expected: PASS.

- [ ] **Step 4: Browser smoke**

Run a Playwright smoke with mocked admin auth/API if needed and assert `/admin/web-enrichment` renders command header, policy controls, tabs, and low-risk action.
