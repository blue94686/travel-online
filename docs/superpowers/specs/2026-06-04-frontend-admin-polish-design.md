# Frontend And Admin Polish Design

Date: 2026-06-04

## Goal

Optimize the travel site's public frontend and admin console into a cleaner, more restrained, easier-to-manage product experience.

The existing site already has a usable teal travel identity, public pages, and a richer admin crawler/enrichment workflow. This work should preserve that base while improving visual hierarchy, information density, data trust, and day-to-day management ergonomics.

## Audience

- Public users browsing scenic areas, searching destinations, comparing nearby food and hiking information, and opening detail pages.
- Admin users managing scenic data, image completion, crawler candidates, POI enrichment, automation, database health, and system operations.

## Design Direction

The direction is a restrained travel operations product:

- Public frontend: calm, readable, image-led, with concise copy and less decorative noise.
- Admin console: dense but organized, status-first, action-oriented, and reliable-looking.
- Shared style: keep the current teal/cyan brand family, white surfaces, light borders, soft shadows, and Chinese-first typography.
- Avoid heavy marketing sections, exaggerated gradients, emoji-led cards, oversized copy in compact surfaces, nested cards, and fake-looking operational numbers.

## Current Style Reading

The current visual system is based on:

- `frontend/src/styles/tokens.css`: teal/cyan primary colors, soft white backgrounds, rounded surfaces, admin tokens, and elevation variables.
- `frontend/src/styles/global.css`: light travel-themed body background, panel/card primitives, buttons, chips, forms, tables, and responsive defaults.
- `frontend/src/styles/layout.css`: site navigation, admin shell, sidebar, topbar, KPI grids, panels, and responsive admin layout.
- `frontend/src/styles/pages.css`: public page-specific layouts for home, search, destinations, scenic detail, weather, orders, products, maps, guides, and other surfaces.

The codebase favors CSS classes and React page components instead of a heavy component library. The implementation should continue that pattern.

## Scope

### Global Polish

- Add or normalize missing semantic tokens used by pages, including soft background/text aliases where needed.
- Tighten spacing, card radius, border, shadow, and text scale for operational interfaces.
- Keep public pages airy, but reduce decorative gradients that make repeated content feel busy.
- Ensure button text, chips, tabs, and toolbar controls fit across desktop and mobile.
- Preserve existing route structure and API contracts unless a small UI-only adapter is needed.

### Public Frontend

#### Home

- Keep the home page as the first public experience, not a landing-page detour.
- Make the hero cleaner and more useful: clearer search entry, concise trust/status hints, and restrained supporting copy.
- Replace emoji-heavy or strongly gradient theme cards with quieter cards that still communicate outdoor, family, culture, food, and seasonal travel themes.
- Improve featured scenic cards, guide previews, province browsing, weather/tools, and inspiration sections for faster scanning.

#### Search

- Make search results feel like a practical travel discovery tool:
  - clearer result count and active filters,
  - cleaner tabs,
  - better empty/loading states,
  - easier comparison of scenic, food, hiking, and guide items.
- Keep query suggestions and recent searches visible without making the page feel cluttered.

#### Destinations

- Improve the filter/sidebar/list relationship so users can quickly browse provinces and scenic areas.
- Make active tabs and selected filters visually obvious.
- Keep scenic cards compact enough for comparison while preserving image and key metadata.

#### Scenic Detail

- Refine the detail hero, facts grid, tabbed content, nearby POI, food, hiking, weather, and guide surfaces.
- Make crawler-provided content provenance visible where the UI already exposes data quality/source concepts.
- Keep side panels and action areas functional on mobile without overlap.

### Admin Console

#### Shell

- Keep the existing sidebar/topbar structure, but make it more like an operations console:
  - clearer section grouping,
  - less visual weight in the sidebar,
  - concise topbar titles/actions,
  - consistent page headers and action clusters.
- Preserve existing navigation routes and role expectations.

#### Operations Dashboard

- Replace static, fake-looking operational metrics with live or clearly labeled fallback data already available to the frontend.
- Organize the page around:
  - pending work,
  - crawler/enrichment progress,
  - data health,
  - recent actions,
  - system checks.
- Use compact status tiles and tables instead of large decorative dashboard cards.

#### Data And Enrichment

- Make crawler completion a first-class management workflow:
  - manual start/stop/status,
  - image completion progress,
  - scenic introduction enrichment,
  - nearby food POI,
  - hiking POI,
  - candidate pool defaults,
  - one-click batch approval for image links and low-risk POI.
- Surface candidate risk, source, confidence, and review status clearly.
- Make bulk actions easy to find but visually separate from destructive actions.

#### Automation, System, And Database

- Tighten automation task cards into more scannable task rows or compact cards.
- Make system health, service state, logs, and maintenance actions consistent with the admin visual language.
- Improve tables with clearer empty states, status badges, and primary/secondary actions.

## Data Presentation Rules

- Do not invent operational numbers. If a value is not backed by an API response, show a neutral empty, loading, or unavailable state.
- Prefer counts, timestamps, state labels, and source labels that map to actual backend fields.
- Candidate pool items should default to review state unless explicitly auto-approved by low-risk rules.
- Image external links and low-risk POI may be batch-approved from admin, but the UI must still show what was approved.
- High-risk or low-confidence items remain manual review items.

## Components And Files

Likely files to touch during implementation:

- `frontend/src/styles/tokens.css`
- `frontend/src/styles/global.css`
- `frontend/src/styles/layout.css`
- `frontend/src/styles/pages.css`
- `frontend/src/components/admin/AdminLayout.jsx`
- `frontend/src/components/admin/AdminSidebar.jsx`
- `frontend/src/components/admin/AdminTopbar.jsx`
- `frontend/src/pages/HomePage.jsx`
- `frontend/src/pages/SearchPage.jsx`
- `frontend/src/pages/DestinationsPage.jsx`
- `frontend/src/pages/ScenicDetailPage.jsx`
- `frontend/src/pages/admin/AdminOperationsPage.jsx`
- `frontend/src/pages/admin/AdminDataPage.jsx`
- `frontend/src/pages/admin/AdminAutomationPage.jsx`
- `frontend/src/pages/admin/AdminSystemPage.jsx`

Small shared components may be added only if they remove real duplication, such as an admin page header, metric strip, status tile, or review queue row.

## Non-Goals

- Do not replace the frontend stack or introduce a new UI library.
- Do not redesign the brand from scratch.
- Do not add a marketing landing page.
- Do not add decorative orb/bokeh backgrounds.
- Do not make the admin interface illustration-heavy.
- Do not change backend crawler semantics unless a UI bug exposes a missing field that must be handled.

## Accessibility And Responsiveness

- Maintain readable contrast for text, badges, buttons, and table rows.
- Keep tap targets usable on mobile.
- Avoid text overflow in chips, buttons, cards, sidebar labels, and tables.
- Ensure admin pages remain usable with collapsed sidebar and narrow viewport widths.
- Use responsive grid constraints for cards, metric tiles, and toolbars so content does not cause layout jumps.

## Verification Plan

Implementation should be verified with:

- `npm run build`
- focused frontend tests affected by changed pages/components
- existing crawler/admin enrichment frontend test
- a local browser pass on public pages and admin pages across desktop and mobile widths when a dev server is available

If existing tests assert old copy or class names that are intentionally improved, update those tests to assert behavior and stable user-facing outcomes instead.

## Acceptance Criteria

- Public frontend feels cleaner, calmer, and easier to scan without losing the current travel identity.
- Admin console presents data in a more complete and management-friendly way.
- Crawler completion, candidate pool, image links, low-risk POI, food POI, and hiking POI are discoverable from admin workflows.
- Admin bulk approval actions are clear, reversible only where existing backend behavior supports it, and separated from risky actions.
- No fake operational numbers remain in polished admin views unless explicitly labeled as examples.
- Mobile and desktop layouts do not overlap or overflow in the optimized surfaces.
- Build and focused tests pass, or any unrelated existing failures are documented clearly.
