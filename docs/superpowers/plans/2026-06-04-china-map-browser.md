# China Map Browser Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an interactive China province map browser to "探索中国" and connect it to existing province, city, and scenic data.

**Architecture:** Build a focused `ChinaProvinceMap` React component that renders a lightweight province grid-map, exposes province selection via buttons, and delegates modal data loading to `DestinationsPage`. Keep the existing grouped province list as a fallback and use existing APIs: `/api/regions/provinces`, `/api/regions/cities`, and `/api/scenic`.

**Tech Stack:** React 18, React Router, existing CSS in `frontend/src/styles/pages.css`, existing scenic API helpers, Node static tests, Vite build.

---

## File Structure

- Create `frontend/src/components/common/ChinaProvinceMap.jsx`: presentation-only map component with keyboard-accessible province buttons and count-density styling.
- Modify `frontend/src/pages/DestinationsPage.jsx`: load province map data, handle province selection, fetch modal details, render modal, and keep list fallback.
- Modify `frontend/src/styles/pages.css`: add restrained map panel, province button, modal, metric, scenic preview, and responsive styles.
- Create `frontend/tests/chinaProvinceMap.test.mjs`: static regression test for component existence, destination integration, modal copy, existing APIs, and no heavy map package.

## Task 1: Add Static Test

**Files:**
- Create: `frontend/tests/chinaProvinceMap.test.mjs`

- [ ] **Step 1: Write the failing test**

```js
import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const componentPath = path.resolve(root, 'src/components/common/ChinaProvinceMap.jsx')
const destinationsPath = path.resolve(root, 'src/pages/DestinationsPage.jsx')
const packagePath = path.resolve(root, 'package.json')

assert.equal(fs.existsSync(componentPath), true, 'ChinaProvinceMap component should exist')

const component = fs.readFileSync(componentPath, 'utf8')
const destinations = fs.readFileSync(destinationsPath, 'utf8')
const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'))

assert.match(component, /export default function ChinaProvinceMap/)
assert.match(component, /aria-label="中国省区地图浏览"/)
assert.match(component, /onProvinceSelect/)
assert.match(component, /province-map-button/)
assert.match(component, /data-density/)

assert.match(destinations, /ChinaProvinceMap/)
assert.match(destinations, /getRegionCities/)
assert.match(destinations, /getSyncedScenicList/)
assert.match(destinations, /province-map-modal/)
assert.match(destinations, /代表景区/)
assert.match(destinations, /进入省份详情/)
assert.match(destinations, /三级浏览/)

const deps = { ...pkg.dependencies, ...pkg.devDependencies }
assert.equal(Boolean(deps['echarts']), false, 'first pass should not add heavy map packages')
assert.equal(Boolean(deps['@amap/amap-jsapi-loader']), false, 'province browser should not depend on map SDK loading')
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `node tests/chinaProvinceMap.test.mjs`

Expected: FAIL because `src/components/common/ChinaProvinceMap.jsx` does not exist.

## Task 2: Build Map Component

**Files:**
- Create: `frontend/src/components/common/ChinaProvinceMap.jsx`

- [ ] **Step 1: Implement the component**

Create a component that:

- accepts `groups`, `selectedProvince`, and `onProvinceSelect`,
- flattens grouped province API data,
- renders positioned province buttons in a lightweight map-like panel,
- calculates density from `scenic_count`,
- supports keyboard and mobile because every province is a real button.

- [ ] **Step 2: Run the static test**

Run: `node tests/chinaProvinceMap.test.mjs`

Expected: FAIL because `DestinationsPage.jsx` does not import or use the component yet.

## Task 3: Integrate Map And Modal

**Files:**
- Modify: `frontend/src/pages/DestinationsPage.jsx`

- [ ] **Step 1: Wire imports and state**

Import `X`, `ArrowRight`, `MapPinned`, `Building2`, and `Sparkles` from `lucide-react`, import `getRegionCities`, and import `ChinaProvinceMap`.

Add state for:

- `selectedProvince`
- `provinceCities`
- `provinceScenic`
- `provinceModalLoading`

- [ ] **Step 2: Add province selection handler**

When a province is selected:

- set the selected province,
- fetch cities with `getRegionCities(province)`,
- fetch representative scenic items with `getSyncedScenicList(?province=...&limit=8&offset=0)`,
- keep modal open even if scenic fetch fails, using empty states.

- [ ] **Step 3: Render map browser**

In the `activeTab === 'provinces'` branch:

- render `ChinaProvinceMap` before the grouped list,
- pass `provincesData`, `selectedProvince?.province`, and `handleProvinceSelect`,
- replace list button navigation with modal selection.

- [ ] **Step 4: Render modal**

Render a modal when `selectedProvince` exists. The modal should show:

- province name,
- scenic count,
- city count,
- representative scenic cards,
- city chips,
- buttons for `进入省份详情`, `三级浏览`, and close.

- [ ] **Step 5: Run the static test**

Run: `node tests/chinaProvinceMap.test.mjs`

Expected: PASS for integration assertions.

## Task 4: Style Map And Modal

**Files:**
- Modify: `frontend/src/styles/pages.css`

- [ ] **Step 1: Add styles**

Add classes for:

- `.china-map-browser`
- `.china-map-shell`
- `.china-province-map`
- `.province-map-button`
- `.province-map-modal-backdrop`
- `.province-map-modal`
- `.province-map-metrics`
- `.province-map-scenic-grid`
- `.province-map-city-row`

The design should be clean and restrained: white surface, teal outlines, soft region fills, readable labels, no decorative orb backgrounds.

- [ ] **Step 2: Add responsive styles**

At mobile widths:

- province buttons become easier to tap,
- map panel remains horizontally usable,
- modal occupies most viewport width and scrolls internally.

## Task 5: Verify

**Files:**
- Test: `frontend/tests/chinaProvinceMap.test.mjs`
- Build: frontend Vite build

- [ ] **Step 1: Run focused test**

Run from `frontend`: `node tests/chinaProvinceMap.test.mjs`

Expected: PASS.

- [ ] **Step 2: Run existing focused crawler/admin UI test**

Run from `frontend`: `node tests/adminCrawlerEnrichment.test.mjs`

Expected: PASS, confirming previous crawler UI wiring remains present.

- [ ] **Step 3: Build frontend**

Run from `frontend`: `npm run build`

Expected: Vite build succeeds.

- [ ] **Step 4: Document any unrelated failures**

If older static tests still assert stale copy/classes from previous UI, do not rewrite unrelated behavior unless the changed files require it. Report those failures separately.
