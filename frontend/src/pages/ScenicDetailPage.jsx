import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams, useLocation } from 'react-router-dom'
import { Calendar, Camera, Clock, Heart, MapPin, Navigation, Route, Share2, Star, Upload, Info, BookOpen, Map, MessageCircle, ChevronRight, Phone, Globe, DollarSign, AlertCircle, Users, Eye, Accessibility, BarChart3, ShieldCheck } from 'lucide-react'
import { getScenicNearby, getScenicProfile } from '../api/scenic.js'
import { getScenicComments, postComment, saveFavorite, saveUserRoute, uploadImage } from '../api/user.js'
import { getScenicImageOrPlaceholder, getScenicPlaceholder } from '../api/fallback.js'
import { useAuth } from '../hooks/useAuth.jsx'
import { useToast } from '../hooks/useToast.jsx'
import MapPanel from '../components/common/MapPanel.jsx'
import WeatherCard from '../components/common/WeatherCard.jsx'
import ReviewCard from '../components/common/ReviewCard.jsx'
import StatusBadge from '../components/common/StatusBadge.jsx'
import EmptyState from '../components/common/EmptyState.jsx'
import RouteCard from '../components/common/RouteCard.jsx'
import SectionHeader from '../components/common/SectionHeader.jsx'
import { SkeletonDetail } from '../components/common/Skeleton.jsx'

export default function ScenicDetailPage() {
  const { id } = useParams()
  const location = useLocation()
  const navigate = useNavigate()
  const { user, isLoggedIn } = useAuth()
  const { addToast } = useToast()
  const [item, setItem] = useState(null)
  const [comments, setComments] = useState([])
  const [nearby, setNearby] = useState([])
  const [mainImage, setMainImage] = useState('')
  const [favorite, setFavorite] = useState(false)
  const [draft, setDraft] = useState('')
  const [rating, setRating] = useState(5)
  const [activeTab, setActiveTab] = useState('intro')
  const numericScenicId = Number(id)
  const isFormalScenic = Number.isInteger(numericScenicId) && String(numericScenicId) === String(id)

  useEffect(() => {
    getScenicProfile(id).then(data => {
      setItem(data)
      setMainImage(getScenicImageOrPlaceholder(data))
    })
    if (String(id).startsWith('jingdian-')) {
      setComments([])
    } else {
      getScenicComments(id).then(data => setComments(data?.items || data || []))
    }
    getScenicNearby(id).then(data => setNearby(data || [])).catch(() => setNearby([]))
    window.scrollTo(0, 0)
  }, [id])

  const gallery = useMemo(() => {
    const images = [item?.cover_image_url, ...(item?.gallery || [])].filter(i => i && i.startsWith('http'))
    if (images.length > 0) return Array.from(new Set(images)).slice(0, 5)
    return Array.from({ length: 3 }, () => getScenicPlaceholder(item))
  }, [item])

  const submitComment = async (event) => {
    event.preventDefault()
    if (!draft.trim()) return addToast('请先填写评论内容', 'warning')
    if (!isFormalScenic) return addToast('源表景点需先采纳到正式景区库后再评论', 'warning')
    if (!isLoggedIn) return addToast('请先登录后再评论', 'warning')
    const created = await postComment({ scenic_id: numericScenicId, content: draft.trim(), rating })
    if (created) {
      setComments(current => [{ id: created?.id || Date.now(), scenic_id: numericScenicId, nickname: user?.nickname || '用户', content: draft.trim(), rating, status: 'pending' }, ...current])
      setDraft('')
      addToast('评论已提交，等待审核', 'success')
    } else {
      addToast('评论提交失败', 'error')
    }
  }

  const submitUpload = async (event) => {
    if (!isLoggedIn) return addToast('请先登录', 'warning')
    if (!isFormalScenic) return addToast('源表景点需先采纳到正式景区库后再上传图片', 'warning')
    const fileInput = document.querySelector('#scenic-upload-input')
    if (fileInput?.files?.length) {
      const formData = new FormData()
      formData.append('file', fileInput.files[0])
      formData.append('scenic_id', String(numericScenicId))
      const created = await uploadImage(formData)
      addToast(created?.status === 'rejected' ? '图片未通过质检' : '图片已提交审核', created?.status === 'rejected' ? 'error' : 'success')
      fileInput.value = ''
    } else {
      addToast('请先选择文件', 'warning')
    }
  }

  const toggleFavorite = async () => {
    if (!isLoggedIn) return addToast('请先登录后再收藏', 'warning')
    if (!isFormalScenic) return addToast('源表景点需先采纳到正式景区库后再收藏', 'warning')
    const next = !favorite
    setFavorite(next)
    try {
      const result = await saveFavorite({ scenic_id: numericScenicId })
      addToast(result?.status === 'removed' ? '已取消收藏' : '已加入收藏', 'success')
    } catch {
      setFavorite(!next)
      addToast('收藏操作失败，请稍后重试', 'error')
    }
  }

  const addToTrip = async () => {
    if (!isLoggedIn) return addToast('请先登录后再加入行程', 'warning')
    const result = await saveUserRoute({
      title: `${item.name} 游玩路线`,
      transport: '自驾',
      stops: ['我的位置', item.name],
      distance_km: 0,
      duration_hours: 0,
      payload: {
        scenic_id: isFormalScenic ? numericScenicId : null,
        destination: item.name,
        province: item.province,
        city: item.city,
        latitude: item.latitude,
        longitude: item.longitude,
      },
    })
    addToast(result?.id ? '已加入我的路线' : '路线保存完成', 'success')
  }

  if (!item) return <SkeletonDetail />

  const imageFallback = getScenicPlaceholder(item)
  const approvedMedia = Array.isArray(item.media_assets) ? item.media_assets : []
  const mediaByUrl = Object.fromEntries(approvedMedia.map(media => [media.url, media]))
  const setFallbackImage = (event) => {
    event.currentTarget.onerror = null
    event.currentTarget.src = imageFallback
  }

  const TABS = [
    { id: 'intro', label: '景区概览', icon: Info },
    { id: 'guide', label: '实用攻略', icon: BookOpen },
    { id: 'routes', label: '推荐路线', icon: Map },
    { id: 'reviews', label: '游客点评', icon: MessageCircle },
  ]

  return (
    <div className="scenic-detail-v2">
      <div className="breadcrumb" style={{ marginBottom: 24, fontSize: 13, color: 'var(--color-muted)' }}>
        <Link to="/" style={{ color: 'inherit' }}>首页</Link> 
        <ChevronRight size={12} style={{ margin: '0 8px' }} /> 
        <Link to="/destinations" style={{ color: 'inherit' }}>探索中国</Link>
        <ChevronRight size={12} style={{ margin: '0 8px' }} /> 
        <span style={{ color: 'var(--color-text)' }}>{item.name}</span>
      </div>

      <section className="detail-hero" style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: 32, marginBottom: 32 }}>
        <div className="hero-gallery">
          <div style={{ height: 400, borderRadius: 16, overflow: 'hidden', marginBottom: 12 }}>
            <img src={mainImage} onError={setFallbackImage} loading="eager" decoding="async" style={{ width: '100%', height: '100%', objectFit: 'cover' }} alt="" />
          </div>
          <div style={{ display: 'flex', gap: 12, overflowX: 'auto' }}>
            {gallery.map((src, i) => (
              <button key={i} aria-label={`预览第 ${i + 1} 张景区图片`} aria-pressed={mainImage === src} onClick={() => setMainImage(src)} style={{ flex: '0 0 100px', height: 70, borderRadius: 8, overflow: 'hidden', border: mainImage === src ? '2px solid var(--color-primary)' : 'none', padding: 0 }}>
                <img src={src} onError={setFallbackImage} loading="lazy" decoding="async" style={{ width: '100%', height: '100%', objectFit: 'cover' }} alt="" />
              </button>
            ))}
          </div>
          {mediaByUrl[mainImage]?.source && (
            <div style={{ marginTop: 10, fontSize: 12, color: 'var(--color-muted)', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <span>图片来源：{mediaByUrl[mainImage].source}</span>
              {mediaByUrl[mainImage].license && <span>授权：{mediaByUrl[mainImage].license}</span>}
              {mediaByUrl[mainImage].attribution && <span>署名：{mediaByUrl[mainImage].attribution}</span>}
            </div>
          )}
        </div>

        <div className="hero-info" style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
                <h1 style={{ fontSize: 32, margin: 0 }}>{item.name}</h1>
                {item.level && <StatusBadge tone="orange">{item.level} 景区</StatusBadge>}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, color: 'var(--color-muted)', fontSize: 14 }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}><Star size={16} fill="#FBBF24" color="#FBBF24" /> <strong>{item.rating || '5.0'}</strong></span>
                <span>{comments.length} 条评价</span>
                <span>{item.province} · {item.city}</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: 12 }}>
              <button className="ghost-btn" aria-label={favorite ? '取消收藏景区' : '收藏景区'} aria-pressed={favorite} style={{ borderRadius: '50%', width: 44, height: 44, padding: 0 }} onClick={toggleFavorite}>
                <Heart size={20} fill={favorite ? 'var(--color-danger)' : 'none'} color={favorite ? 'var(--color-danger)' : 'currentColor'} />
              </button>
              <button className="ghost-btn" aria-label="分享景区链接" style={{ borderRadius: '50%', width: 44, height: 44, padding: 0 }} onClick={() => { navigator.clipboard.writeText(window.location.href); addToast('链接已复制', 'success') }}>
                <Share2 size={20} />
              </button>
            </div>
          </div>

          <p style={{ fontSize: 16, color: 'var(--color-text-soft)', lineHeight: 1.6, margin: '24px 0' }}>
            {item.summary || '暂无简介'}
          </p>

          <div className="quick-facts" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 32 }}>
            <div style={{ padding: 16, background: 'var(--color-bg-soft)', borderRadius: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-muted)', fontSize: 12, marginBottom: 4 }}><Clock size={14}/> 开放时间</div>
              <strong>{item.opening_hours || '08:00 - 18:00'}</strong>
            </div>
            <div style={{ padding: 16, background: 'var(--color-bg-soft)', borderRadius: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-muted)', fontSize: 12, marginBottom: 4 }}><DollarSign size={14}/> 门票参考</div>
              <strong>{item.ticket_price || '免费'}</strong>
            </div>
            <div style={{ padding: 16, background: 'var(--color-bg-soft)', borderRadius: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-muted)', fontSize: 12, marginBottom: 4 }}><Calendar size={14}/> 最佳季节</div>
              <strong>{item.best_season || '四季皆宜'}</strong>
            </div>
            <div style={{ padding: 16, background: 'var(--color-bg-soft)', borderRadius: 12 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--color-muted)', fontSize: 12, marginBottom: 4 }}><Clock size={14}/> 建议游玩时长</div>
              <strong>{item.recommended_duration || '待更新'}</strong>
            </div>
          </div>

          <div style={{ marginTop: 'auto', display: 'flex', gap: 16 }}>
            <button className="primary-btn" style={{ flex: 1, padding: '14px' }} onClick={() => navigate(`/trip-planning?tab=map&to=${encodeURIComponent(item.name)}`)}>
              <Navigation size={18} /> 开始规划路线
            </button>
            <button className="ghost-btn" style={{ flex: 1, padding: '14px' }} onClick={addToTrip}>
              <Route size={18} /> 加入我的行程
            </button>
          </div>
        </div>
      </section>

      <div className="detail-content-layout" style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 32 }}>
        <main>
          <div className="tab-nav panel" style={{ display: 'flex', gap: 32, padding: '0 24px', marginBottom: 24, position: 'sticky', top: 80, zIndex: 10 }}>
            {TABS.map(tab => (
              <button key={tab.id} className={`tab-item ${activeTab === tab.id ? 'active' : ''}`} onClick={() => setActiveTab(tab.id)} style={{ padding: '20px 0', background: 'none', border: 'none', fontSize: 15, fontWeight: 600, color: activeTab === tab.id ? 'var(--color-primary)' : 'var(--color-muted)', borderBottom: activeTab === tab.id ? '2px solid var(--color-primary)' : '2px solid transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 8 }}>
                <tab.icon size={18} /> {tab.label}
              </button>
            ))}
          </div>

          {activeTab === 'intro' && (
            <div className="stack" style={{ gap: 32 }}>
              <section className="panel" style={{ padding: 32 }}>
                <SectionHeader title="景区详情" />
                <div style={{ lineHeight: 1.8, fontSize: 16, color: 'var(--color-text-soft)' }}>
                  {item.description || '详细介绍正在补全中...'}
                </div>
                {item.tags?.length > 0 && (
                  <div className="tag-row" style={{ marginTop: 24 }}>
                    {item.tags.map(tag => <span key={tag} className="tag" style={{ background: 'var(--color-bg-soft)', padding: '6px 12px', borderRadius: 8, fontSize: 13 }}>{tag}</span>)}
                  </div>
                )}
              </section>

              <section className="panel" style={{ padding: 32 }}>
                <SectionHeader title="历史文化" />
                <p style={{ lineHeight: 1.8 }}>{item.history_culture || '该景区的历史底蕴深厚，承载着丰富的地域文化。'}</p>
                <div style={{ marginTop: 20, padding: 20, background: 'var(--color-primary-soft)', borderRadius: 12 }}>
                  <strong style={{ color: 'var(--color-primary)', display: 'block', marginBottom: 8 }}>核心看点</strong>
                  <p style={{ margin: 0, fontSize: 14 }}>{item.highlights || '精选景观与特色体验待您探索。'}</p>
                </div>
              </section>

              {item.suitable_groups?.length > 0 && (
                <section className="panel" style={{ padding: 32 }}>
                  <SectionHeader title="适合人群" />
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
                    {item.suitable_groups.map(g => (
                      <span key={g} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: '#F0FDF4', color: '#166534', borderRadius: 999, fontSize: 14, fontWeight: 500 }}>
                        <Users size={14} /> {g}
                      </span>
                    ))}
                  </div>
                </section>
              )}

              {item.must_see_spots?.length > 0 && (
                <section className="panel" style={{ padding: 32 }}>
                  <SectionHeader title="必看景点" />
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
                    {item.must_see_spots.map((spot, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: 'var(--color-bg-soft)', borderRadius: 10, fontSize: 14 }}>
                        <Eye size={14} style={{ color: 'var(--color-primary)', flexShrink: 0 }} /> {spot}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              {item.photo_spots?.length > 0 && (
                <section className="panel" style={{ padding: 32 }}>
                  <SectionHeader title="拍照打卡" />
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: 10 }}>
                    {item.photo_spots.map((spot, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', background: '#FEF3C7', color: '#92400E', borderRadius: 10, fontSize: 14 }}>
                        <Camera size={14} style={{ flexShrink: 0 }} /> {spot}
                      </div>
                    ))}
                  </div>
                </section>
              )}

              <section className="panel" style={{ padding: 32 }}>
                <SectionHeader title="用户实拍" />
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
                  {gallery.slice(0, 8).map((src, i) => <img key={i} src={src} onError={setFallbackImage} loading="lazy" decoding="async" style={{ width: '100%', height: 120, objectFit: 'cover', borderRadius: 8 }} alt="" />)}
                </div>
                <p style={{ margin: '0 0 16px', color: 'var(--color-muted)', fontSize: 13 }}>
                  图片优先展示后台审核通过的外链/CDN 资源，本地只保存 URL、来源、授权和质量分，不存储原图文件。
                </p>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px', background: 'var(--color-bg-soft)', borderRadius: 12 }}>
                  <span style={{ fontSize: 14, color: 'var(--color-muted)' }}>分享你的精彩瞬间</span>
                  <label className="primary-btn" style={{ padding: '8px 16px', fontSize: 13, cursor: 'pointer' }}>
                    <Upload size={14} /> 上传图片
                    <input id="scenic-upload-input" type="file" accept="image/*" style={{ display: 'none' }} onChange={submitUpload} />
                  </label>
                </div>
              </section>
            </div>
          )}

          {activeTab === 'guide' && (
            <div className="stack" style={{ gap: 32 }}>
              <section className="panel" style={{ padding: 32 }}>
                <SectionHeader title="基本信息" />
                <div style={{ display: 'grid', gap: 20 }}>
                  <div style={{ display: 'flex', gap: 12 }}><Phone size={18} style={{ color: 'var(--color-primary)' }}/> <div><strong>咨询电话</strong><p style={{ margin: '4px 0 0', color: 'var(--color-muted)' }}>{item.phone || '暂无'}</p></div></div>
                  <div style={{ display: 'flex', gap: 12 }}><MapPin size={18} style={{ color: 'var(--color-primary)' }}/> <div><strong>详细地址</strong><p style={{ margin: '4px 0 0', color: 'var(--color-muted)' }}>{item.address}</p></div></div>
                  {item.official_website && <div style={{ display: 'flex', gap: 12 }}><Globe size={18} style={{ color: 'var(--color-primary)' }}/> <div><strong>官方网站</strong><p style={{ margin: '4px 0 0' }}><a href={item.official_website} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-primary)' }}>点击访问官方平台</a></p></div></div>}
                </div>
              </section>

              <section className="panel" style={{ padding: 32 }}>
                <SectionHeader title="交通与停车" />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32 }}>
                  <div>
                    <strong style={{ display: 'block', marginBottom: 12 }}>公共交通</strong>
                    <p style={{ fontSize: 14, color: 'var(--color-text-soft)', lineHeight: 1.6 }}>{item.public_transport || item.traffic_info || '建议使用地图导航获取实时公交/地铁线路。'}</p>
                  </div>
                  <div>
                    <strong style={{ display: 'block', marginBottom: 12 }}>自驾停车</strong>
                    <p style={{ fontSize: 14, color: 'var(--color-text-soft)', lineHeight: 1.6 }}>{item.parking_info || '景区周边设有停车场，节假日建议提前规划。'}</p>
                  </div>
                </div>
                {item.self_driving_route && (
                  <div style={{ marginTop: 20, padding: 16, background: '#F0F9FF', borderRadius: 12 }}>
                    <strong style={{ display: 'block', marginBottom: 8, color: '#0369A1' }}>自驾路线建议</strong>
                    <p style={{ margin: 0, fontSize: 14, color: 'var(--color-text-soft)', lineHeight: 1.6 }}>{item.self_driving_route}</p>
                  </div>
                )}
              </section>

              {item.accessibility_tips && (
                <section className="panel" style={{ padding: 32 }}>
                  <SectionHeader title="无障碍信息" />
                  <div style={{ display: 'flex', gap: 12, padding: 16, background: '#F0FDF4', borderRadius: 12, color: '#166534' }}>
                    <Accessibility size={18} style={{ flexShrink: 0, marginTop: 2 }} />
                    <span style={{ fontSize: 14, lineHeight: 1.6 }}>{item.accessibility_tips}</span>
                  </div>
                </section>
              )}

              <section className="panel" style={{ padding: 32 }}>
                <SectionHeader title="旅行贴士" />
                <div style={{ display: 'grid', gap: 16 }}>
                  {item.travel_tips?.length ? item.travel_tips.map((tip, i) => (
                    <div key={i} style={{ display: 'flex', gap: 12, padding: 16, background: '#FFF7ED', borderRadius: 12, color: '#9A3412' }}>
                      <AlertCircle size={18} />
                      <span style={{ fontSize: 14 }}>{tip}</span>
                    </div>
                  )) : <p>暂无特别提示，祝您旅途愉快！</p>}
                </div>
              </section>
            </div>
          )}

          {activeTab === 'routes' && (
            <div className="stack" style={{ gap: 32 }}>
              <section className="panel" style={{ padding: 32 }}>
                <SectionHeader title="官方推荐线路" />
                <div className="stack" style={{ gap: 24 }}>
                  {item.recommended_routes?.map((routeStr, i) => (
                    <div key={i} className="route-v2-card" style={{ padding: 24, border: '1px solid var(--color-border)', borderRadius: 16 }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                        <strong style={{ fontSize: 18 }}>路线 {i + 1}</strong>
                        <span className="status-badge">约 {item.recommended_duration || '4-6 小时'}</span>
                      </div>
                      <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                        {typeof routeStr === 'string' ? routeStr.split(/[-—→]/).map((s, idx, arr) => (
                          <span key={idx} style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                            <span style={{ padding: '8px 16px', background: 'var(--color-bg-soft)', borderRadius: 10, fontSize: 14 }}>{s.trim()}</span>
                            {idx < arr.length - 1 && <ChevronRight size={14} style={{ color: 'var(--color-muted)' }} />}
                          </span>
                        )) : '路线详情生成中'}
                      </div>
                    </div>
                  ))}
                </div>
              </section>

              {item.recommended_itinerary?.length > 0 && (
                <section className="panel" style={{ padding: 32 }}>
                  <SectionHeader title="推荐行程" />
                  <div className="stack" style={{ gap: 16 }}>
                    {item.recommended_itinerary.map((day, i) => (
                      <div key={i} style={{ padding: 20, background: 'var(--color-bg-soft)', borderRadius: 12 }}>
                        <strong style={{ display: 'block', marginBottom: 8, color: 'var(--color-primary)' }}>
                          {typeof day === 'object' ? day.title || `第 ${i + 1} 天` : `第 ${i + 1} 天`}
                        </strong>
                        <p style={{ margin: 0, fontSize: 14, color: 'var(--color-text-soft)', lineHeight: 1.6 }}>
                          {typeof day === 'object' ? day.content || day.description || JSON.stringify(day) : String(day)}
                        </p>
                      </div>
                    ))}
                  </div>
                </section>
              )}
            </div>
          )}

          {activeTab === 'reviews' && (
            <div className="stack" style={{ gap: 32 }}>
              <section className="panel" style={{ padding: 32 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
                  <SectionHeader title={`全部评论 (${comments.length})`} />
                  <button className="primary-btn" onClick={() => document.getElementById('comment-form').scrollIntoView({ behavior: 'smooth' })}>写点评</button>
                </div>
                <div className="stack" style={{ gap: 20 }}>
                  {comments.length ? comments.map(c => <ReviewCard item={c} key={c.id} />) : <EmptyState title="暂无点评" text="成为第一位分享体验的游客。" />}
                </div>
              </section>

              <section id="comment-form" className="panel" style={{ padding: 32 }}>
                <SectionHeader title="发表你的评价" />
                <form onSubmit={submitComment}>
                  <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 20 }}>
                    <span>总体评价</span>
                    <div style={{ display: 'flex', gap: 4 }}>
                      {[1, 2, 3, 4, 5].map(s => (
                        <button key={s} type="button" onClick={() => setRating(s)} style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}>
                          <Star size={24} fill={s <= rating ? '#FBBF24' : 'none'} color={s <= rating ? '#FBBF24' : '#D1D5DB'} />
                        </button>
                      ))}
                    </div>
                  </div>
                  <textarea 
                    value={draft} 
                    onChange={e => setDraft(e.target.value)} 
                    placeholder="分享您的游玩感受、交通建议或避雷指南..." 
                    style={{ width: '100%', height: 120, padding: 16, borderRadius: 12, border: '1px solid var(--color-border)', fontSize: 15, marginBottom: 20, outline: 'none' }}
                  />
                  <button className="primary-btn" style={{ padding: '12px 32px' }}>提交评价</button>
                </form>
              </section>
            </div>
          )}
        </main>

        <aside className="stack" style={{ gap: 32 }}>
          <section className="panel" style={{ padding: 20 }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: 16 }}>景区位置</h3>
            <div style={{ height: 200, borderRadius: 12, overflow: 'hidden', marginBottom: 12 }}>
              <MapPanel compact title="" city={item.city} />
            </div>
            <p style={{ fontSize: 13, color: 'var(--color-muted)', display: 'flex', gap: 6 }}><MapPin size={14} /> {item.address}</p>
          </section>

          <WeatherCard weather={item.weather} />

          <section className="panel" style={{ padding: 20 }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: 16 }}>附近推荐</h3>
            <div className="stack" style={{ gap: 12 }}>
              {nearby.slice(0, 4).map(row => (
                <Link to={`/scenic/${row.recommended_scenic_id}`} key={row.recommended_scenic_id} style={{ display: 'flex', gap: 12, textDecoration: 'none', color: 'inherit' }}>
                  <img src={row.cover_image_url || imageFallback} onError={setFallbackImage} loading="lazy" decoding="async" style={{ width: 60, height: 60, borderRadius: 8, objectFit: 'cover' }} alt="" />
                  <div style={{ flex: 1 }}>
                    <strong style={{ display: 'block', fontSize: 14 }}>{row.name}</strong>
                    <small style={{ color: 'var(--color-muted)', fontSize: 11 }}>{row.distance_text} · {row.reason}</small>
                  </div>
                </Link>
              ))}
            </div>
          </section>

          <section className="panel" style={{ padding: 20 }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: 16, display: 'flex', alignItems: 'center', gap: 8 }}><BarChart3 size={16} /> 数据信息</h3>
            {item.completeness_score > 0 && (
              <div style={{ marginBottom: 14 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, color: 'var(--color-muted)', marginBottom: 6 }}>
                  <span>资料完整度</span>
                  <span style={{ fontWeight: 600, color: item.completeness_score >= 80 ? '#16A34A' : item.completeness_score >= 50 ? '#D97706' : '#EF4444' }}>{item.completeness_score}%</span>
                </div>
                <div style={{ height: 6, background: 'var(--color-border)', borderRadius: 3, overflow: 'hidden' }}>
                  <div style={{ height: '100%', width: `${item.completeness_score}%`, background: item.completeness_score >= 80 ? '#16A34A' : item.completeness_score >= 50 ? '#D97706' : '#EF4444', borderRadius: 3, transition: 'width .3s' }} />
                </div>
              </div>
            )}
            <div style={{ display: 'grid', gap: 10, fontSize: 13, color: 'var(--color-muted)' }}>
              {item.data_source_note && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <ShieldCheck size={14} style={{ flexShrink: 0, marginTop: 2, color: 'var(--color-primary)' }} />
                  <span>{item.data_source_note}</span>
                </div>
              )}
              {item.image_policy && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                  <ShieldCheck size={14} style={{ flexShrink: 0, marginTop: 2, color: 'var(--color-primary)' }} />
                  <span>图片策略：已审核外链优先，本地轻量索引，缺图自动降级占位。</span>
                </div>
              )}
              {item.last_enriched_at && (
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <Clock size={14} style={{ flexShrink: 0 }} />
                  <span>最近更新：{new Date(item.last_enriched_at).toLocaleDateString('zh-CN')}</span>
                </div>
              )}
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
