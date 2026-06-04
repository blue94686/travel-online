const PROVINCE_LAYOUT = {
  新疆维吾尔自治区: [13, 32],
  西藏自治区: [18, 62],
  青海省: [31, 52],
  甘肃省: [40, 45],
  宁夏回族自治区: [49, 39],
  内蒙古自治区: [55, 26],
  黑龙江省: [78, 14],
  吉林省: [80, 25],
  辽宁省: [77, 34],
  北京市: [68, 36],
  天津市: [71, 39],
  河北省: [67, 43],
  山西省: [61, 45],
  陕西省: [56, 52],
  河南省: [64, 56],
  山东省: [73, 52],
  江苏省: [75, 63],
  上海市: [81, 67],
  安徽省: [70, 65],
  湖北省: [63, 66],
  重庆市: [54, 67],
  四川省: [43, 68],
  贵州省: [51, 78],
  云南省: [42, 84],
  湖南省: [62, 75],
  江西省: [69, 76],
  浙江省: [77, 73],
  福建省: [75, 82],
  广东省: [66, 87],
  广西壮族自治区: [56, 86],
  海南省: [61, 95],
  台湾省: [84, 85],
  香港特别行政区: [69, 91],
  澳门特别行政区: [66, 92],
}

const REGION_ORDER = ['东北', '华北', '华东', '华中', '华南', '西南', '西北', '港澳台', '其他']

function flattenGroups(groups = {}) {
  const entries = []
  REGION_ORDER.forEach(group => {
    ;(groups[group] || []).forEach(item => entries.push({ ...item, region_group: group }))
  })
  Object.entries(groups).forEach(([group, provinces]) => {
    if (REGION_ORDER.includes(group)) return
    ;(provinces || []).forEach(item => entries.push({ ...item, region_group: group }))
  })
  return entries.filter(item => item?.province)
}

function shortName(province = '') {
  return province
    .replace('维吾尔自治区', '')
    .replace('壮族自治区', '')
    .replace('回族自治区', '')
    .replace('特别行政区', '')
    .replace('自治区', '')
    .replace('省', '')
    .replace('市', '')
}

function densityFor(count, maxCount) {
  const scenicCount = Number(count || 0)
  if (!scenicCount || !maxCount) return 'low'
  const ratio = scenicCount / maxCount
  if (ratio >= 0.72) return 'high'
  if (ratio >= 0.36) return 'medium'
  return 'low'
}

export default function ChinaProvinceMap({ groups = {}, selectedProvince = '', onProvinceSelect }) {
  const provinces = flattenGroups(groups)
  const maxCount = Math.max(...provinces.map(item => Number(item.scenic_count || 0)), 0)
  const positioned = provinces.filter(item => PROVINCE_LAYOUT[item.province])
  const unpositioned = provinces.filter(item => !PROVINCE_LAYOUT[item.province])

  if (!provinces.length) {
    return (
      <section className="china-map-browser">
        <div className="china-map-empty">正在加载省区地图数据...</div>
      </section>
    )
  }

  return (
    <section className="china-map-browser" aria-label="中国省区地图浏览">
      <div className="china-map-copy">
        <span>地图浏览</span>
        <h2>点击省区查看景区信息</h2>
        <p>按全国源表统计展示省级入口，点击后可查看城市、代表景区和继续浏览路径。</p>
      </div>

      <div className="china-map-shell">
        <div className="china-province-map">
          <div className="china-map-mainland" aria-hidden="true" />
          {positioned.map(item => {
            const [x, y] = PROVINCE_LAYOUT[item.province]
            const isActive = selectedProvince === item.province
            return (
              <button
                key={item.province}
                type="button"
                className={`province-map-button ${isActive ? 'active' : ''}`}
                style={{ '--map-x': `${x}%`, '--map-y': `${y}%` }}
                data-density={densityFor(item.scenic_count, maxCount)}
                aria-pressed={isActive}
                title={`${item.province} · ${Number(item.scenic_count || 0).toLocaleString()} 景区`}
                onClick={() => onProvinceSelect?.(item)}
              >
                <strong>{shortName(item.province)}</strong>
                <span>{Number(item.scenic_count || 0).toLocaleString()}</span>
              </button>
            )
          })}
        </div>

        <aside className="china-map-legend">
          <div><i data-density="high" /> 高密度景区</div>
          <div><i data-density="medium" /> 中密度景区</div>
          <div><i data-density="low" /> 待继续补全</div>
        </aside>
      </div>

      {unpositioned.length > 0 && (
        <div className="china-map-extra-list" aria-label="其他省区入口">
          {unpositioned.map(item => (
            <button
              key={item.province}
              type="button"
              className="ghost-btn"
              onClick={() => onProvinceSelect?.(item)}
            >
              {item.province}
              <span>{Number(item.scenic_count || 0).toLocaleString()} 景区</span>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}
