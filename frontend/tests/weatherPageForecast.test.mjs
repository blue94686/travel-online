import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const baseUrl = process.env.SCENIC_ONLINE_PAGE_BASE_URL || 'http://127.0.0.1:5174'

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } })

await page.goto(`${baseUrl}/trip-planning?tab=weather&city=${encodeURIComponent('苏州市')}`, { waitUntil: 'networkidle' })
await page.waitForSelector('.weather-forecast-strip b', { timeout: 10000 })

const labels = await page.$$eval('.weather-forecast-strip b', nodes => nodes.map(node => node.textContent.trim()))
await browser.close()

assert.ok(labels.length > 0)
assert.equal(labels.some(label => /^-/.test(label)), false, `forecast labels should not start with a negative value: ${labels.join(', ')}`)
