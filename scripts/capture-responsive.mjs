import fs from 'node:fs/promises'
import path from 'node:path'
import { createRequire } from 'node:module'

const requireFromCwd = createRequire(path.join(process.cwd(), 'package.json'))
const { chromium } = requireFromCwd('playwright')
const baseUrl = process.env.SCENIC_ONLINE_PAGE_BASE_URL || 'http://127.0.0.1:5173'
const apiUrl = process.env.SCENIC_ONLINE_API_BASE_URL || 'http://127.0.0.1:8000'
const outDir = process.env.SCENIC_ONLINE_SCREENSHOT_DIR || '/private/tmp/scenic-online-responsive-screenshots'
const shots = [
  ['home-desktop', '/', 1440, 1000],
  ['home-tablet', '/', 768, 1000],
  ['home-mobile', '/', 390, 900],
  ['scenic-desktop', '/scenic', 1440, 1000],
  ['scenic-henan-desktop', '/scenic?province=%E6%B2%B3%E5%8D%97%E7%9C%81', 1440, 1000],
  ['scenic-detail-desktop', '/scenic/1', 1440, 1000],
  ['themes-desktop', '/themes', 1440, 1000],
  ['map-desktop', '/map', 1440, 1000],
  ['map-to-westlake-desktop', '/map?to=%E6%9D%AD%E5%B7%9E%E8%A5%BF%E6%B9%96', 1440, 1000],
  ['map-mobile', '/map', 390, 950],
  ['weather-desktop', '/weather', 1440, 1000],
  ['community-desktop', '/community', 1440, 1000],
  ['provinces-desktop', '/provinces', 1440, 1000],
  ['provinces-henan-desktop', '/provinces?province=%E6%B2%B3%E5%8D%97%E7%9C%81', 1440, 1000],
  ['earth-desktop', '/earth-online', 1440, 1000],
  ['earth-mobile', '/earth-online', 390, 950],
  ['user-desktop', '/user', 1440, 1000],
  ['user-workbench', '/user', 1024, 1000],
  ['admin-dashboard', '/admin', 1440, 1000],
  ['admin-workbench', '/admin/workbench', 1440, 1000],
  ['admin-earth-online', '/admin/earth-online', 1440, 1000],
  ['admin-enrichment', '/admin/enrichment', 1440, 1000],
  ['admin-services', '/admin/services', 1440, 1000],
  ['admin-api', '/admin/api', 1440, 1000],
  ['admin-data-import', '/admin/data', 1440, 1000],
  ['admin-mobile', '/admin', 390, 950],
  ['admin-api-mobile', '/admin/api', 390, 950],
  ['destinations-mobile', '/destinations', 390, 950],
]

async function login(email, password) {
  const response = await fetch(`${apiUrl}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  const payload = await response.json()
  if (!response.ok || !payload.success) throw new Error(payload.message || `登录失败: ${email}`)
  return payload.data
}

function isExternalOptional(resourceUrl) {
  try {
    const host = new URL(resourceUrl).hostname
    return [
      'images.unsplash.com',
      'tile.openstreetmap.org',
      'server.arcgisonline.com',
      'services.arcgisonline.com',
      'www.openstreetmap.org',
    ].some(domain => host === domain || host.endsWith(`.${domain}`))
  } catch {
    return false
  }
}

function isOptionalConsoleError(text) {
  return /Failed to load resource: net::ERR_(CONNECTION_CLOSED|NAME_NOT_RESOLVED|TIMED_OUT)/.test(text)
}

await fs.mkdir(outDir, { recursive: true })
const [adminAuth, userAuth] = await Promise.all([
  login('superadmin@scenic.local', 'SuperAdmin123456'),
  login('user@scenic.local', 'User123456'),
])
const browser = await chromium.launch()
const results = []
for (const [name, route, width, height] of shots) {
  const context = await browser.newContext({ viewport: { width, height } })
  const auth = route.startsWith('/admin') ? adminAuth : route === '/user' ? userAuth : null
  if (auth) {
    await context.addInitScript(({ token, user }) => {
      localStorage.setItem('scenic-token', token)
      localStorage.setItem('scenic-user', JSON.stringify(user))
      localStorage.setItem('scenic-role', user.role)
      localStorage.setItem('scenic-user-email', user.email)
    }, auth)
  }
  const page = await context.newPage()
  const errors = []
  const badResponses = []
  page.on('console', message => {
    if (message.type() === 'error' && !isOptionalConsoleError(message.text())) errors.push(message.text())
  })
  page.on('response', response => {
    const status = response.status()
    if (status >= 400 && !response.url().includes('/favicon') && !isExternalOptional(response.url())) badResponses.push(`${status} ${response.url()}`)
  })
  page.on('requestfailed', request => {
    if (!isExternalOptional(request.url())) badResponses.push(`failed ${request.url()} ${request.failure()?.errorText || ''}`)
  })
  await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 15000 })
  await page.waitForTimeout(500)
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2)
  const file = path.join(outDir, `${name}.png`)
  await page.screenshot({ path: file, fullPage: true })
  results.push({ name, route, width, height, overflow, errors: errors.length + badResponses.length, file, details: [...errors, ...badResponses] })
  await context.close()
}
await browser.close()
console.table(results)
if (results.some(item => item.overflow || item.errors)) {
  console.error(JSON.stringify(results.filter(item => item.overflow || item.errors), null, 2))
  process.exitCode = 1
}
