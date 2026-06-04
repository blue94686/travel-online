import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const source = fs.readFileSync(path.resolve('src/pages/TripPlanningPage.jsx'), 'utf8')

assert.equal(source.includes('出行助手'), false)
assert.equal(source.includes("handleTabChange('tools')"), false)
assert.match(source, /const VALID_TABS = new Set\(\['map', 'weather'\]\)/)
assert.match(source, /normalizeTab/)
assert.match(source, /createWeatherInsights/)
assert.match(source, /今日出行判断/)
assert.match(source, /weather-insight-grid/)
assert.match(source, /selectedRouteDetail/)
assert.match(source, /route-detail-overlay/)
assert.match(source, /费用预估/)
assert.match(source, /route-mini-map/)
