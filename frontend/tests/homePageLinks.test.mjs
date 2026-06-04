import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const homeSource = fs.readFileSync(path.resolve('src/pages/HomePage.jsx'), 'utf8')
const routerSource = fs.readFileSync(path.resolve('src/router.jsx'), 'utf8')
const rankingsSource = fs.readFileSync(path.resolve('src/pages/RankingsPage.jsx'), 'utf8')
const guideSource = fs.readFileSync(path.resolve('src/pages/GuideDetailPage.jsx'), 'utf8')

assert.match(homeSource, /to="\/rankings"[^>]*>探索热门榜单/)
assert.match(homeSource, /to="\/trip-planning\?tab=map"[^>]*>定制专属行程/)
assert.match(homeSource, /to=\{`\/guides\/\$\{article\.id\}`\}/)
assert.equal(homeSource.includes('<button className="primary-btn">探索热门榜单</button>'), false)
assert.equal(homeSource.includes('<button className="ghost-btn">定制专属行程</button>'), false)
assert.match(routerSource, /path: 'rankings'/)
assert.match(routerSource, /path: 'guides\/:id'/)
assert.match(rankingsSource, /热门榜单/)
assert.match(guideSource, /getArticle/)
assert.match(rankingsSource, /榜单说明/)
assert.match(rankingsSource, /季节限定/)
assert.match(rankingsSource, /热门搜索/)
assert.match(guideSource, /出发前清单/)
assert.match(guideSource, /指南摘要/)
assert.match(homeSource, /data\?\.groups[\s\S]*Object\.values\(data\.groups\)\.flat\(\)[\s\S]*data\?\.items/)
assert.match(rankingsSource, /data\?\.groups[\s\S]*Object\.values\(data\.groups\)\.flat\(\)[\s\S]*data\?\.items/)
