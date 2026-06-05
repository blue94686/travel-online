import assert from 'node:assert/strict'

import { getScenicSourceLinks } from '../src/utils/scenicSourceLinks.js'

assert.deepEqual(getScenicSourceLinks(null), [])

const both = getScenicSourceLinks({
  official_website: 'https://www.example.gov.cn/scenic',
  source_url: 'https://uri.amap.com/marker?position=116,39&name=test',
})

assert.deepEqual(both.map(item => item.label), ['官方网站', '资料来源'])
assert.equal(both[0].url, 'https://www.example.gov.cn/scenic')
assert.equal(both[1].url, 'https://uri.amap.com/marker?position=116,39&name=test')

const sourceOnly = getScenicSourceLinks({
  official_website: '',
  source_url: 'https://zh.wikipedia.org/wiki/test',
})

assert.deepEqual(sourceOnly, [{
  label: '资料来源',
  text: '查看公开来源/地图入口',
  url: 'https://zh.wikipedia.org/wiki/test',
}])

const duplicated = getScenicSourceLinks({
  official_website: 'https://example.com/a',
  source_url: 'https://example.com/a',
})

assert.equal(duplicated.length, 1)
