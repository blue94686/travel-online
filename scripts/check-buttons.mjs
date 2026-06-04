import fs from 'node:fs/promises'
import path from 'node:path'
import { createRequire } from 'node:module'

const requireFromCwd = createRequire(path.join(process.cwd(), 'package.json'))
const baseUrl = process.env.SCENIC_ONLINE_PAGE_BASE_URL || 'http://localhost:5173'
const apiUrl = process.env.SCENIC_ONLINE_API_BASE_URL || 'http://127.0.0.1:8000'
const reportDir = process.env.SCENIC_ONLINE_BUTTON_REPORT_DIR || '/private/tmp/scenic-online-button-audit'

const pages = [
  '/',
  '/scenic',
  '/scenic/1',
  '/scenic/jingdian-1',
  '/themes',
  '/community',
  '/earth-online',
  '/trip-planning',
  '/destinations',
  '/admin',
  '/admin/content',
  '/admin/images',
  '/admin/comments',
  '/admin/data',
  '/admin/data/source',
  '/admin/data/quality',
  '/admin/scenic',
  '/admin/database',
  '/admin/enrichment',
  '/admin/layout',
  '/admin/automation',
  '/admin/integration',
  '/admin/api',
  '/admin/services',
  '/admin/earth-online',
  '/admin/system',
  '/admin/users',
  '/admin/roles',
  '/admin/security',
  '/admin/settings',
  '/admin/logs',
]

const skipPattern = /删除|驳回|下架|通过|封面|导入|发布|保存|重置|上传|提交|发送|注册|登录|退出|举报|拉黑|复制|导出|备份|完整性检查|批量|新增|编辑|创建|加入|收藏|点赞|分享|预览|打开设置/
const optionalHosts = [
  'images.unsplash.com',
  'upload.wikimedia.org',
  'commons.wikimedia.org',
  'tile.openstreetmap.org',
  'server.arcgisonline.com',
  'services.arcgisonline.com',
  'www.openstreetmap.org',
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

function isOptional(resourceUrl) {
  try {
    const host = new URL(resourceUrl).hostname
    return optionalHosts.some(domain => host === domain || host.endsWith(`.${domain}`))
  } catch {
    return false
  }
}

async function installAuth(context, route, adminAuth, userAuth) {
  const auth = route.startsWith('/admin') ? adminAuth : route === '/user' ? userAuth : null
  if (!auth) return
  await context.addInitScript(({ token, user }) => {
    localStorage.setItem('scenic-token', token)
    localStorage.setItem('scenic-user', JSON.stringify(user))
    localStorage.setItem('scenic-role', user.role)
    localStorage.setItem('scenic-user-email', user.email)
  }, auth)
}

function normalizeText(text) {
  return (text || '').replace(/\s+/g, ' ').trim()
}

function withTimeout(promise, ms, label) {
  let timer
  return Promise.race([
    promise.finally(() => clearTimeout(timer)),
    new Promise((_, reject) => {
      timer = setTimeout(() => reject(new Error(`${label} timeout after ${ms}ms`)), ms)
    }),
  ])
}

async function auditButton(locator, page, label) {
  const beforeUrl = page.url()
  const beforeText = normalizeText(await page.locator('body').innerText().catch(() => ''))
  let dialogSeen = false
  let networkSeen = false
  const onDialog = dialog => {
    dialogSeen = true
    dialog.dismiss().catch(() => {})
  }
  const onResponse = response => {
    if (response.status() < 500 && response.url().includes('/api/')) networkSeen = true
  }
  page.on('dialog', onDialog)
  page.on('response', onResponse)
  try {
    await withTimeout(locator.click({ timeout: 1800 }), 2500, `click ${label}`)
    await page.waitForTimeout(350)
  } catch (error) {
    page.off('dialog', onDialog)
    page.off('response', onResponse)
    return { label, ok: false, reason: `click failed: ${error.message}` }
  }
  page.off('dialog', onDialog)
  page.off('response', onResponse)
  const afterUrl = page.url()
  const afterText = normalizeText(await page.locator('body').innerText().catch(() => ''))
  const changed = beforeUrl !== afterUrl || beforeText !== afterText || dialogSeen || networkSeen
  return { label, ok: changed, reason: changed ? '' : 'clicked without visible, navigation, dialog, or network feedback' }
}

async function openRoute(page, route, errors) {
  try {
    await page.goto(`${baseUrl}${route}`, { waitUntil: 'domcontentloaded', timeout: 10000 })
  } catch (error) {
    await page.goto(`${baseUrl}${route}`, { waitUntil: 'commit', timeout: 8000 }).catch(commitError => {
      errors.push(`navigation failed: ${commitError.message}`)
    })
  }
  await page.waitForLoadState('load', { timeout: 3500 }).catch(() => {})
  const bodyText = await page.locator('body').innerText({ timeout: 1000 }).catch(() => '')
  if (bodyText.trim().length > 40) {
    const failedIndex = errors.findIndex(item => item.startsWith('navigation failed:'))
    if (failedIndex >= 0) errors.splice(failedIndex, 1)
  }
}

async function run() {
  const { chromium } = requireFromCwd('playwright')
  await fs.mkdir(reportDir, { recursive: true })
  const [adminAuth, userAuth] = await Promise.all([
    login('superadmin@scenic.local', 'SuperAdmin123456'),
    login('user@scenic.local', 'User123456'),
  ])
  const browser = await chromium.launch()
  const results = []

  for (const route of pages) {
    console.log(`[button-audit] ${route}`)
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } })
    await installAuth(context, route, adminAuth, userAuth)
    const page = await context.newPage()
    const routeErrors = []
    page.on('console', message => {
      if (message.type() === 'error') routeErrors.push(message.text())
    })
    page.on('response', response => {
      if (response.status() >= 500 && !isOptional(response.url())) routeErrors.push(`${response.status()} ${response.url()}`)
    })
    await openRoute(page, route, routeErrors)
    await page.waitForTimeout(700)

    const buttonCount = await page.locator('button, a.primary-btn, [role="button"]').count()
    const samples = []
    for (let index = 0; index < buttonCount && samples.length < 4; index += 1) {
      const locator = page.locator('button, a.primary-btn, [role="button"]').nth(index)
      if (!(await locator.isVisible().catch(() => false))) continue
      if (!(await locator.isEnabled().catch(() => false))) continue
      const className = await locator.getAttribute('class').catch(() => '') || ''
      const selected = await locator.getAttribute('aria-selected').catch(() => '') || ''
      const current = await locator.getAttribute('aria-current').catch(() => '') || ''
      if (className.includes('active') || selected === 'true' || current === 'page') continue
      const label = normalizeText(await locator.innerText().catch(() => '')) || await locator.getAttribute('aria-label') || await locator.getAttribute('title') || `button-${index + 1}`
      if (!label || skipPattern.test(label)) continue
      samples.push({ index, label })
    }

    const checks = []
    for (const sample of samples) {
      await openRoute(page, route, routeErrors)
      await page.waitForTimeout(250)
      const locator = page.locator('button, a.primary-btn, [role="button"]').nth(sample.index)
      checks.push(await withTimeout(auditButton(locator, page, sample.label), 3500, `${route} ${sample.label}`).catch(error => ({
        label: sample.label,
        ok: false,
        reason: error.message,
      })))
    }

    const file = path.join(reportDir, `${route === '/' ? 'home' : route.replaceAll('/', '_').replace(/^_/, '')}.png`)
    await page.screenshot({ path: file, fullPage: true }).catch(() => {})
    results.push({ route, sampled: checks.length, failures: checks.filter(item => !item.ok), errors: routeErrors, screenshot: file })
    await context.close()
  }

  await browser.close()
  await fs.writeFile(path.join(reportDir, 'button-report.json'), JSON.stringify(results, null, 2))
  console.table(results.map(item => ({
    route: item.route,
    sampled: item.sampled,
    failures: item.failures.length,
    errors: item.errors.length,
    screenshot: item.screenshot,
  })))
  const invalid = results.filter(item => item.failures.length || item.errors.length)
  if (invalid.length) {
    console.error(JSON.stringify({ invalid }, null, 2))
    process.exitCode = 1
  }
}

run().catch(error => {
  console.error(error)
  process.exitCode = 1
})
