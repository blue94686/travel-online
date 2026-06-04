import assert from 'node:assert/strict'
import { createWeatherInsights } from '../src/utils/weatherInsights.js'

const rainyHotWeather = {
  current: {
    temp: 34,
    feelsLike: 38,
    humidity: '88%',
    wind: '东北风 5级',
    air: '轻度污染 112',
    condition: '雷阵雨',
  },
  travelAdvice: ['带伞出行，山地和石阶线路注意防滑。'],
}

const tough = createWeatherInsights(rainyHotWeather, [])
assert.equal(tough.indexes.length, 4)
assert.ok(tough.score < 70)
assert.ok(tough.alerts.some(item => item.includes('降雨')))
assert.ok(tough.alerts.some(item => item.includes('高温')))
assert.ok(tough.tips.some(item => item.includes('雨具')))

const mild = createWeatherInsights({
  current: {
    temp: 24,
    feelsLike: 25,
    humidity: '61%',
    wind: '东北风 2级',
    air: '优 34',
    condition: '多云',
  },
}, [])

assert.ok(mild.score >= 85)
assert.ok(mild.summary.includes('适合户外'))
assert.ok(mild.alerts.some(item => item.includes('暂无明显天气风险')))
