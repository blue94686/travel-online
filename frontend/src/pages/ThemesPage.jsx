import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
import { Mountain, Landmark, Camera, TreePine, Utensils, Car, Baby, Snowflake, Flower2, Sun, ChevronRight, Compass, Sparkles, CalendarDays, MapPinned, Route, Users } from 'lucide-react'
import { getScenicThemes, getSyncedScenicList } from '../api/scenic.js'
import HeroSection from '../components/common/HeroSection.jsx'
import ScenicCard from '../components/common/ScenicCard.jsx'
import { SkeletonList } from '../components/common/Skeleton.jsx'
import EmptyState from '../components/common/EmptyState.jsx'

const THEME_ICON_MAP = {
  Mountain,
  Landmark,
  Camera,
  TreePine,
  Utensils,
  Car,
  Baby,
  Snowflake,
  Flower2,
  Sun,
}

const FALLBACK_THEMES = [
  {
    slug: 'hiking',
    name: '徒步登山',
    icon: 'Mountain',
    image_url: 'https://images.unsplash.com/photo-1551632811-561732d1e306?auto=format&fit=crop&w=1200&q=80',
    description: '用双脚丈量山河，把峡谷、森林、峰顶和云海串成一条有呼吸感的路线。',
    guide: '优先选择成熟步道和有补给点的景区，出发前确认天气、海拔、关闭路段和返程交通。',
    keywords: ['徒步', '登山', '步道', '峡谷'],
    season: '春秋最舒适，夏季适合清晨出发',
    audience: '适合体能较好、喜欢户外节奏的旅行者',
    route_idea: '半日轻徒步可选城市近郊山地，一日路线建议选择环线或索道下撤点明确的目的地。',
  },
  {
    slug: 'heritage',
    name: '人文古迹',
    icon: 'Landmark',
    image_url: 'https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=1200&q=80',
    description: '从古城、寺庙、陵寝、博物馆到历史街区，读懂一座城市留下来的时间层次。',
    guide: '提前了解开放时间和讲解服务，热门古建类景区建议预约官方讲解或错峰参观。',
    keywords: ['古迹', '历史', '文化', '古城'],
    season: '四季皆宜，雨雪天气更适合室内展馆',
    audience: '适合亲子研学、文化爱好者和慢节奏城市漫游',
    route_idea: '把核心古迹、博物馆和老街放在同一天，减少跨城移动，留足讲解和拍照时间。',
  },
  {
    slug: 'photo',
    name: '摄影打卡',
    icon: 'Camera',
    image_url: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?auto=format&fit=crop&w=1200&q=80',
    description: '围绕日出日落、云海、湖面、花海和城市地标，寻找更容易出片的目的地。',
    guide: '关注黄金时段、观景台朝向和交通收班时间，热门机位尽量提前到达。',
    keywords: ['摄影', '风景', '日出', '观景台'],
    season: '春花、夏云、秋色、冬雪各有主题',
    audience: '适合摄影爱好者、短视频创作者和轻旅行用户',
    route_idea: '把清晨和傍晚留给主机位，中午安排室内展馆、咖啡休息或转场。',
  },
  {
    slug: 'nature',
    name: '自然风光',
    icon: 'TreePine',
    image_url: 'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1200&q=80',
    description: '山水、森林、草原、湿地和海岸线，是最适合放慢脚步的旅行主题。',
    guide: '自然类景区受天气影响明显，建议优先看实时天气、景区公告和交通接驳安排。',
    keywords: ['自然', '风光', '山水', '森林'],
    season: '春秋综合体验最佳，夏季注意防晒和雷雨',
    audience: '适合家庭、情侣、摄影和周末放松旅行',
    route_idea: '选择一个核心景区加一个周边轻量点位，避免一天内堆太多山路和换乘。',
  },
  {
    slug: 'food',
    name: '美食之旅',
    icon: 'Utensils',
    image_url: 'https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=1200&q=80',
    description: '用地方小吃、夜市、老字号和农家乐，把目的地的烟火气安排进路线。',
    guide: '优先选择当地人高频消费的街区，景区内餐饮作为补给，主餐放在城区更稳。',
    keywords: ['美食', '小吃', '特色菜', '夜市'],
    season: '四季皆宜，冬季适合热食和温泉组合',
    audience: '适合城市周末游、朋友出行和轻松慢游',
    route_idea: '上午景区慢逛，下午咖啡茶馆，晚上集中安排夜市或地方菜。',
  },
  {
    slug: 'drive',
    name: '自驾旅行',
    icon: 'Car',
    image_url: 'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1200&q=80',
    description: '把公路、观景台、村镇、湖泊和营地串联起来，风景不只在终点。',
    guide: '提前检查车况、停车场、充电或加油点，山区路线要避开夜间和极端天气。',
    keywords: ['自驾', '公路', '环线', '停车'],
    season: '春秋适合长线，夏季适合草原和避暑线',
    audience: '适合家庭、朋友结伴和需要灵活节奏的旅行者',
    route_idea: '按“城市出发-核心景区-观景公路-特色住宿-返程补给”组织两日线。',
  },
  {
    slug: 'family',
    name: '亲子乐园',
    icon: 'Baby',
    image_url: 'https://images.unsplash.com/photo-1502086223501-7ea244bce1e4?auto=format&fit=crop&w=1200&q=80',
    description: '降低体力门槛，增加互动体验、科普内容和休息空间，让孩子也能玩得稳。',
    guide: '优先查看卫生间、母婴室、餐饮、推车友好度和室内备选项目。',
    keywords: ['亲子', '乐园', '动物园', '研学'],
    season: '周末和小长假热门，暑期适合科普研学',
    audience: '适合带娃家庭、亲子研学和低强度短途游',
    route_idea: '每天安排一个主景区即可，中间穿插餐饮休息，避免连续排队和长距离步行。',
  },
  {
    slug: 'summer',
    name: '避暑胜地',
    icon: 'Snowflake',
    image_url: 'https://images.unsplash.com/photo-1519331379826-f10be5486c6f?auto=format&fit=crop&w=1200&q=80',
    description: '去山地、森林、水域和高海拔小城，避开闷热，寻找清凉和慢节奏。',
    guide: '山区早晚温差大，漂流和峡谷类项目需要关注降雨、闭园和安全公告。',
    keywords: ['避暑', '清凉', '漂流', '森林'],
    season: '6-9 月热度最高',
    audience: '适合家庭度假、老人避暑和夏季周末游',
    route_idea: '白天安排清凉景区，傍晚回到住宿地散步，减少正午暴晒下的户外排队。',
  },
  {
    slug: 'flower',
    name: '赏花踏青',
    icon: 'Flower2',
    image_url: 'https://images.unsplash.com/photo-1490750967868-88aa4486c946?auto=format&fit=crop&w=1200&q=80',
    description: '跟着花期走，把樱花、桃花、油菜花、杜鹃和草甸安排进春日路线。',
    guide: '花期受温度和降雨影响明显，出发前查看景区公告、实时照片和交通限流。',
    keywords: ['赏花', '花海', '踏青', '春游'],
    season: '3-5 月最佳，不同地区花期错峰',
    audience: '适合情侣、家庭、摄影和轻户外旅行',
    route_idea: '早上拍花海，中午避开人流用餐，下午安排湖边、公园或古镇轻逛。',
  },
  {
    slug: 'snow',
    name: '冰雪世界',
    icon: 'Sun',
    image_url: 'https://images.unsplash.com/photo-1483921020237-2ff51e8e4b22?auto=format&fit=crop&w=1200&q=80',
    description: '滑雪、雾凇、雪乡、温泉和冬季山景，组成更有层次的冷季旅行。',
    guide: '注意防寒、防滑和交通管制，滑雪项目需确认雪道开放、装备租赁和保险。',
    keywords: ['滑雪', '冰雪', '温泉', '雾凇'],
    season: '12-2 月最佳，北方雪季更稳定',
    audience: '适合冬季度假、滑雪入门和温泉组合游',
    route_idea: '上午滑雪或赏雪，下午温泉休整，夜间减少山路驾驶。',
  },
]

const FALLBACK_BY_NAME = Object.fromEntries(FALLBACK_THEMES.map(theme => [theme.name, theme]))
const DEFAULT_HERO_IMAGES = FALLBACK_THEMES.slice(7, 10).map(theme => theme.image_url)
const THEME_PAGE_SIZE = 48

const slugifyTheme = (value = '') => encodeURIComponent(String(value || '').trim())

const themePath = (theme) => `/themes/${slugifyTheme(theme.slug || theme.name)}`

function normalizeTheme(theme) {
  const fallback = FALLBACK_BY_NAME[theme.name] || {}
  const keywords = Array.isArray(theme.keywords) && theme.keywords.length ? theme.keywords : (fallback.keywords || [])
  const iconName = theme.icon || fallback.icon

  return {
    ...fallback,
    ...theme,
    slug: theme.slug || fallback.slug || theme.name,
    image: theme.image || theme.image_url || fallback.image_url,
    description: theme.description || fallback.description || '精选主题目的地，适合按兴趣快速规划旅行。',
    guide: theme.guide || fallback.guide || '出发前建议查看景区公告、实时天气和交通接驳安排。',
    keywords,
    season: theme.season || fallback.season || '四季皆宜',
    audience: theme.audience || fallback.audience || '适合周末短途和轻松旅行',
    routeIdea: theme.routeIdea || theme.route_idea || fallback.route_idea || fallback.routeIdea || '选择一个核心景区搭配周边轻量点位，行程更从容。',
    iconName,
    icon: THEME_ICON_MAP[iconName] || Sparkles,
    count: Number(theme.count || 0),
  }
}

function resolveThemeToken(theme, token) {
  if (!theme || !token) return false
  const decoded = decodeURIComponent(token)
  return [theme.slug, theme.name, theme.iconName].filter(Boolean).some(value => String(value) === decoded)
}

export default function ThemesPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { slug = '' } = useParams()
  const searchParams = new URLSearchParams(location.search)
  const activeTheme = slug ? decodeURIComponent(slug) : (searchParams.get('theme') || '')
  const [apiThemes, setApiThemes] = useState([])
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)

  const themes = useMemo(() => {
    const source = apiThemes.length ? apiThemes : FALLBACK_THEMES
    return source.map(normalizeTheme)
  }, [apiThemes])

  const selectedTheme = themes.find(theme => resolveThemeToken(theme, activeTheme))
  const selectedThemeName = selectedTheme?.name || activeTheme
  const selectedThemeTotal = selectedTheme?.count || total
  const themeTotal = themes.reduce((sum, theme) => sum + (theme.count || 0), 0)
  const recommendedThemes = themes.filter(theme => ['赏花踏青', '自然风光', '自驾旅行'].includes(theme.name)).slice(0, 3)
  const otherThemes = themes.filter(theme => theme.name !== selectedTheme?.name).slice(0, 4)
  const featuredItems = items.slice(0, 3)

  useEffect(() => {
    let cancelled = false
    getScenicThemes().then(data => {
      if (cancelled || !Array.isArray(data)) return
      setApiThemes(data)
    })
    return () => { cancelled = true }
  }, [])

  useEffect(() => {
    if (!activeTheme) {
      setItems([])
      setTotal(0)
      return
    }
    let cancelled = false
    setLoading(true)
    getSyncedScenicList(`?theme=${encodeURIComponent(selectedThemeName)}&limit=${THEME_PAGE_SIZE}&offset=0`).then(data => {
      if (cancelled) return
      const nextItems = Array.isArray(data) ? data : (data?.items || [])
      setItems(nextItems)
      setTotal(Array.isArray(data) ? nextItems.length : (data?.total || nextItems.length))
    }).finally(() => {
      if (!cancelled) setLoading(false)
    })
    window.scrollTo(0, 0)
    return () => { cancelled = true }
  }, [activeTheme, selectedThemeName])

  const loadMore = () => {
    if (!activeTheme || loadingMore) return
    setLoadingMore(true)
    getSyncedScenicList(`?theme=${encodeURIComponent(selectedThemeName)}&limit=${THEME_PAGE_SIZE}&offset=${items.length}`).then(data => {
      const nextItems = Array.isArray(data) ? data : (data?.items || [])
      setItems(current => [...current, ...nextItems])
      setTotal(Array.isArray(data) ? items.length + nextItems.length : (data?.total || items.length + nextItems.length))
    }).finally(() => setLoadingMore(false))
  }

  return (
    <div className="themes-page-v2">
      <HeroSection
        variant="display"
        images={activeTheme && selectedTheme ? [selectedTheme.image] : DEFAULT_HERO_IMAGES}
        title={selectedTheme?.name || activeTheme || '按兴趣出发'}
        subtitle={selectedTheme?.description || '主题旅行已接入数据库目录，按兴趣、季节和人群快速找到更合适的目的地。'}
        capsules={!activeTheme ? [
          { title: `${themes.length}`, subtitle: '主题目录' },
          { title: themeTotal ? `${themeTotal.toLocaleString()}+` : '持续补全', subtitle: '主题目的地' }
        ] : []}
      />

      <div style={{ padding: '0 max(20px, calc((100vw - 1200px) / 2))', marginTop: '-40px', position: 'relative', zIndex: 5 }}>
        {!activeTheme ? (
          <div className="stack" style={{ gap: 32 }}>
            <div className="panel" style={{ padding: 32, borderRadius: 20 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
                <Sparkles size={24} style={{ color: 'var(--color-primary)' }} />
                <h2 style={{ margin: 0, fontSize: 20 }}>全部主题索引</h2>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: 20 }}>
                {themes.map(theme => {
                  const Icon = theme.icon
                  return (
                    <button
                      key={theme.slug}
                      onClick={() => navigate(themePath(theme))}
                      className="theme-card-v2"
                      style={{
                        position: 'relative',
                        minHeight: 300,
                        borderRadius: 8,
                        overflow: 'hidden',
                        border: '1px solid var(--color-border)',
                        cursor: 'pointer',
                        textAlign: 'left',
                        padding: 0,
                        background: 'var(--color-surface)',
                      }}
                    >
                      <img src={theme.image} style={{ width: '100%', height: 132, objectFit: 'cover', display: 'block' }} alt="" />
                      <div style={{ padding: 18 }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12, marginBottom: 10 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <Icon size={22} style={{ color: 'var(--color-primary)' }} />
                            <strong style={{ fontSize: 20, fontWeight: 650 }}>{theme.name}</strong>
                          </div>
                          <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>{theme.count ? `${theme.count.toLocaleString()} 个` : '待补充'}</span>
                        </div>
                        <p style={{ fontSize: 13, lineHeight: 1.65, color: 'var(--color-muted)', margin: '0 0 12px' }}>{theme.description}</p>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 12 }}>
                          {theme.keywords.slice(0, 4).map(keyword => (
                            <span key={keyword} style={{ fontSize: 12, padding: '4px 8px', borderRadius: 999, background: 'var(--color-bg-soft)', color: 'var(--color-text)' }}>{keyword}</span>
                          ))}
                        </div>
                        <div style={{ display: 'grid', gap: 6, fontSize: 12, color: 'var(--color-muted)' }}>
                          <span>适游季节：{theme.season}</span>
                          <span>适合人群：{theme.audience}</span>
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            </div>

            <section className="panel" style={{ padding: 32, borderRadius: 20, background: 'var(--color-bg-soft)' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 120px', gap: 32, alignItems: 'center' }}>
                <div>
                  <h3 style={{ margin: '0 0 12px' }}>不知道怎么选？</h3>
                  <p style={{ color: 'var(--color-muted)', fontSize: 14, lineHeight: 1.8, margin: 0 }}>
                    可从当前季节、目的地数量和同行人群入手。{recommendedThemes.length > 0 && `推荐先看 ${recommendedThemes.map(theme => `#${theme.name}`).join('、')}。`}
                  </p>
                  <button
                    className="primary-btn"
                    style={{ marginTop: 18 }}
                    onClick={() => {
                      const next = themes[Math.floor(Math.random() * themes.length)]
                      if (next) navigate(themePath(next))
                    }}
                  >
                    随机探索一个
                  </button>
                </div>
                <div style={{ width: 120, height: 120, borderRadius: '50%', background: 'white', display: 'grid', placeItems: 'center', color: 'var(--color-primary)' }}>
                  <Compass size={48} />
                </div>
              </div>
            </section>
          </div>
        ) : (
          <div className="stack" style={{ gap: 24 }}>
            <div className="panel" style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '16px 24px', borderRadius: 16 }}>
              <button className="ghost-btn" onClick={() => navigate('/themes')} style={{ padding: 4 }}><ChevronRight size={18} style={{ transform: 'rotate(180deg)' }} /></button>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                {selectedTheme && <selectedTheme.icon size={20} style={{ color: 'var(--color-primary)' }} />}
                <h2 style={{ margin: 0, fontSize: 18 }}>{selectedTheme?.name || activeTheme}</h2>
              </div>
              <div style={{ marginLeft: 'auto', fontSize: 14, color: 'var(--color-muted)' }}>
                共找到 {Number(selectedThemeTotal || items.length).toLocaleString()} 个目的地，已显示 {items.length}
              </div>
            </div>

            {selectedTheme && (
              <>
                <div className="panel" style={{ padding: 24, borderRadius: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 24 }}>
                  <div>
                    <h3 style={{ margin: '0 0 10px' }}>主题指南</h3>
                    <p style={{ margin: '0 0 14px', color: 'var(--color-muted)', lineHeight: 1.7 }}>{selectedTheme.guide}</p>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {selectedTheme.keywords.map(keyword => (
                        <span key={keyword} style={{ fontSize: 12, padding: '6px 10px', borderRadius: 999, background: 'var(--color-bg-soft)' }}>{keyword}</span>
                      ))}
                    </div>
                  </div>
                  <div style={{ display: 'grid', gap: 10, fontSize: 13, color: 'var(--color-muted)' }}>
                    <strong style={{ color: 'var(--color-text)' }}>行程建议</strong>
                    <span><CalendarDays size={14} /> 适游季节：{selectedTheme.season}</span>
                    <span><Users size={14} /> 适合人群：{selectedTheme.audience}</span>
                    <span><Route size={14} /> {selectedTheme.routeIdea}</span>
                  </div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 16 }}>
                  {[
                    ['主题目的地', selectedThemeTotal ? `${Number(selectedThemeTotal).toLocaleString()} 个` : '持续补全', MapPinned],
                    ['推荐节奏', selectedTheme.routeIdea.split('，')[0] || '一日一核心景区', Route],
                    ['出行提示', selectedTheme.season, CalendarDays],
                  ].map(([label, value, Icon]) => (
                    <div className="panel" key={label} style={{ padding: 18, borderRadius: 14, minHeight: 112 }}>
                      <Icon size={20} style={{ color: 'var(--color-primary)', marginBottom: 10 }} />
                      <div style={{ color: 'var(--color-muted)', fontSize: 12, marginBottom: 6 }}>{label}</div>
                      <strong style={{ fontSize: 17, lineHeight: 1.45 }}>{value}</strong>
                    </div>
                  ))}
                </div>

                {featuredItems.length > 0 && (
                  <section className="panel" style={{ padding: 24, borderRadius: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 16, marginBottom: 16 }}>
                      <h3 style={{ margin: 0 }}>精选推荐</h3>
                      <Link className="ghost-btn" to={`/destinations?tab=scenic&theme=${encodeURIComponent(selectedTheme.name)}`}>查看全部</Link>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}>
                      {featuredItems.map(item => (
                        <Link key={item.id} to={`/scenic/${item.id}`} style={{ minHeight: 180, borderRadius: 8, overflow: 'hidden', position: 'relative', display: 'block', color: 'white', background: '#24342f' }}>
                          <img src={item.cover_image_url || selectedTheme.image} alt="" style={{ width: '100%', height: '100%', objectFit: 'cover', position: 'absolute', inset: 0, opacity: .72 }} />
                          <div style={{ position: 'absolute', inset: 0, background: 'linear-gradient(180deg, transparent, rgba(0,0,0,.68))' }} />
                          <div style={{ position: 'absolute', left: 16, right: 16, bottom: 14 }}>
                            <strong style={{ fontSize: 17 }}>{item.name}</strong>
                            <p style={{ margin: '6px 0 0', fontSize: 12, lineHeight: 1.55, opacity: .9 }}>{item.city || item.province} · {item.summary || selectedTheme.description}</p>
                          </div>
                        </Link>
                      ))}
                    </div>
                  </section>
                )}
              </>
            )}

            {loading ? (
              <SkeletonList count={6} />
            ) : items.length > 0 ? (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 20 }}>
                  {items.map(item => <ScenicCard scenic={item} key={item.id} />)}
                </div>
                {items.length < selectedThemeTotal && (
                  <div style={{ display: 'flex', justifyContent: 'center', padding: '8px 0 24px' }}>
                    <button className="primary-btn" onClick={loadMore} disabled={loadingMore}>
                      {loadingMore ? '正在加载...' : `继续加载 ${selectedTheme?.name || activeTheme} 目的地`}
                    </button>
                  </div>
                )}
              </>
            ) : (
              <div className="panel" style={{ padding: 60, textAlign: 'center' }}>
                <EmptyState title="暂无结果" text={`未找到符合“${selectedTheme?.name || activeTheme}”主题的景区，请尝试其他分类。`} />
              </div>
            )}

            {otherThemes.length > 0 && (
              <section className="panel" style={{ padding: 24, borderRadius: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
                  <Sparkles size={20} style={{ color: 'var(--color-primary)' }} />
                  <h3 style={{ margin: 0 }}>其他主题推荐</h3>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(190px, 1fr))', gap: 14 }}>
                  {otherThemes.map(theme => {
                    const Icon = theme.icon
                    return (
                      <Link key={theme.slug} to={themePath(theme)} style={{ border: '1px solid var(--color-border)', borderRadius: 8, overflow: 'hidden', background: 'var(--color-surface)' }}>
                        <img src={theme.image} alt="" style={{ width: '100%', height: 90, objectFit: 'cover', display: 'block' }} />
                        <div style={{ padding: 12 }}>
                          <strong style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 14 }}><Icon size={15} /> {theme.name}</strong>
                          <p style={{ margin: '6px 0 0', color: 'var(--color-muted)', fontSize: 12, lineHeight: 1.5 }}>{theme.description}</p>
                        </div>
                      </Link>
                    )
                  })}
                </div>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
