import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const destinations = fs.readFileSync(path.resolve('src/pages/DestinationsPage.jsx'), 'utf8')
const scenicDetail = fs.readFileSync(path.resolve('src/pages/ScenicDetailPage.jsx'), 'utf8')

assert.equal(destinations.includes("activeTab === 'themes'"), false)
assert.equal(destinations.includes('主题旅行</button>'), false)
assert.match(destinations, /normalizeTab = \(value\) => \(value === 'provinces' \|\| value === 'scenic'\) \? value : 'scenic'/)

assert.match(scenicDetail, /media_assets/)
assert.match(scenicDetail, /image_policy/)
assert.match(scenicDetail, /本地只保存 URL、来源、授权和质量分/)
assert.match(scenicDetail, /onError=\{setFallbackImage\}/)
