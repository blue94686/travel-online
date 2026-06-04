import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ExternalLink, Globe2, Heart, Info, MapPinned, Radar, Satellite } from 'lucide-react'
import { getEarthCategories, getEarthSources, getEarthStats, saveEarthFavorite } from '../api/earth.js'
import { imageFallback } from '../api/fallback.js'

const categoryText = {
  scenic_official: '景区官方',
  city_live: '城市实况',
  nature_live: '自然风景',
  weather_earth: '天气地球',
  satellite_earth: '卫星地球',
  space_earth: '太空视角',
  map_poi: '地图 POI',
  global_featured: '全球精选'
}

export default function EarthOnlinePage() {
  const location = useLocation()
  const navigate = useNavigate()
  const params = useMemo(() => new URLSearchParams(location.search), [location.search])
  const [category, setCategory] = useState(params.get('category') || 'all')
  const [keyword, setKeyword] = useState('')
  const [sources, setSources] = useState([])
  const [categories, setCategories] = useState([])
  const [stats, setStats] = useState({})
  const [notice, setNotice] = useState('')

  useEffect(() => { getEarthCategories().then(data => setCategories(data || [])); getEarthStats().then(data => setStats(data || {})) }, [])
  useEffect(() => {
    const query = new URLSearchParams()
    if (category !== 'all') query.set('category', category)
    if (keyword.trim()) query.set('keyword', keyword.trim())
    getEarthSources(query.toString() ? `?${query}` : '').then(data => setSources(data || []))
  }, [category, keyword])

  const switchCategory = (value) => {
    setCategory(value)
    navigate(value === 'all' ? '/earth-online' : `/earth-online?category=${value}`, { replace: true })
  }

  const favorite = async (source) => {
    const role = localStorage.getItem('scenic-role')
    if (!role) return setNotice('请先登录后再收藏地球 Online 来源')
    await saveEarthFavorite(source.id)
    setNotice(`${source.name} 已加入收藏`)
  }

  return (
    <>
      {notice && <div className="notice">{notice}</div>}
      <section className="earth-hero">
        <div className="earth-visual">
          <span /><i /><b />
          <em className="orbit orbit-one" />
          <em className="orbit orbit-two" />
          <strong className="earth-dot dot-a" />
          <strong className="earth-dot dot-b" />
          <strong className="earth-dot dot-c" />
        </div>
        <div className="earth-hero-content">
          <p className="eyebrow">公开来源聚合</p>
          <h1>地球 Online</h1>
          <p>公开实况 · 天气地球 · 卫星影像 · 太空视角</p>
          <div className="earth-capsules">
            <span>已审核来源 {stats.approved || sources.length}</span>
            <span>全球分类 {stats.categories || categories.length}</span>
            <span>最近检测 {stats.lastChecked || '按需检测'}</span>
            <span>外链优先</span>
          </div>
          <div className="earth-actions">
            {['global_featured', 'weather_earth', 'satellite_earth', 'space_earth'].map(item => <button key={item} onClick={() => switchCategory(item)}>{categoryText[item]}</button>)}
          </div>
        </div>
        <div className="earth-data-panel">
          <p><span>LIVE</span>公开实况外链</p>
          <p><span>SAT</span>卫星影像入口</p>
          <p><span>WX</span>天气地球观察</p>
        </div>
      </section>

      <section className="earth-filter panel">
        <div className="chip-row">{categories.map(item => <button className={category === item.key ? 'active' : ''} onClick={() => switchCategory(item.key)} key={item.key}>{item.label}</button>)}</div>
        <input value={keyword} onChange={e => setKeyword(e.target.value)} placeholder="搜索平台、国家、城市或来源名称" />
      </section>

      <section className="content-grid two">
        <article className="panel earth-map-demo">
          <div className="mini-earth"><span /><span /><span /><span /></div>
          <div>
            <h2>全球来源分布</h2>
            <p>以公开平台、卫星地球、天气地球和地图 POI 为主。未审核、候选、风险来源不会在前台展示。</p>
            <div className="compact-grid"><span>公开外链 {stats.external_only || 18}</span><span>可用来源 {stats.online || 0}</span><span>分类 {stats.categories || 8}</span></div>
          </div>
        </article>
        <article className="panel earth-watchlist">
          <h2>今日推荐观察</h2>
          {[
            ['天气地球', '观察云图、雷达和强对流趋势', 'weather_earth'],
            ['太空视角', '打开公开空间站与任务页面', 'space_earth'],
            ['自然直播', '进入自然保护区公开直播集合', 'nature_live'],
            ['城市地标', '查看旅游城市与地标公开实况', 'global_featured']
          ].map(([title, text, target]) => <button type="button" key={title} onClick={() => switchCategory(target)}><MapPinned size={16} /><strong>{title}</strong><span>{text}</span></button>)}
        </article>
      </section>

      <section className="content-grid two">
        <article className="panel earth-safety">
          <h2>来源安全说明</h2>
          <p>地球 Online 只收录公开、合法、可解释来源。无法确认嵌入授权的来源仅提供官网外链。</p>
          <p>禁止私人监控、未授权摄像头、盗链视频流和绕过登录鉴权的内容。</p>
          <p>卫星地球和太空视角主要用于科普与出行参考。</p>
        </article>
      </section>

      <section>
        <div className="card-title-row"><h2>公开来源</h2><span>{sources.length} 个已审核来源</span></div>
        <div className="earth-source-grid">
          {sources.map(source => (
            <article className="earth-source-card" key={source.id}>
              <img src={source.thumbnail_url || imageFallback} onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = imageFallback }} alt={source.name} />
              <div>
                <div className="card-title-row"><h3>{source.name}</h3><span className="status-badge">{categoryText[source.category] || source.category}</span></div>
                <p>{source.description}</p>
                <div className="earth-meta">
                  <span>{source.country || '全球'} {source.city || ''}</span>
                  <span>{source.source_platform}</span>
                  <span>{source.is_live ? '实时' : '非实时'}</span>
                  <span>{source.is_embeddable ? '可嵌入' : '仅外链'}</span>
                  <span>状态 {source.availability_status}</span>
                  <span>风险 {source.risk_level}</span>
                </div>
                <p className="auth-note"><Info size={15} /> {source.authorization_note || '公开来源，前台按外链方式打开。'}</p>
                <div className="admin-actions">
                  <a className="primary-btn" href={source.source_url} target="_blank" rel="noopener noreferrer"><ExternalLink size={16} /> 打开公开页面</a>
                  {source.can_embed && <button onClick={() => setNotice(`${source.name} 嵌入预览已打开`)}>查看嵌入预览</button>}
                  <button onClick={() => favorite(source)}><Heart size={16} /> 收藏来源</button>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      <section className="content-grid three">
        {[
          [Satellite, '卫星地球', 'NASA、ESA 与 Copernicus 公开地球观测入口。', 'satellite_earth'],
          [Radar, '天气地球', '云图、雷达、风雨与旅行天气判断。', 'weather_earth'],
          [Globe2, '太空视角', '从空间站和任务视角理解地球。', 'space_earth']
        ].map(([Icon, title, text, to]) => <Link className="feature-tile" to={`/earth-online?category=${to}`} key={title}><Icon size={24} /><div><h3>{title}</h3><p>{text}</p></div></Link>)}
      </section>
    </>
  )
}
