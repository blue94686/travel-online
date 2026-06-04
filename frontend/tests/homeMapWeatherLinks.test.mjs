import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const homeSource = fs.readFileSync(path.resolve('src/pages/HomePage.jsx'), 'utf8')
const weatherSource = fs.readFileSync(path.resolve('src/components/common/WeatherCard.jsx'), 'utf8')
const mapSource = fs.readFileSync(path.resolve('src/components/common/MapPanel.jsx'), 'utf8')

assert.match(homeSource, /<WeatherCard[\s\S]*to=\{`\/trip-planning\?tab=weather&city=/)
assert.match(homeSource, /<MapPanel[\s\S]*actionTo=\{`\/trip-planning\?tab=map&from=/)
assert.match(weatherSource, /<Link className="tool-card weather-card-link" to=\{to\}>/)
assert.match(mapSource, /OpenStreetMap 真实地图/)
assert.match(mapSource, /osm-map-frame/)
assert.match(mapSource, /buildSatellitePreviewUrl/)
assert.match(mapSource, /satellite-map-frame/)
assert.match(mapSource, /map-card-cover/)
assert.match(mapSource, /map-open-link/)
