const COST_RULES = {
  driving: [
    ['燃油/电耗', 0.65],
    ['过路停车', 0.28],
    ['机动预留', 0.18],
  ],
  transit: [
    ['公共交通', 0.18],
    ['接驳打车', 0.12],
    ['机动预留', 0.08],
  ],
  walking: [
    ['交通费用', 0],
    ['补给预留', 2.2],
    ['机动预留', 0.5],
  ],
  train: [
    ['车票预估', 0.42],
    ['市内接驳', 0.12],
    ['机动预留', 0.08],
  ],
  flight: [
    ['机票预估', 0.85],
    ['机场接驳', 0.16],
    ['机动预留', 0.12],
  ],
}

export function estimateRouteCosts(route = {}, mode = 'driving') {
  const distance = Math.max(0, Number(route.distance_km) || 0)
  const minutes = Math.max(0, Number(route.duration_minutes) || 0)
  const rules = COST_RULES[mode] || COST_RULES.driving
  return rules.map(([label, factor]) => {
    const base = mode === 'walking' ? minutes : distance
    return {
      label,
      value: Math.round(base * factor),
    }
  })
}

function normalizeRawPoints(points = []) {
  const parsed = points.map(point => {
    const lng = Number(point?.[0])
    const lat = Number(point?.[1])
    return { lng, lat }
  }).filter(point => Number.isFinite(point.lng) && Number.isFinite(point.lat))
  if (parsed.length >= 2) return parsed
  return [
    { lng: 0, lat: 0 },
    { lng: 0.35, lat: 0.55 },
    { lng: 0.7, lat: 0.28 },
    { lng: 1, lat: 0.82 },
  ]
}

export function buildRouteMapModel(points = [], startLabel = '起点', endLabel = '终点') {
  const parsed = normalizeRawPoints(points)
  const minLng = Math.min(...parsed.map(point => point.lng))
  const maxLng = Math.max(...parsed.map(point => point.lng))
  const minLat = Math.min(...parsed.map(point => point.lat))
  const maxLat = Math.max(...parsed.map(point => point.lat))
  const lngRange = maxLng - minLng || 1
  const latRange = maxLat - minLat || 1
  const normalized = parsed.map((point, index) => ({
    x: 48 + ((point.lng - minLng) / lngRange) * 544,
    y: 230 - ((point.lat - minLat) / latRange) * 174,
    label: index === 0 ? startLabel : index === parsed.length - 1 ? endLabel : `途经 ${index}`,
    type: index === 0 ? 'start' : index === parsed.length - 1 ? 'end' : 'via',
  }))

  const path = normalized.map((point, index) => `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(1)} ${point.y.toFixed(1)}`).join(' ')
  const guidePath = normalized.map((point, index) => {
    const lift = index % 2 === 0 ? -28 : 24
    return `${index === 0 ? 'M' : 'L'} ${point.x.toFixed(1)} ${(point.y + lift).toFixed(1)}`
  }).join(' ')

  return {
    width: 640,
    height: 300,
    path,
    guidePath,
    points: normalized,
  }
}
