const apiBase = process.env.SCENIC_ONLINE_API_BASE_URL || 'http://127.0.0.1:8000'
const webBase = process.env.SCENIC_ONLINE_WEB_BASE_URL || 'http://127.0.0.1'

const apiChecks = [
  ['/api/health', data => data?.status === 'ok'],
  ['/api/regions/provinces', data => data?.groups && Object.keys(data.groups).length > 0],
  ['/api/regions/cities?province=云南省', data => Array.isArray(data) && data.includes('丽江市')],
  ['/api/regions/districts?province=云南省&city=丽江市', data => Array.isArray(data) && data.includes('古城区')],
  ['/api/scenic?limit=12', data => Array.isArray(data?.items) && data.items.length > 0 && Number(data.total) > 100000],
  ['/api/scenic?province=云南省&city=丽江市&district=古城区&limit=8', data => Array.isArray(data?.items) && data.items.some(item => item.source === 'jingdian')],
  ['/api/scenic/jingdian-1/profile', data => data?.id === 'jingdian-1' && data?.source === 'jingdian' && Boolean(data.address)],
  ['/api/scenic/themes', data => Array.isArray(data) && data.length > 0],
  ['/api/scenic/1/profile', data => Boolean(data?.source_url && data?.image_policy)],
  ['/api/scenic/2/nearby', data => Array.isArray(data)],
  ['/api/admin/enrichment/overview', data => Number.isFinite(Number(data?.totalScenic))],
  ['/api/admin/enrichment/profile/external-readiness', data => data?.storage_policy && data?.fallback_policy],
]

const pageChecks = [
  '/',
  '/destinations',
  '/scenic/1',
  '/themes',
  '/trip-planning',
  '/community',
  '/earth-online',
  '/admin',
]

async function fetchJson(path) {
  const response = await fetch(`${apiBase}${path}`)
  const text = await response.text()
  let payload
  try {
    payload = JSON.parse(text)
  } catch {
    throw new Error(`non-json response ${response.status}: ${text.slice(0, 120)}`)
  }
  if (!response.ok || payload.success === false) {
    throw new Error(payload.message || `HTTP ${response.status}`)
  }
  return payload.data
}

async function checkApi(path, predicate) {
  const data = await fetchJson(path)
  if (!predicate(data)) {
    throw new Error(`unexpected payload for ${path}`)
  }
  if (path.includes('/profile')) {
    const media = Array.isArray(data.media_assets) ? data.media_assets : []
    const hasPublicMedia = media.some(item => item.url?.startsWith('http') && !item.url.includes('images.unsplash.com'))
    if (hasPublicMedia && media.some(item => item.url?.includes('images.unsplash.com'))) {
      throw new Error(`profile mixes public media with demo images: ${path}`)
    }
  }
}

async function checkPage(path) {
  const response = await fetch(`${webBase}${path}`)
  if (response.status >= 500) {
    throw new Error(`page ${path} returned HTTP ${response.status}`)
  }
}

async function main() {
  const failures = []
  for (const [path, predicate] of apiChecks) {
    try {
      await checkApi(path, predicate)
      console.log(`OK api ${path}`)
    } catch (error) {
      const detail = error.cause?.message ? `${error.message}: ${error.cause.message}` : error.message
      failures.push(`API ${apiBase}${path}: ${detail}`)
      console.error(`FAIL api ${apiBase}${path}: ${detail}`)
    }
  }
  for (const path of pageChecks) {
    try {
      await checkPage(path)
      console.log(`OK page ${path}`)
    } catch (error) {
      const detail = error.cause?.message ? `${error.message}: ${error.cause.message}` : error.message
      failures.push(`PAGE ${webBase}${path}: ${detail}`)
      console.error(`FAIL page ${webBase}${path}: ${detail}`)
    }
  }
  if (failures.length) {
    console.error(`\n${failures.length} consistency checks failed`)
    process.exit(1)
  }
  console.log('\nAll data consistency checks passed')
}

main().catch(error => {
  console.error(error)
  process.exit(1)
})
