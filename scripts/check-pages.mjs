import fs from 'node:fs/promises'
import path from 'node:path'
import { createRequire } from 'node:module'

const requireFromCwd = createRequire(path.join(process.cwd(), 'package.json'))
const baseUrl = process.env.SCENIC_ONLINE_PAGE_BASE_URL || 'http://127.0.0.1:5173'
const apiUrl = process.env.SCENIC_ONLINE_API_BASE_URL || 'http://127.0.0.1:8000'
const screenshotDir = process.env.SCENIC_ONLINE_SCREENSHOT_DIR || '/private/tmp/scenic-online-page-check-screenshots'
const pages = [
  '/', '/scenic', '/scenic/1', '/scenic/jingdian-1', '/themes', '/rankings', '/guides/1', '/map', '/weather', '/community',
  '/earth-online', '/provinces', '/user', '/auth', '/search', '/sources', '/trip-planning', '/destinations',
  '/admin', '/admin/scenic',
  '/admin/images', '/admin/comments', '/admin/users', '/admin/data', '/admin/data/source', '/admin/data/quality', '/admin/api',
  '/admin/services', '/admin/earth-online', '/admin/enrichment', '/admin/workbench',
  '/admin/roles', '/admin/security', '/admin/settings', '/admin/logs'
]
const allowedRedirects = new Map([
  ['/map', '/trip-planning'],
  ['/weather', '/trip-planning'],
])

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

function authForRoute(route, adminAuth, userAuth) {
  if (route.startsWith('/admin')) return adminAuth
  if (route === '/user') return userAuth
  return null
}

function expectedPath(route) {
  return allowedRedirects.get(route) || route
}

function isWrongPage(route, finalUrl, text) {
  const pathName = new URL(finalUrl).pathname
  const expected = expectedPath(route)
  if (route.startsWith('/admin') && pathName === '/auth') return true
  if (!pathName.startsWith(expected)) return true
  return /页面未找到|找不到页面|Not Found/i.test(text)
}

function isExternalOptional(resourceUrl) {
  try {
    const host = new URL(resourceUrl).hostname
    return [
      'images.unsplash.com',
      'upload.wikimedia.org',
      'commons.wikimedia.org',
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

async function checkWithFetch() {
  const results = []
  for (const page of pages) {
    const url = `${baseUrl}${page}`
    try {
      const response = await fetch(url)
      const html = await response.text()
      results.push({
        page,
        accessible: response.ok,
        nonEmpty: html.trim().length > 200,
        hasButtons: /<button|role="button"|primary-btn/.test(html),
        errors: response.ok ? [] : [`HTTP ${response.status}`],
        screenshot: ''
      })
    } catch (error) {
      results.push({ page, accessible: false, nonEmpty: false, hasButtons: false, errors: [error.message], screenshot: '' })
    }
  }
  return results
}

async function checkWithPlaywright() {
  const { chromium } = requireFromCwd('playwright')
  const [adminAuth, userAuth] = await Promise.all([
    login('superadmin@scenic.local', 'SuperAdmin123456'),
    login('user@scenic.local', 'User123456'),
  ])
  await fs.mkdir(screenshotDir, { recursive: true })
  const browser = await chromium.launch()
  const results = []
  for (const route of pages) {
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } })
    const auth = authForRoute(route, adminAuth, userAuth)
    if (auth) {
      await context.addInitScript(({ token, user }) => {
        localStorage.setItem('scenic-token', token)
        localStorage.setItem('scenic-user', JSON.stringify(user))
        localStorage.setItem('scenic-role', user.role)
        localStorage.setItem('scenic-user-email', user.email)
      }, auth)
    }
    const page = await context.newPage()
    const url = `${baseUrl}${route}`
    const errors = []
    const badResponses = []
    page.on('console', message => {
      if (message.type() === 'error' && !isOptionalConsoleError(message.text())) errors.push(message.text())
    })
    page.on('response', response => {
      const status = response.status()
      const resourceUrl = response.url()
      if (status >= 400 && !resourceUrl.includes('/favicon') && !isExternalOptional(resourceUrl)) badResponses.push(`${status} ${resourceUrl}`)
    })
    page.on('requestfailed', request => {
      if (!isExternalOptional(request.url())) badResponses.push(`failed ${request.url()} ${request.failure()?.errorText || ''}`)
    })
    const response = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 15000 }).catch(error => {
      errors.push(error.message)
      return null
    })
    await page.waitForLoadState('load', { timeout: 5000 }).catch(() => {})
    await page.waitForTimeout(600)
    const bodyText = await page.locator('body').innerText().then(text => text.trim()).catch(() => '')
    const textLength = bodyText.length
    const buttons = await page.locator('button, a.primary-btn, [role="button"]').count().catch(() => 0)
    const file = path.join(screenshotDir, `${route === '/' ? 'home' : route.replaceAll('/', '_').replace(/^_/, '')}.png`)
    if (response?.ok()) await page.screenshot({ path: file, fullPage: true })
    const wrongPage = response?.ok() ? isWrongPage(route, page.url(), bodyText) : false
    results.push({
      page: route,
      accessible: Boolean(response?.ok()),
      nonEmpty: textLength > 40,
      hasButtons: buttons > 0,
      finalUrl: page.url(),
      errors: [...errors, ...badResponses, ...(wrongPage ? [`wrong page: ${page.url()}`] : [])],
      screenshot: response?.ok() ? file : ''
    })
    await context.close()
  }
  await browser.close()
  return results
}

let results
try {
  results = await checkWithPlaywright()
} catch (error) {
  results = await checkWithFetch()
  results.unshift({ page: '__runner__', accessible: true, nonEmpty: true, hasButtons: false, errors: [`Playwright unavailable: ${error.message}`], screenshot: '' })
}

const invalid = results.filter(item => !item.accessible || !item.nonEmpty || item.errors.length)
console.table(results.map(({ page, accessible, nonEmpty, hasButtons, errors, screenshot }) => ({
  page,
  accessible,
  nonEmpty,
  hasButtons,
  errors: errors.length,
  screenshot
})))
if (invalid.length) {
  console.error(JSON.stringify({ invalid }, null, 2))
  process.exitCode = 1
}
