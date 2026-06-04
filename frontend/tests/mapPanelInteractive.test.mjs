import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const source = fs.readFileSync(path.resolve('src/components/common/MapPanel.jsx'), 'utf8')

assert.match(source, /InteractiveTileMap/)
assert.match(source, /server\.arcgisonline\.com\/ArcGIS\/rest\/services\/World_Imagery\/MapServer\/tile/)
assert.match(source, /tile\.openstreetmap\.org/)
assert.match(source, /aria-label="放大地图"/)
assert.match(source, /aria-label="缩小地图"/)
assert.match(source, /setFallbackZoom/)
assert.equal(source.includes('ArcGIS World Imagery 卫星影像'), true)
