#!/usr/bin/env bash
set -euo pipefail

node --input-type=module - <<'NODE'
const baseUrl = process.env.SCENIC_ONLINE_API_BASE_URL || 'http://127.0.0.1:8000'
const checks = [
  ['/api/health'],
  ['/api/scenic'],
  ['/api/scenic/1'],
  ['/api/scenic/1/nearby'],
  ['/api/regions/provinces'],
  ['/api/weather', { city: '杭州' }],
  ['/api/community/posts'],
  ['/api/earth-online/sources'],
  ['/api/layouts/home'],
  ['/api/admin/layouts/home'],
  ['/api/user/workbench-layout'],
  ['/api/admin/dashboard'],
  ['/api/admin/database/status'],
  ['/api/admin/services/status'],
  ['/api/admin/enrichment/overview'],
  ['/api/admin/earth-online/sources'],
]

async function sleep(ms) {
  await new Promise(resolve => setTimeout(resolve, ms))
}

async function request(path, query = {}) {
  const url = new URL(path, baseUrl)
  Object.entries(query).forEach(([key, value]) => url.searchParams.set(key, value))
  let lastError
  for (let attempt = 1; attempt <= 5; attempt += 1) {
    try {
      const response = await fetch(url)
      const text = await response.text()
      let payload
      try {
        payload = JSON.parse(text)
      } catch {
        throw new Error(`invalid JSON: ${text.slice(0, 120)}`)
      }
      if (!response.ok || payload.success !== true) {
        throw new Error(`HTTP ${response.status} success=${payload.success} message=${payload.message || ''}`)
      }
      console.log(`OK ${path}`)
      return
    } catch (error) {
      lastError = error
      await sleep(400)
    }
  }
  throw new Error(`${path} failed: ${lastError?.message || 'unknown error'}`)
}

for (const [path, query] of checks) {
  await request(path, query)
}
NODE
