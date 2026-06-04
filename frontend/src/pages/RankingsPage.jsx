import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, CalendarDays, Car, Clock3, Compass, Crown, MapPin, Mountain, Route, ShieldCheck, Sparkles, Star, Umbrella } from 'lucide-react'
import HeroSection from '../components/common/HeroSection.jsx'
import SectionHeader from '../components/common/SectionHeader.jsx'
import ScenicCard from '../components/common/ScenicCard.jsx'
import { SkeletonList } from '../components/common/Skeleton.jsx'
import { getScenicList } from '../api/scenic.js'
import { request } from '../api/client.js'

const ROUTE_COLLECTIONS = [
  {
    title: '川西雪山环线',
    subtitle: '成都出发，串联雪山、草原和藏寨',
    image: '/images/hero-mountain-lake.jpg',
    tag: '自驾 5-7 天',
    season: '5-10 月',
    stops: ['成都', '康定', '新都桥', '稻城亚丁'],
    highlights: '雪山观景、公路摄影、藏寨人文',
    to: '/provinces/四川省',
  },
  {
    title: '江南园林慢游',
    subtitle: '苏州、杭州、绍兴一线的古典园林与水乡',
    image: '/images/hero-mountain-lake.jpg',
    tag: '周末 2-3 天',
    season: '3-5 月 / 9-11 月',
    stops: ['苏州', '杭州', '绍兴'],
    highlights: '园林、古镇、湖景、茶事体验',
    to: '/provinces/江苏省',
  },
  {
    title: '华北古迹巡礼',
    subtitle: '保定、北京、承德周边的历史文化目的地',
    image: '/images/hero-mountain-lake.jpg',
    tag: '文化 3-4 天',
    season: '4-6 月 / 9-10 月',
    stops: ['保定', '北京', '承德'],
    highlights: '世界遗产、皇家园林、古建研学',
    to: '/provinces/河北省',
  },
]

const SEASONAL_IDEAS = [
  { season: '春季', title: '赏花踏青', desc: '关注江南、华中和西南低海拔目的地，适合轻徒步与古镇慢游。', to: '/themes/赏花踏青' },
  { season: '夏季', title: '避暑亲水', desc: '优先选择高海拔山地、峡谷、湖泊和森林公园，避开正午强日照。', to: '/themes/避暑胜地' },
  { season: '秋季', title: '自驾观景', desc: '山地公路、草原和古村落进入高光期，建议提前规划住宿和停车。', to: '/trip-planning?tab=map' },
  { season: '冬季', title: '冰雪温泉', desc: '北方冰雪、南方温泉和城市文化游更稳定，注意交通和天气预警。', to: '/themes/冰雪世界' },
]

const RANKING_RULES = [
  ['目的地评分', '优先展示评分、评论反馈和资料完整度更高的景区。'],
  ['区域覆盖', '按省份、城市、主题路线分组，避免榜单只集中在单一区域。'],
  ['出行可执行', '路线推荐优先考虑天数、交通方式、季节和周末可达性。'],
]

const HOT_SEARCHES = ['河北保定周边', '江南园林', '川西自驾', '避暑胜地', '摄影打卡', '亲子乐园']

function normalizeProvinceRows(data) {
  const rows = Array.isArray(data)
    ? data
    : data?.groups
        ? Object.values(data.groups).flat()
        : Array.isArray(data?.items)
          ? data.items
          : []

  const byProvince = new Map()
  rows.forEach(item => {
    const province = item?.province || item?.name
    if (!province) return
    const scenicCount = Number(item.scenic_count ?? item.count ?? 0)
    const current = byProvince.get(province)
    if (!current || scenicCount > (current.scenic_count || 0)) {
      byProvince.set(province, { ...item, province, scenic_count: scenicCount })
    }
  })

  return Array.from(byProvince.values()).sort((a, b) => (b.scenic_count || 0) - (a.scenic_count || 0))
}

export default function RankingsPage() {
  const [scenic, setScenic] = useState([])
  const [provinces, setProvinces] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getScenicList('?limit=12&sort=rating').then(data => setScenic(Array.isArray(data) ? data : (data?.items || []))),
      request('/api/regions/provinces').then(data => setProvinces(normalizeProvinceRows(data).slice(0, 10))),
    ]).finally(() => setLoading(false))
  }, [])

  const topScenic = useMemo(() => scenic.slice(0, 6), [scenic])
  const scenicTotal = provinces.reduce((sum, item) => sum + Number(item.scenic_count || 0), 0)

  return (
    <>
      <HeroSection
        variant="display"
        images={[
          '/images/hero-mountain-lake.jpg',
        ]}
        title="热门榜单"
        subtitle="用目的地热度、评分、主题路线和季节灵感，快速找到下一次出发方向。"
        capsules={[
          { title: String(scenic.length || 12), subtitle: '精选目的地' },
          { title: String(provinces.length || 10), subtitle: '热门省份' },
        ]}
      />

      <section className="ranking-lead-panel">
        <div>
          <span><Sparkles size={16} /> 灵感合集</span>
          <h2>寻找你的下一次旅行</h2>
          <p>精选全国最美自驾路线、小众打卡地及季节性限定景观，让你的周末不再单调。</p>
        </div>
        <div className="ranking-lead-actions">
          <Link className="primary-btn" to="/trip-planning?tab=map">定制专属行程 <ArrowRight size={16} /></Link>
          <Link className="ghost-btn" to="/provinces">按省份浏览</Link>
        </div>
      </section>

      <section className="ranking-stat-grid">
        {[
          [Crown, '高评分景区', `${topScenic.length || 0} 个`, '按评分与资料质量排序'],
          [MapPin, '热门省份景区', `${scenicTotal.toLocaleString()} 个`, '来自省级目的地数据库'],
          [CalendarDays, '季节灵感', '4 组', '覆盖春夏秋冬出游主题'],
          [ShieldCheck, '榜单规则', '3 项', '减少空泛推荐和重复地区'],
        ].map(([Icon, label, value, desc]) => (
          <article key={label}>
            <Icon size={20} />
            <span>{label}</span>
            <strong>{value}</strong>
            <p>{desc}</p>
          </article>
        ))}
      </section>

      <section>
        <SectionHeader eyebrow="精选榜单" title="高评分目的地" action={<Link to="/destinations">查看全部</Link>} />
        {loading ? (
          <SkeletonList count={4} />
        ) : (
          <div className="card-grid three">
            {topScenic.map((item, index) => (
              <div className="ranking-card-wrap" key={item.id}>
                <span className="ranking-ribbon"><Crown size={15} /> TOP {index + 1}</span>
                <ScenicCard scenic={item} variant="grid" />
              </div>
            ))}
          </div>
        )}
      </section>

      <section>
        <SectionHeader eyebrow="路线灵感" title="热门主题路线" />
        <div className="ranking-route-grid">
          {ROUTE_COLLECTIONS.map(route => (
            <Link className="ranking-route-card" to={route.to} key={route.title}>
              <img src={route.image} alt="" />
              <div>
                <span>{route.tag}</span>
                <strong>{route.title}</strong>
                <p>{route.subtitle}</p>
                <small><Clock3 size={14} /> 推荐季节：{route.season}</small>
                <small><Route size={14} /> {route.stops.join(' → ')}</small>
                <em>{route.highlights}</em>
              </div>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader eyebrow="季节限定" title="按时间选择目的地" />
        <div className="ranking-season-grid">
          {SEASONAL_IDEAS.map(item => (
            <Link to={item.to} key={item.season}>
              <b>{item.season}</b>
              <strong>{item.title}</strong>
              <p>{item.desc}</p>
              <span>查看主题 <ArrowRight size={14} /></span>
            </Link>
          ))}
        </div>
      </section>

      <section>
        <SectionHeader eyebrow="区域热度" title="热门省份排行" action={<Link to="/provinces">省份浏览</Link>} />
        <div className="ranking-province-list">
          {provinces.map((province, index) => (
            <Link to={`/provinces/${encodeURIComponent(province.province)}`} key={province.province}>
              <b>{String(index + 1).padStart(2, '0')}</b>
              <span><MapPin size={16} /> {province.province}</span>
              <strong>{Number(province.scenic_count || 0).toLocaleString()} 景区</strong>
            </Link>
          ))}
        </div>
      </section>

      <section className="ranking-info-grid">
        <article>
          <SectionHeader eyebrow="榜单说明" title="推荐依据" />
          <div className="ranking-rule-list">
            {RANKING_RULES.map(([title, desc]) => (
              <p key={title}><ShieldCheck size={16} /><span><strong>{title}</strong>{desc}</span></p>
            ))}
          </div>
        </article>
        <article>
          <SectionHeader eyebrow="热门搜索" title="快速筛选" />
          <div className="ranking-hot-searches">
            {HOT_SEARCHES.map(keyword => (
              <Link to={`/search?q=${encodeURIComponent(keyword)}`} key={keyword}><Compass size={15} /> {keyword}</Link>
            ))}
          </div>
        </article>
      </section>

      <section className="ranking-tool-strip">
        {[
          [Mountain, '山岳湖泊', '/themes/自然风光'],
          [Umbrella, '季节限定', '/themes/避暑胜地'],
          [Car, '自驾路线', '/trip-planning?tab=map'],
          [Star, '高分推荐', '/destinations?tab=scenic'],
        ].map(([Icon, label, to]) => (
          <Link to={to} key={label}><Icon size={20} /> {label}</Link>
        ))}
      </section>
    </>
  )
}
