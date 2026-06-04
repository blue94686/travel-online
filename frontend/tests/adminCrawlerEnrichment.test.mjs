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
