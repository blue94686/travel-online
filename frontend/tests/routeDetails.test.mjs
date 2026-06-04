import assert from 'node:assert/strict'
import { buildRouteMapModel, estimateRouteCosts } from '../src/utils/routeDetails.js'

const driving = estimateRouteCosts({ distance_km: 120, duration_minutes: 110 }, 'driving')
assert.deepEqual(driving.map(item => item.label), ['燃油/电耗', '过路停车', '机动预留'])
assert.ok(driving.every(item => item.value > 0))

const walking = estimateRouteCosts({ distance_km: 5, duration_minutes: 75 }, 'walking')
assert.equal(walking.find(item => item.label === '交通费用').value, 0)
assert.ok(walking.find(item => item.label === '补给预留').value > 0)

const mapModel = buildRouteMapModel([
  [120.1, 30.1],
  [120.3, 30.4],
  [120.7, 30.2],
], '苏州', '西湖')

assert.match(mapModel.path, /^M /)
assert.equal(mapModel.points[0].label, '苏州')
assert.equal(mapModel.points.at(-1).label, '西湖')
assert.ok(mapModel.points.length >= 3)
assert.ok(mapModel.points.every(point => point.x >= 48 && point.x <= 592))
