# Frontend And Admin Polish Design

Date: 2026-06-04

## Goal

Optimize the travel site's public frontend and admin console into a cleaner, more restrained, easier-to-manage product experience.

The existing site already has a usable teal travel identity, public pages, and a richer admin crawler/enrichment workflow. This work should preserve that base while improving visual hierarchy, information density, data trust, and day-to-day management ergonomics.

This is not only a visual polish pass. It must also fill missing presentation and management surfaces so the product feels like a complete public travel site plus a real admin management platform.

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

### Management Platform Completion

The admin area already has many backend APIs and routes, but the UI currently presents some of them as scattered panels or incomplete views. The optimized admin platform should provide clear, discoverable management surfaces for:

- Scenic database management: list, search, filter, create, edit, delete, enrich, and inspect source fields.
- Image management: pending review, external image candidates, cover selection, copyright/source labels, approve/reject, and low-risk batch approval.
- Comment/community management: pending comments, hide/delete, IP blacklist, risk labels, and basic moderation history.
- Content operations: banners, articles/guides, publication state, frontpage placement, preview links, and draft/published separation.
- Data source management: `tpt_jingdian` source status, import preview, import progress, source row counts, and error/fallback states.
- Enrichment management: crawler status, manual batch run, slow background job, stop/refresh, candidate pool, scenic introduction candidates, nearby food POI, hiking POI, image candidates, confidence, risk, source, and one-click batch approval for low-risk items.
- Database workbench: table browsing, schema preview, SQL terminal, quick queries, export current view, database files, backup state, and safety hints.
- Page layout management: public page module order, visibility, component templates, draft preview, version history, publish, reset, and restore.
- API/service management: configured providers, key status, health check, latency/log views, and unavailable states.
- User/role/security management: user list, role update, status update, password reset where supported, role matrix, security logs, IP blacklist, and audit logs.
- System settings: site defaults, image policy, crawler/enrichment toggles, data sync policy, and admin-only operational switches where supported by existing endpoints.

The first implementation pass should prioritize completing the surfaces that already have API support. When a capability is not backed by an endpoint, the UI should show a clear unavailable state instead of pretending the action works.

### Global Polish

- Add or normalize missing semantic tokens used by pages, including soft background/text aliases where needed.
- Tighten spacing, card radius, border, shadow, and text scale for operational interfaces.
- Keep public pages airy, but reduce decorative gradients that make repeated content feel busy.
- Ensure button text, chips, tabs, and toolbar controls fit across desktop and mobile.
- Preserve existing route structure and API contracts unless a small UI-only adapter is needed.

### Public Frontend

The public frontend must expose the data that admin workflows manage. The pages should not only look calmer; they should better present scenic introductions, image coverage, nearby POI, food, hiking, data source quality, and useful travel actions.

#### Home

- Keep the home page as the first public experience, not a landing-page detour.
- Make the hero cleaner and more useful: clearer search entry, concise trust/status hints, and restrained supporting copy.
- Replace emoji-heavy or strongly gradient theme cards with quieter cards that still communicate outdoor, family, culture, food, and seasonal travel themes.
- Improve featured scenic cards, guide previews, province browsing, weather/tools, and inspiration sections for faster scanning.
- Surface curated scenic areas, themes, provinces, guides, and current weather/tools in a way that feels maintained by the admin platform.

#### Search

- Make search results feel like a practical travel discovery tool:
  - clearer result count and active filters,
  - cleaner tabs,
  - better empty/loading states,
  - easier comparison of scenic, food, hiking, and guide items.
- Keep query suggestions and recent searches visible without making the page feel cluttered.
- Show richer result metadata where available, including image availability, region, level, theme tags, and source confidence.

#### Destinations

- Improve the filter/sidebar/list relationship so users can quickly browse provinces and scenic areas.
- Make active tabs and selected filters visually obvious.
- Keep scenic cards compact enough for comparison while preserving image and key metadata.
- Add clearer province/city/district browsing states backed by the imported national source table.

#### Scenic Detail

- Refine the detail hero, facts grid, tabbed content, nearby POI, food, hiking, weather, and guide surfaces.
- Make crawler-provided content provenance visible where the UI already exposes data quality/source concepts.
- Keep side panels and action areas functional on mobile without overlap.
- Present enriched scenic introductions, external image links, nearby food, nearby attractions, hiking/trail suggestions, route/weather actions, and source/license labels when data exists.
- Use empty states that explain missing data without making the page feel broken.

#### Other Public Pages

- Rankings, themes, province detail, trip planning, Earth Online, sources, guides, and community pages should inherit the cleaner visual system.
- Do not fully rebuild every page in the first pass. Apply shared CSS and component improvements so secondary pages feel consistent.
- Prioritize pages that users hit most often: home, search, destinations, scenic detail, trip planning entry points, and guide/detail surfaces.

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
- Add an admin platform entry map so administrators can jump directly to missing images, crawler candidates, scenic records, content drafts, user/security work, and service checks.

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
- Provide separate visible sections for scenic introduction candidates, image candidates, food POI, hiking POI, and rejected/skipped candidates when the API can supply them.
- Make the remaining image completion workload visible, including the 2,528-image backlog concept as configurable/progress data rather than hardcoded decoration.

#### Scenic Library

- Turn the formal scenic database page into a management workspace, not only a database browser:
  - search and filter scenic records,
  - inspect key fields,
  - edit supported scenic fields,
  - create/delete records where supported,
  - run single-scenic enrichment,
  - open the public detail page,
  - show source/import/enrichment status.
- Keep the SQL/data table workbench available, but separate it from ordinary scenic content management.

#### Content And Review

- Make image review, comment review, banners, articles/guides, and frontpage recommendations feel like one content operations area.
- Add clearer tabs, queue counts, risk/source badges, bulk-friendly rows, and stable modal layouts.
- Separate public content publishing from moderation queues so administrators do not lose orientation.

#### Automation, System, And Database

- Tighten automation task cards into more scannable task rows or compact cards.
- Make system health, service state, logs, and maintenance actions consistent with the admin visual language.
- Improve tables with clearer empty states, status badges, and primary/secondary actions.
- Make users, roles, settings, security, logs, and services route-specific inside `AdminSystemPage` instead of looking like one generic system page.
- Keep dangerous operations visually quiet but clearly confirmed.

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
- `frontend/src/components/admin/AdminTable.jsx`
- `frontend/src/components/admin/AdminKpiCard.jsx`
- `frontend/src/pages/HomePage.jsx`
- `frontend/src/pages/SearchPage.jsx`
- `frontend/src/pages/DestinationsPage.jsx`
- `frontend/src/pages/ScenicDetailPage.jsx`
- `frontend/src/pages/admin/AdminOperationsPage.jsx`
- `frontend/src/pages/admin/AdminDataPage.jsx`
- `frontend/src/pages/admin/AdminAutomationPage.jsx`
- `frontend/src/pages/admin/AdminContentPage.jsx`
- `frontend/src/pages/admin/AdminDatabasePage.jsx`
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
- Public frontend shows enriched scenic introductions, image coverage, nearby food, hiking/trail information, and source labels when available.
- Admin console presents data in a more complete and management-friendly way.
- Admin console feels like a complete management platform, with clear entry points for scenic records, content, images, comments, enrichment, data source, database, layout, users, roles, security, services, logs, and settings.
- Crawler completion, candidate pool, image links, low-risk POI, food POI, and hiking POI are discoverable from admin workflows.
- Admin bulk approval actions are clear, reversible only where existing backend behavior supports it, and separated from risky actions.
- No fake operational numbers remain in polished admin views unless explicitly labeled as examples.
- Unsupported admin actions show unavailable states instead of fake success.
- Mobile and desktop layouts do not overlap or overflow in the optimized surfaces.
- Build and focused tests pass, or any unrelated existing failures are documented clearly.
