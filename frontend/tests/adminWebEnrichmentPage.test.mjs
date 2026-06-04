import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const pagePath = path.resolve(root, 'src/pages/admin/AdminWebEnrichmentPage.jsx')
const apiPath = path.resolve(root, 'src/api/admin.js')
const routerPath = path.resolve(root, 'src/router.jsx')
const sidebarPath = path.resolve(root, 'src/components/admin/AdminSidebar.jsx')
const topbarPath = path.resolve(root, 'src/components/admin/AdminTopbar.jsx')
const stylesPath = path.resolve(root, 'src/styles/pages.css')

assert.equal(fs.existsSync(pagePath), true, 'AdminWebEnrichmentPage should exist')

const page = fs.readFileSync(pagePath, 'utf8')
const api = fs.readFileSync(apiPath, 'utf8')
const router = fs.readFileSync(routerPath, 'utf8')
const sidebar = fs.readFileSync(sidebarPath, 'utf8')
const topbar = fs.readFileSync(topbarPath, 'utf8')
const styles = fs.readFileSync(stylesPath, 'utf8')

assert.match(api, /getWebEnrichmentOverview/)
assert.match(api, /getWebEnrichmentCandidates/)
assert.match(api, /startCrawlerEnrichmentJob/)
assert.match(api, /approveLowRiskCrawlerCandidates/)

assert.match(router, /AdminWebEnrichmentPage/)
assert.match(router, /web-enrichment/)
assert.match(sidebar, /全网更新/)
assert.match(sidebar, /\/admin\/web-enrichment/)
assert.match(topbar, /全网更新中心/)

assert.match(page, /全网更新中心/)
assert.match(page, /策略配置/)
assert.match(page, /候选池/)
assert.match(page, /任务时间线/)
assert.match(page, /批量通过低风险/)
assert.match(page, /试跑一批/)
assert.match(page, /启动后台更新/)
assert.match(page, /停止任务/)
assert.match(page, /图片外链/)
assert.match(page, /景区介绍/)
assert.match(page, /周边美食/)
assert.match(page, /徒步 POI/)
assert.match(page, /include_paid_providers/)
assert.equal(page.includes('Math.random'), false, 'web enrichment page must not fake metrics')

assert.match(styles, /admin-web-enrichment-page/)
assert.match(styles, /web-enrichment-strategy/)
assert.match(styles, /web-candidate-card/)
