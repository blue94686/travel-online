import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowRight, CalendarDays, Compass, MapPinned, Route, Sparkles, Star, TreePine } from 'lucide-react'
import { getRegionCities, getRegionProvinces, getSyncedScenicList } from '../api/scenic.js'
import HeroSection from '../components/common/HeroSection.jsx'
import ScenicCard from '../components/common/ScenicCard.jsx'
import EmptyState from '../components/common/EmptyState.jsx'
import SectionHeader from '../components/common/SectionHeader.jsx'
import { themes as themeNames } from '../utils/scenicSync.js'

const PROVINCE_HERO_IMAGES = [
  'https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=1920&q=80',
  'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?auto=format&fit=crop&w=1920&q=80',
  'https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=1920&q=80',
]

const PROVINCE_NOTES = {
  '河北省': {
    summary: '连接京津、山海、长城和皇家园林的复合型目的地，适合周末自驾、古建研学和山海度假。',
    season: '4-6 月与 9-10 月综合体验较稳',
    route: '保定古城与太行山线、承德避暑山庄线、秦皇岛海滨线可分开规划。',
  },
  '浙江省': {
    summary: '湖山、古镇、海岛和江南城市密集分布，适合慢游、摄影、亲子和短途度假。',
    season: '春秋最佳，夏季适合海岛与山地避暑',
    route: '杭州西湖起步，可延伸到绍兴、湖州、舟山或温州山海线。',
  },
  '四川省': {
    summary: '雪山、峡谷、古城、美食和民族文化集中，适合长线深度游与自然风光旅行。',
    season: '春秋适合大多数线路，夏季适合川西避暑',
    route: '成都作为中转，分成九寨黄龙、峨眉乐山、川西环线等主题。',
  },
}

function provincePath(province) {
  return `/provinces/${encodeURIComponent(province)}`
}

function flattenProvinceGroups(groups = {}) {
  return Object.values(groups).flat().filter(item => item?.province)
}

export default function ProvinceDetailPage() {
  const navigate = useNavigate()
  const { province: rawProvince = '' } = useParams()
  const province = rawProvince ? decodeURIComponent(rawProvince) : ''
  const [provinceGroups, setProvinceGroups] = useState({})
  const [cities, setCities] = useState([])
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)

  const allProvinces = useMemo(() => flattenProvinceGroups(provinceGroups), [provinceGroups])
  const currentProvince = allProvinces.find(item => item.province === province)
  const otherProvinces = allProvinces.filter(item => item.province !== province).slice(0, 8)
  const note = PROVINCE_NOTES[province] || {
    summary: `${province || '全国'}拥有不同类型的景区、城市公园、人文古迹和自然目的地，适合按城市、主题和季节继续筛选。`,
    season: '四季皆宜，建议结合天气与景区公告安排',
    route: '先选择一个核心城市，再串联周边 1-2 个轻量目的地，行程更从容。',
  }

  useEffect(() => {
    getRegionProvinces().then(data => setProvinceGroups(data?.groups || {})).catch(() => setProvinceGroups({}))
  }, [])

  useEffect(() => {
    if (!province) return
    setLoading(true)
    Promise.all([
      getRegionCities(province).catch(() => []),
      getSyncedScenicList(`?province=${encodeURIComponent(province)}&limit=60&offset=0`).catch(() => null),
    ]).then(([cityData, scenicData]) => {
      setCities(Array.isArray(cityData) ? cityData : [])
      const nextItems = Array.isArray(scenicData) ? scenicData : (scenicData?.items || [])
      setItems(nextItems)
      setTotal(Array.isArray(scenicData) ? nextItems.length : (scenicData?.total || nextItems.length))
    }).finally(() => setLoading(false))
    window.scrollTo(0, 0)
  }, [province])

  if (!province) {
    return (
      <div className="province-page">
        <HeroSection
          variant="display"
          images={PROVINCE_HERO_IMAGES}
          title="省份浏览"
          subtitle="按省份进入独立目的地页面，查看城市入口、精选景区、主题玩法和相邻推荐。"
          capsules={[
            { title: String(allProvinces.length || 34), subtitle: '省级入口' },
            { title: '三级浏览', subtitle: '省 / 城市 / 区县' },
          ]}
        />
        <div className="page-content page-content-wide" style={{ marginTop: -40, position: 'relative', zIndex: 5 }}>
          <div className="stack" style={{ gap: 28 }}>
            {Object.entries(provinceGroups).map(([group, provinces]) => (
              <section className="panel" key={group} style={{ padding: 28, borderRadius: 16 }}>
                <SectionHeader eyebrow="Region" title={group} />
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: 14, marginTop: 18 }}>
                  {provinces.map(item => (
                    <Link key={item.province} to={provincePath(item.province)} style={{ border: '1px solid var(--color-border)', borderRadius: 8, padding: 16, background: 'var(--color-surface)', display: 'grid', gap: 8 }}>
                      <strong style={{ fontSize: 18 }}>{item.province}</strong>
                      <span style={{ color: 'var(--color-muted)', fontSize: 13 }}>{item.city_count || 0} 个城市 · {(item.scenic_count || 0).toLocaleString()} 个目的地</span>
                    </Link>
                  ))}
                </div>
              </section>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="province-page">
      <HeroSection
        variant="display"
        images={PROVINCE_HERO_IMAGES}
        title={province}
        subtitle={note.summary}
        capsules={[
          { title: (currentProvince?.scenic_count || total || items.length).toLocaleString(), subtitle: '目的地' },
          { title: String(cities.length || currentProvince?.city_count || 0), subtitle: '城市入口' },
          { title: note.season, subtitle: '推荐季节' },
        ]}
      />

      <div className="page-content page-content-wide" style={{ marginTop: -40, position: 'relative', zIndex: 5 }}>
        <div className="stack" style={{ gap: 24 }}>
          <div className="panel" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 24px', borderRadius: 16 }}>
            <button className="ghost-btn" onClick={() => navigate('/provinces')} style={{ padding: 4 }}><ArrowRight size={18} style={{ transform: 'rotate(180deg)' }} /></button>
            <strong>{province}目的地详情</strong>
            <Link className="ghost-btn" style={{ marginLeft: 'auto' }} to={`/destinations?province=${encodeURIComponent(province)}&tab=scenic`}>进入三级浏览</Link>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
            {[
              ['城市玩法', cities.slice(0, 5).join(' / ') || '城市数据持续补全', MapPinned],
              ['适游季节', note.season, CalendarDays],
              ['路线建议', note.route, Route],
            ].map(([label, value, Icon]) => (
              <div className="panel" key={label} style={{ padding: 20, borderRadius: 14 }}>
                <Icon size={20} style={{ color: 'var(--color-primary)', marginBottom: 10 }} />
                <div style={{ color: 'var(--color-muted)', fontSize: 12, marginBottom: 6 }}>{label}</div>
                <strong style={{ fontSize: 16, lineHeight: 1.55 }}>{value}</strong>
              </div>
            ))}
          </div>

          {cities.length > 0 && (
            <section className="panel" style={{ padding: 24, borderRadius: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <Compass size={20} style={{ color: 'var(--color-primary)' }} />
                <h3 style={{ margin: 0 }}>城市入口</h3>
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                {cities.slice(0, 24).map(city => (
                  <Link key={city} className="ghost-btn" to={`/destinations?province=${encodeURIComponent(province)}&city=${encodeURIComponent(city)}&tab=scenic`}>{city}</Link>
                ))}
              </div>
            </section>
          )}

          <section className="panel" style={{ padding: 24, borderRadius: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <Star size={20} style={{ color: 'var(--color-primary)' }} />
                <h3 style={{ margin: 0 }}>精选景区</h3>
              </div>
              <Link className="ghost-btn" to={`/destinations?province=${encodeURIComponent(province)}&tab=scenic`}>查看全部</Link>
            </div>
            {loading ? (
              <div style={{ color: 'var(--color-muted)', padding: 30 }}>正在加载景区...</div>
            ) : items.length > 0 ? (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: 18 }}>
                {items.slice(0, 9).map(item => <ScenicCard key={item.id} scenic={item} />)}
              </div>
            ) : (
              <EmptyState title="暂无景区数据" text="可进入三级浏览查看同步状态。" />
            )}
          </section>

          <section className="panel" style={{ padding: 24, borderRadius: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
              <TreePine size={20} style={{ color: 'var(--color-primary)' }} />
              <h3 style={{ margin: 0 }}>按主题继续探索</h3>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12 }}>
              {themeNames.filter(name => name !== '全部').slice(0, 8).map(theme => (
                <Link key={theme} to={`/destinations?province=${encodeURIComponent(province)}&theme=${encodeURIComponent(theme)}&tab=scenic`} style={{ border: '1px solid var(--color-border)', borderRadius: 8, padding: 14, background: 'var(--color-bg-soft)' }}>
                  <strong>{theme}</strong>
                  <span style={{ display: 'block', marginTop: 6, color: 'var(--color-muted)', fontSize: 12 }}>筛选 {province} 目的地</span>
                </Link>
              ))}
            </div>
          </section>

          {otherProvinces.length > 0 && (
            <section className="panel" style={{ padding: 24, borderRadius: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                <Sparkles size={20} style={{ color: 'var(--color-primary)' }} />
                <h3 style={{ margin: 0 }}>其他省份推荐</h3>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 12 }}>
                {otherProvinces.map(item => (
                  <Link key={item.province} to={provincePath(item.province)} style={{ border: '1px solid var(--color-border)', borderRadius: 8, padding: 14, background: 'var(--color-surface)' }}>
                    <strong>{item.province}</strong>
                    <span style={{ display: 'block', marginTop: 6, color: 'var(--color-muted)', fontSize: 12 }}>{(item.scenic_count || 0).toLocaleString()} 个目的地</span>
                  </Link>
                ))}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  )
}
