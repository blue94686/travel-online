import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { CloudSun, Globe2, MapPin, MessageSquare, Search, Leaf, Map, Compass, User, TrendingUp, ChevronRight } from 'lucide-react'
import { getScenicList } from '../api/scenic.js'
import { getComments } from '../api/user.js'
import { getWeather } from '../api/weather.js'
import { request } from '../api/client.js'
import { getBanners, getArticles } from '../api/layouts.js'
import useAutoLocation from '../hooks/useAutoLocation.js'
import SectionHeader from '../components/common/SectionHeader.jsx'
import ScenicCard from '../components/common/ScenicCard.jsx'
import WeatherCard from '../components/common/WeatherCard.jsx'
import ReviewCard from '../components/common/ReviewCard.jsx'
import MapPanel from '../components/common/MapPanel.jsx'
import HeroSection from '../components/common/HeroSection.jsx'
import { SkeletonList } from '../components/common/Skeleton.jsx'

const THEME_CARDS = [
  { name: '徒步登山', icon: '⛰', gradient: 'linear-gradient(135deg, #667eea, #764ba2)' },
  { name: '人文古迹', icon: '🏛', gradient: 'linear-gradient(135deg, #f093fb, #f5576c)' },
  { name: '摄影打卡', icon: '📸', gradient: 'linear-gradient(135deg, #4facfe, #00f2fe)' },
  { name: '自然风光', icon: '🌿', gradient: 'linear-gradient(135deg, #43e97b, #38f9d7)' },
  { name: '美食之旅', icon: '🍜', gradient: 'linear-gradient(135deg, #fa709a, #fee140)' },
  { name: '自驾旅行', icon: '🚗', gradient: 'linear-gradient(135deg, #a18cd1, #fbc2eb)' },
  { name: '亲子乐园', icon: '🎡', gradient: 'linear-gradient(135deg, #fccb90, #d57eeb)' },
  { name: '避暑胜地', icon: '❄', gradient: 'linear-gradient(135deg, #74b9ff, #0984e3)' },
]

const TOOLS = [
  ['景区与主题', '发现目的地', Compass, '/destinations'],
  ['地图与路线', '规划行程', Map, '/trip-planning'],
  ['天气与实况', '实况影像', CloudSun, '/trip-planning'],
  ['地球 Online', '全球观测', Globe2, '/earth-online'],
  ['评论社区', '图文分享', MessageSquare, '/community'],
  ['用户中心', '我的收藏', User, '/user'],
]

const FALLBACK_PROVINCES = [
  { province: '江苏省', scenic_count: 44497 },
  { province: '浙江省', scenic_count: 50743 },
  { province: '四川省', scenic_count: 47895 },
  { province: '广东省', scenic_count: 43393 },
  { province: '湖南省', scenic_count: 29640 },
  { province: '云南省', scenic_count: 28620 },
  { province: '陕西省', scenic_count: 23800 },
  { province: '福建省', scenic_count: 22410 },
]

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

export default function HomePage() {
  const [scenic, setScenic] = useState([])
  const [comments, setComments] = useState([])
  const [banners, setBanners] = useState([])
  const [articles, setArticles] = useState([])
  const [weather, setWeather] = useState(null)
  const [provinces, setProvinces] = useState([])
  const [loading, setLoading] = useState(true)
  const autoLocation = useAutoLocation()

  useEffect(() => {
    Promise.all([
      getScenicList('?limit=8&sort=rating').then(data => { setScenic(Array.isArray(data) ? data : (data?.items || [])); return data }),
      getComments().then(data => { setComments(data?.items || data || []); return data }),
      getBanners().then(setBanners),
      getArticles().then(setArticles),
      request('/api/regions/provinces').then(data => {
        const all = normalizeProvinceRows(data)
        setProvinces((all.length ? all : FALLBACK_PROVINCES).slice(0, 8))
      }).catch(() => setProvinces(FALLBACK_PROVINCES)),
    ]).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (autoLocation.city) getWeather(autoLocation.city).then(setWeather)
  }, [autoLocation.city])

  const localCity = autoLocation.city || '苏州市'
  const localCityName = localCity.replace('市', '')
  const weatherCurrent = weather?.current || null

  return (
    <>
      {autoLocation.message && <div className="notice location-notice">{autoLocation.message}</div>}

      {/* Hero / Banner */}
      <HeroSection
        variant="home"
        images={banners.some(b => b.image_url) ? banners.map(b => b.image_url).filter(Boolean) : [
          'https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1920&q=80',
          'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=1920&q=80',
          'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1920&q=80'
        ]}
        searchCity={localCity}
        capsules={[
          { icon: <MapPin size={24} />, title: autoLocation.status === 'loading' ? '定位中...' : localCityName, subtitle: autoLocation.status === 'success' ? '当前定位' : '默认城市' },
          { icon: <CloudSun size={24} />, title: weatherCurrent ? `${weatherCurrent.temp}°C ${weatherCurrent.condition}` : '加载中...', subtitle: weather?.provider || '天气' },
          { icon: <Leaf size={24} />, title: weatherCurrent?.air || '暂无', subtitle: '空气质量' },
        ]}
        title={banners.length > 0 ? banners[0].title : "今天去哪玩？"}
        subtitle="极客旅行 · 精准规划 · 实时掌握"
      />

      {/* 本周精选 - 横向滚动 */}
      <section>
        <SectionHeader eyebrow="本周精选" title="高评分目的地" action={<Link to="/destinations">查看全部 <ChevronRight size={14} /></Link>} />
        {loading ? (
          <SkeletonList count={4} />
        ) : scenic.length > 0 ? (
          <div className="horizontal-scroll scenic-rail">
            {scenic.slice(0, 8).map(item => (
              <div key={item.id} className="scenic-rail-item">
                <ScenicCard scenic={item} variant="grid" />
              </div>
            ))}
          </div>
        ) : (
          <div className="empty-state">暂无景区数据，请确认后端服务已启动。</div>
        )}
      </section>

      {/* 灵感合集 */}
      <section className="home-inspiration-panel">
        <div className="home-inspiration-copy">
            <SectionHeader eyebrow="灵感合集" title="寻找你的下一次旅行" />
            <p>精选全国最美自驾路线、小众打卡地及季节性限定景观，让你的周末不再单调。</p>
            <div className="home-inspiration-actions">
              <Link className="primary-btn" to="/rankings">探索热门榜单</Link>
              <Link className="ghost-btn" to="/trip-planning?tab=map">定制专属行程</Link>
            </div>
        </div>
        <div className="home-inspiration-grid">
            {[
              { name: '川西环线', img: '/images/hero-mountain-lake.jpg', count: '12 景区', to: '/rankings' },
              { name: '苏式园林', img: '/images/hero-mountain-lake.jpg', count: '8 景区', to: '/rankings' },
            ].map(col => (
              <Link to={col.to} key={col.name} className="home-inspiration-card">
                <img src={col.img} alt="" />
                <div>
                  <strong>{col.name}</strong>
                  <small>{col.count}</small>
                </div>
              </Link>
            ))}
        </div>
      </section>

      {/* 最新资讯/文章 */}
      {articles.length > 0 && (
        <section>
          <SectionHeader eyebrow="官方指南" title="精选攻略与公告" action={<Link to="/community">阅读更多</Link>} />
          <div className="home-guide-grid">
            {articles.slice(0, 3).map(article => (
              <article key={article.id} className="home-guide-card">
                <div className="home-guide-media">
                  <img src={article.cover_image || article.image_url || '/images/hero-mountain-lake.jpg'} alt="" />
                </div>
                <div className="home-guide-body">
                  <span className="status-badge">{article.category}</span>
                  <h3><Link to={`/guides/${article.id}`}>{article.title}</Link></h3>
                  <p>
                    {article.content.substring(0, 100)}...
                  </p>
                  <div className="home-guide-meta">
                    <span>{article.author} · {article.created_at?.split('T')[0]}</span>
                    <Link className="ghost-btn" to={`/guides/${article.id}`}>阅读全文</Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>
      )}

      {/* 主题旅行 */}
      <section>
        <SectionHeader eyebrow="主题旅行" title="按兴趣出发" action={<Link to="/themes">全部主题 <ChevronRight size={14} /></Link>} />
        <div className="home-theme-grid">
          {THEME_CARDS.map(theme => (
            <Link to={`/themes/${encodeURIComponent(theme.name)}`} key={theme.name} className="home-theme-card" style={{ '--theme-bg': theme.gradient }}>
              <div>{theme.icon}</div>
              <strong>{theme.name}</strong>
            </Link>
          ))}
        </div>
      </section>

      {/* 热门省份 + 天气 */}
      <section className="home-live-grid">
        <div className="home-province-panel">
          <SectionHeader eyebrow="热门省份" title="省级目的地" action={<Link to="/provinces">更多</Link>} />
          {provinces.length > 0 ? (
            <div className="home-province-grid">
              {provinces.map(p => (
                <Link to={`/provinces/${encodeURIComponent(p.province)}`} key={p.province}>
                  <strong>{p.province}</strong>
                  <span>{p.scenic_count || 0} 景区</span>
                </Link>
              ))}
            </div>
          ) : <div className="empty-state">{loading ? '加载中...' : '暂无省份数据'}</div>}
        </div>
        <div className="home-live-side">
          <WeatherCard weather={weather || { current: { temp: '--', condition: '加载中', air: '--' } }} to={`/trip-planning?tab=weather&city=${encodeURIComponent(localCity)}`} />
          <div className="home-map-wrap">
            <MapPanel title="地图查看" compact city={localCityName} actionTo={`/trip-planning?tab=map&from=${encodeURIComponent(localCityName)}&to=${encodeURIComponent(localCityName)}`} />
          </div>
        </div>
      </section>

      {/* 最新评论 */}
      {comments.length > 0 && (
        <section>
          <SectionHeader eyebrow="最新评论" title="游客分享" action={<Link to="/community">更多</Link>} />
          <div className="horizontal-scroll review-rail">
            {comments.slice(0, 6).map(item => (
              <div key={item.id} className="review-rail-item">
                <Link to={item.scenic_id ? `/scenic/${item.scenic_id}` : '/community'}><ReviewCard item={item} /></Link>
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 工具入口 */}
      <section className="home-tools-panel">
        <SectionHeader eyebrow="旅行工具" title="常用入口" />
        <div className="home-tool-grid">
          {TOOLS.map(([title, text, Icon, to]) => (
            <Link className="home-tool-card" to={to} key={title}>
              <Icon size={22} />
              <span><strong>{title}</strong><small>{text}</small></span>
            </Link>
          ))}
        </div>
      </section>
    </>
  )
}
