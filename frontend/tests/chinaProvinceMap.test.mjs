import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'

const root = process.cwd()
const componentPath = path.resolve(root, 'src/components/common/ChinaProvinceMap.jsx')
const destinationsPath = path.resolve(root, 'src/pages/DestinationsPage.jsx')
const packagePath = path.resolve(root, 'package.json')

assert.equal(fs.existsSync(componentPath), true, 'ChinaProvinceMap component should exist')

const component = fs.readFileSync(componentPath, 'utf8')
const destinations = fs.readFileSync(destinationsPath, 'utf8')
const pkg = JSON.parse(fs.readFileSync(packagePath, 'utf8'))

assert.match(component, /export default function ChinaProvinceMap/)
assert.match(component, /aria-label="中国省区地图浏览"/)
assert.match(component, /onProvinceSelect/)
assert.match(component, /province-map-button/)
assert.match(component, /data-density/)

assert.match(destinations, /ChinaProvinceMap/)
assert.match(destinations, /getRegionCities/)
assert.match(destinations, /getSyncedScenicList/)
assert.match(destinations, /province-map-modal/)
assert.match(destinations, /代表景区/)
assert.match(destinations, /进入省份详情/)
assert.match(destinations, /三级浏览/)

const deps = { ...pkg.dependencies, ...pkg.devDependencies }
assert.equal(Boolean(deps.echarts), false, 'first pass should not add heavy map packages')
assert.equal(Boolean(deps['@amap/amap-jsapi-loader']), false, 'province browser should not depend on map SDK loading')
