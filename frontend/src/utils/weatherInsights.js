function readNumber(value, fallback = 0) {
  const match = String(value ?? '').match(/-?\d+/)
  return match ? Number(match[0]) : fallback
}

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, Math.round(value)))
}

function includesAny(text, words) {
  return words.some(word => text.includes(word))
}

function airPenalty(air = '') {
  if (air.includes('重度') || air.includes('严重')) return 28
  if (air.includes('中度')) return 20
  if (air.includes('轻度')) return 13
  if (air.includes('良')) return 4
  return 0
}

function buildTips({ temp, condition, wind, humidity }) {
  const tips = []
  if (includesAny(condition, ['雨', '雷', '阵雨'])) tips.push('带雨具和防滑鞋，石阶、栈道、亲水区域放慢速度。')
  if (includesAny(condition, ['雪', '冰'])) tips.push('穿防滑保暖鞋，预留交通和排队缓冲时间。')
  if (temp >= 32) tips.push('准备防晒用品和补水，避开正午长距离徒步。')
  if (temp <= 5) tips.push('增加保暖层，山顶和临水区域体感更冷。')
  if (readNumber(wind, 0) >= 5) tips.push('减少高山、索道、游船等受风影响较大的项目。')
  if (readNumber(humidity, 0) >= 85) tips.push('空气湿度偏高，轻装慢行并注意衣物透气。')
  if (!tips.length) tips.push('轻便外套、充电宝和少量饮水即可，适合常规半日或一日游。')
  return tips
}

function buildAlerts({ temp, condition, wind, air }) {
  const alerts = []
  if (includesAny(condition, ['雨', '雷', '阵雨'])) alerts.push('有降雨或雷雨风险，户外线路注意防滑。')
  if (includesAny(condition, ['雪', '冰'])) alerts.push('低温冰雪天气，山路和台阶通行风险上升。')
  if (temp >= 32) alerts.push('高温时段体感偏热，注意防晒补水。')
  if (temp <= 5) alerts.push('低温天气，早晚和高海拔区域需保暖。')
  if (readNumber(wind, 0) >= 5) alerts.push('风力偏大，高空和水上项目建议谨慎。')
  if (airPenalty(air) >= 13) alerts.push('空气质量一般，减少高强度户外活动。')
  if (!alerts.length) alerts.push('暂无明显天气风险，按常规出行准备。')
  return alerts
}

export function createWeatherInsights(weather = {}, forecast = []) {
  const current = weather.current || weather || {}
  const temp = readNumber(current.temp, 24)
  const feelsLike = readNumber(current.feelsLike, temp)
  const humidity = current.humidity || '--'
  const wind = current.wind || '微风'
  const air = current.air || '--'
  const condition = current.condition || '多云'
  const rainy = includesAny(condition, ['雨', '雷', '阵雨'])
  const snowy = includesAny(condition, ['雪', '冰'])
  const windy = readNumber(wind, 0) >= 5
  const humid = readNumber(humidity, 0) >= 85

  let score = 92
  if (rainy) score -= 20
  if (snowy) score -= 18
  if (temp >= 32) score -= 15
  if (temp <= 5) score -= 12
  if (windy) score -= 10
  if (humid) score -= 5
  score -= airPenalty(air)
  score = clamp(score)

  const comfort = temp >= 32 ? '偏热' : temp <= 5 ? '偏冷' : humid ? '闷湿' : '舒适'
  const travel = score >= 85 ? '很适合' : score >= 70 ? '适合短线' : score >= 55 ? '谨慎安排' : '建议改期'
  const photo = rainy || snowy ? '弱光雨雪' : airPenalty(air) >= 13 ? '通透度一般' : includesAny(condition, ['晴', '云']) ? '适合拍摄' : '正常'
  const gear = rainy ? '雨具防滑' : temp >= 32 ? '防晒补水' : temp <= 5 ? '保暖防风' : '轻装出行'

  return {
    score,
    summary: score >= 85
      ? `${condition}，体感${feelsLike}°C，整体适合户外游览。`
      : `${condition}，体感${feelsLike}°C，建议按天气风险调整线路。`,
    indexes: [
      { key: 'travel', label: '出行指数', value: travel, detail: score >= 70 ? '可安排景区步行、观景和城市漫游。' : '优先短线、室内或低强度路线。' },
      { key: 'comfort', label: '舒适度', value: comfort, detail: `温度 ${temp}°C，湿度 ${humidity}。` },
      { key: 'photo', label: '摄影指数', value: photo, detail: airPenalty(air) >= 13 ? '远景通透度可能受影响。' : '适合拍摄风景、人像和城市街景。' },
      { key: 'gear', label: '装备建议', value: gear, detail: buildTips({ temp, condition, wind, humidity })[0] },
    ],
    tips: [...new Set([...(weather.travelAdvice || []), ...buildTips({ temp, condition, wind, humidity })])].slice(0, 4),
    alerts: buildAlerts({ temp, condition, wind, air }),
    forecastCount: forecast.length,
  }
}
