import { useEffect, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { AlertTriangle, Bus, Camera, CloudSun, Map as MapIcon, Navigation, Plane, Share2, Save, Car, Train, Footprints, Shirt, ShieldCheck, Umbrella, ThermometerSun, Wind, Droplets, X } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import HeroSection from '../components/common/HeroSection.jsx'
import SectionHeader from '../components/common/SectionHeader.jsx'
import EmptyState from '../components/common/EmptyState.jsx'
import { getWeather, getWeatherForecast } from '../api/weather.js'
import { request } from '../api/client.js'
import { useToast } from '../hooks/useToast.jsx'
import MapPanel from '../components/common/MapPanel.jsx'
import { geocodeAddress, getMapRoute } from '../api/map.js'
import { createWeatherInsights } from '../utils/weatherInsights.js'
import { buildRouteMapModel, estimateRouteCosts } from '../utils/routeDetails.js'

const routeModes = [
  { key: 'driving', label: '汽车自驾', icon: Car, note: '灵活停靠，适合周边和亲子出行' },
  { key: 'transit', label: '公交地铁', icon: Bus, note: '市内换乘，适合低成本出行' },
  { key: 'walking', label: '步行', icon: Footprints, note: '短距离景区周边慢游' },
  { key: 'train', label: '高铁动车', icon: Train, note: '跨城高效，含进出站时间估算' },
  { key: 'flight', label: '飞机', icon: Plane, note: '远距离跨省，含机场换乘时间估算' },
]

const weatherInsightIcons = {
  travel: ShieldCheck,
  comfort: ThermometerSun,
  photo: Camera,
  gear: Shirt,
}

const VALID_TABS = new Set(['map', 'weather'])

function normalizeTab(tab) {
  return VALID_TABS.has(tab) ? tab : 'map'
}

function parseTempRange(value = '') {
  const text = String(value).replace(/°C|℃/gi, '').trim()
  const range = text.match(/^(-?\d+)\s*(?:-|~|至)\s*(-?\d+)$/)
  const numbers = range ? [Number(range[1]), Number(range[2])] : (text.match(/-?\d+/g)?.map(Number) || [])
  if (numbers.length >= 2) return { low: Math.min(numbers[0], numbers[1]), high: Math.max(numbers[0], numbers[1]) }
  if (numbers.length === 1) return { low: numbers[0] - 3, high: numbers[0] + 3 }
  return { low: 0, high: 0 }
}

function normalizeForecast(items = []) {
  return items.map((item, index) => {
    const range = parseTempRange(item.temp || `${item.nighttemp || ''}-${item.daytemp || ''}`)
    return {
      day: item.day || item.date || `第 ${index + 1} 天`,
      condition: item.condition || item.day_weather || item.dayweather || '多云',
      low: range.low,
      high: range.high,
    }
  })
}

function formatDuration(minutes = 0) {
  const value = Number(minutes) || 0
  if (value < 60) return `${Math.max(1, Math.round(value))} 分钟`
  const hours = Math.floor(value / 60)
  const rest = Math.round(value % 60)
  return rest ? `${hours} 小时 ${rest} 分钟` : `${hours} 小时`
}

export default function TripPlanningPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const { addToast } = useToast()
  const searchParams = new URLSearchParams(location.search)
  
  const initialTab = normalizeTab(searchParams.get('tab') || 'map')
  const [activeTab, setActiveTab] = useState(initialTab)
  const [searchCity, setSearchCity] = useState(searchParams.get('city') || '苏州市')
  
  // Weather State
  const [weatherCurrent, setWeatherCurrent] = useState(null)
  const [forecast, setForecast] = useState([])
  const [weatherLoading, setWeatherLoading] = useState(false)

  // Map State
  const [mapLayer, setMapLayer] = useState('standard')
  const [startInput, setStartInput] = useState(searchParams.get('from') || '苏州')
  const [endInput, setEndInput] = useState(searchParams.get('to') || '杭州西湖')
  const [routeConfig, setRouteConfig] = useState({ start: '', end: '' })
  const [routeLoading, setRouteLoading] = useState(false)
  const [routeResults, setRouteResults] = useState([])
  const [selectedMode, setSelectedMode] = useState('')
  const [selectedRouteDetail, setSelectedRouteDetail] = useState(null)

  // Sync tab state with URL
  useEffect(() => {
    const rawTab = searchParams.get('tab') || 'map'
    const currentTab = normalizeTab(rawTab)
    if (rawTab !== currentTab) {
      const nextParams = new URLSearchParams(location.search)
      nextParams.set('tab', currentTab)
      navigate(`/trip-planning?${nextParams.toString()}`, { replace: true })
      return
    }
    if (activeTab !== currentTab) setActiveTab(currentTab)
  }, [location.search])

  useEffect(() => {
    const params = new URLSearchParams(location.search)
    const city = params.get('city')
    const from = params.get('from')
    const to = params.get('to')
    if (city && city !== searchCity) setSearchCity(city)
    if (from && from !== startInput) setStartInput(from)
    if (to && to !== endInput) setEndInput(to)
  }, [location.search])

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    const newParams = new URLSearchParams(location.search)
    newParams.set('tab', tab)
    navigate(`/trip-planning?${newParams.toString()}`)
  }

  useEffect(() => {
    if (activeTab === 'weather') {
      setWeatherLoading(true)
      Promise.all([
        getWeather(searchCity),
        getWeatherForecast(searchCity)
      ]).then(([weather, fore]) => {
        if (weather) {
          setWeatherCurrent(weather)
          setForecast(normalizeForecast(weather.forecast || fore || []))
        } else {
          setWeatherCurrent(null)
          setForecast(normalizeForecast(fore || []))
        }
      }).finally(() => setWeatherLoading(false))
    }
  }, [activeTab, searchCity])

  const handleSearch = (e) => {
    e.preventDefault()
    const form = new FormData(e.target)
    const city = form.get('city')
    if(city) setSearchCity(city)
  }

  const handlePlanRoute = async () => {
    if (!startInput.trim() || !endInput.trim()) return
    setRouteLoading(true)
    setSelectedRouteDetail(null)
    setRouteConfig({ start: startInput.trim(), end: endInput.trim() })
    const origin = await geocodeAddress(startInput.trim())
    const destination = await geocodeAddress(endInput.trim())
    if (!origin?.lng || !destination?.lng) {
      setRouteResults([])
      setSelectedRouteDetail(null)
      setRouteLoading(false)
      return
    }
    const originText = `${origin.lng},${origin.lat}`
    const destinationText = `${destination.lng},${destination.lat}`
    const results = await Promise.all(routeModes.map(async mode => {
      const route = await getMapRoute({ origin: originText, destination: destinationText, mode: mode.key })
      return { ...mode, route }
    }))
    setRouteResults(results.filter(item => item.route))
    setRouteLoading(false)
  }

  const handleSaveRoute = async () => {
    if (!startInput.trim() || !endInput.trim()) return addToast('请先填写出发地和目的地', 'warning')
    const saved = await request('/api/user/routes', {
      method: 'POST',
      body: JSON.stringify({
        title: `${startInput.trim()} → ${endInput.trim()}`,
        transport: selectedMode || 'driving',
        stops: [startInput.trim(), endInput.trim()],
      }),
    })
    if (saved) {
      addToast('路线已保存到我的路线', 'success')
    } else {
      addToast('请先登录后再保存', 'warning')
    }
  }

  const weatherInsights = weatherCurrent ? createWeatherInsights(weatherCurrent, forecast) : null
  const selectedModeLabel = routeModes.find(mode => mode.key === selectedMode)?.label || '全部方式'
  const routeDetailCosts = selectedRouteDetail ? estimateRouteCosts(selectedRouteDetail.route, selectedRouteDetail.key) : []
  const routeDetailCostMax = Math.max(1, ...routeDetailCosts.map(item => item.value))
  const routeDetailCostTotal = routeDetailCosts.reduce((sum, item) => sum + item.value, 0)
  const routeMapModel = selectedRouteDetail ? buildRouteMapModel(selectedRouteDetail.route?.points, startInput.trim(), endInput.trim()) : null

  return (
    <div className="trip-planning-page">
      <HeroSection 
        variant="display"
        images={[
          'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?auto=format&fit=crop&w=1920&q=80',
          'https://images.unsplash.com/photo-1501785888041-af3ef285b470?auto=format&fit=crop&w=1920&q=80'
        ]}
        title="行程与天气"
        subtitle="路线规划、地图图层与实况天气预报"
        capsules={[]}
      />

      <div className="floating-tab-shell">
        <div className="tab-nav panel app-tab-nav" role="tablist" aria-label="行程规划工具">
           <button className={`ghost-btn ${activeTab === 'map' ? 'active' : ''}`} type="button" role="tab" aria-selected={activeTab === 'map'} onClick={() => handleTabChange('map')}>
             <MapIcon size={18}/> 地图规划
           </button>
           <button className={`ghost-btn ${activeTab === 'weather' ? 'active' : ''}`} type="button" role="tab" aria-selected={activeTab === 'weather'} onClick={() => handleTabChange('weather')}>
             <CloudSun size={18}/> 天气实况
           </button>
        </div>
      </div>

      <div className="page-content page-content-wide">
        
        {activeTab === 'map' && (
          <div className="map-planning-layout">
             <aside className="panel stack route-planner-panel">
                <SectionHeader title="路线规划" />
                <div className="input-group">
                   <label htmlFor="route-start">出发地</label>
                   <input id="route-start" value={startInput} onChange={e => setStartInput(e.target.value)} placeholder="输入起点" className="form-input"/>
                </div>
                <div className="input-group">
                   <label htmlFor="route-end">目的地</label>
                   <input id="route-end" value={endInput} onChange={e => setEndInput(e.target.value)} placeholder="输入终点" className="form-input"/>
                </div>
                <button className="primary-btn" onClick={handlePlanRoute} style={{width:'100%', marginTop:'10px'}}><Navigation size={16}/> 开始规划</button>
                
                <div className="route-mode-grid">
                  {routeModes.map(({ key, label, icon: Icon }) => (
	                    <button
	                      type="button"
	                      key={key}
	                      className={`route-mode-chip ${selectedMode === key ? 'active' : ''}`}
	                      aria-pressed={selectedMode === key}
	                      onClick={() => setSelectedMode(selectedMode === key ? '' : key)}
	                      style={selectedMode === key ? { background: 'var(--color-primary)', color: '#fff', borderColor: 'var(--color-primary)' } : {}}
	                    >
                      <Icon size={16} />
                      {label}
                    </button>
                  ))}
                </div>
                <p aria-live="polite" style={{ margin: '4px 0 0', fontSize: 13, color: 'var(--color-muted)' }}>
                  当前方式：{selectedModeLabel}
                </p>

                {routeLoading && <div className="notice">正在计算多种交通方案...</div>}
                {routeResults.length > 0 && (
                  <div className="route-result-list">
                    {routeResults.filter(r => !selectedMode || r.key === selectedMode).map(({ key, label, icon: Icon, note, route }) => (
                      <button
                        type="button"
                        key={key}
                        className="route-option-card"
                        onClick={() => setSelectedRouteDetail({ key, label, note, route })}
                      >
                        <div>
                          <Icon size={20} />
                          <strong>{label}</strong>
                        </div>
                        <p>{note}</p>
                        <div className="route-option-meta">
                          <span>{route.distance_km} km</span>
                          <span>{formatDuration(route.duration_minutes)}</span>
                        </div>
                        <small>{route.traffic}</small>
                      </button>
                    ))}
                  </div>
                )}

                <hr className="soft-divider"/>
                
                <div className="layer-controls">
                   <strong>图层切换</strong>
                   <div className="chip-row" style={{marginTop:'10px'}}>
                      <button className={mapLayer === 'standard' ? 'active' : ''} onClick={() => setMapLayer('standard')}>标准地图</button>
                      <button className={mapLayer === 'satellite' ? 'active' : ''} onClick={() => setMapLayer('satellite')}>卫星影像</button>
                   </div>
                </div>

                <div className="action-buttons" style={{display:'flex', gap:'10px', marginTop:'20px'}}>
                   <button className="ghost-btn" style={{flex:1}} onClick={handleSaveRoute}><Save size={16}/> 保存</button>
                   <button className="ghost-btn" style={{flex:1}} onClick={() => { navigator.clipboard.writeText(window.location.href); addToast('链接已复制', 'success') }}><Share2 size={16}/> 分享</button>
                </div>
             </aside>
             <main>
                <div className="panel map-stage-panel">
                   <MapPanel title="" compact={false} startPoint={routeConfig.start} endPoint={routeConfig.end} layer={mapLayer} city={startInput || '苏州'} />
                </div>
             </main>
             {selectedRouteDetail && (
               <div className="route-detail-overlay" role="dialog" aria-modal="true" aria-label="路线详情" onClick={() => setSelectedRouteDetail(null)}>
                 <section className="route-detail-modal" onClick={event => event.stopPropagation()}>
                   <header className="route-detail-header">
                     <div>
                       <span>路线详情</span>
                       <h2>{selectedRouteDetail.label}</h2>
                       <p>{startInput.trim()} → {endInput.trim()}</p>
                     </div>
                     <button type="button" className="icon-btn" aria-label="关闭路线详情" onClick={() => setSelectedRouteDetail(null)}>
                       <X size={20} />
                     </button>
                   </header>

                   <div className="route-detail-body">
                     <article className="route-detail-section">
                       <div className="route-detail-title">
                         <MapIcon size={18} />
                         <strong>路线图</strong>
                       </div>
                       <div className="route-mini-map">
                         <svg viewBox="0 0 640 300" role="img" aria-label="路线图">
                           <defs>
                             <linearGradient id="routeDetailLine" x1="0" x2="1">
                               <stop offset="0%" stopColor="#14b8a6" />
                               <stop offset="100%" stopColor="#38bdf8" />
                             </linearGradient>
                             <linearGradient id="routeMapPark" x1="0" x2="1" y1="0" y2="1">
                               <stop offset="0%" stopColor="#d9fbe8" />
                               <stop offset="100%" stopColor="#b9efd8" />
                             </linearGradient>
                             <filter id="routeShadow" x="-20%" y="-20%" width="140%" height="140%">
                               <feDropShadow dx="0" dy="8" stdDeviation="6" floodColor="#0f766e" floodOpacity=".18" />
                             </filter>
                           </defs>
                           <rect width="640" height="300" rx="24" fill="#eef8f5" />
                           <path d="M34 236C98 186 150 190 206 218C262 246 314 228 354 194C414 142 482 146 610 86" fill="none" stroke="#cce3df" strokeWidth="16" strokeLinecap="round" opacity=".8" />
                           <path d="M-20 84C68 40 158 46 238 88C332 138 430 126 650 36" fill="none" stroke="#d6e7f0" strokeWidth="34" strokeLinecap="round" opacity=".7" />
                           <path d="M426 238C470 190 552 184 630 216V300H392C386 278 396 260 426 238Z" fill="url(#routeMapPark)" opacity=".9" />
                           <path d="M26 52H614M26 108H614M26 164H614M26 220H614M106 24V276M202 24V276M298 24V276M394 24V276M490 24V276M586 24V276" stroke="#c9ded9" strokeWidth="1.4" opacity=".85" />
                           <path d="M70 276C110 226 128 164 184 140C240 116 284 132 336 104C394 74 452 82 574 44" fill="none" stroke="#ffffff" strokeWidth="18" strokeLinecap="round" opacity=".88" />
                           <path d="M70 276C110 226 128 164 184 140C240 116 284 132 336 104C394 74 452 82 574 44" fill="none" stroke="#c5d8d4" strokeWidth="3" strokeDasharray="9 12" strokeLinecap="round" opacity=".9" />
                           {routeMapModel && (
                             <>
                               <path d={routeMapModel.guidePath} fill="none" stroke="#0f766e" strokeWidth="3" strokeDasharray="8 12" strokeLinecap="round" opacity=".38" />
                               <path d={routeMapModel.path} fill="none" stroke="#ffffff" strokeWidth="19" strokeLinecap="round" strokeLinejoin="round" filter="url(#routeShadow)" />
                               <path d={routeMapModel.path} fill="none" stroke="url(#routeDetailLine)" strokeWidth="10" strokeLinecap="round" strokeLinejoin="round" />
                               {routeMapModel.points.map((point, index) => (
                                 <g key={`${point.type}-${index}`} transform={`translate(${point.x} ${point.y})`}>
                                   <circle r={point.type === 'via' ? 9 : 14} fill={point.type === 'end' ? '#0f766e' : '#14b8a6'} stroke="#fff" strokeWidth="4" />
                                   {point.type !== 'via' && <text y="5" textAnchor="middle" fill="#fff" fontSize="12" fontWeight="900">{point.type === 'start' ? '起' : '终'}</text>}
                                   {point.type === 'via' && <circle r="3" fill="#fff" />}
                                 </g>
                               ))}
                               {routeMapModel.points.filter(point => point.type !== 'via').map((point, index) => (
                                 <g key={`${point.type}-label`} transform={`translate(${point.x} ${index === 0 ? point.y - 34 : point.y + 38})`}>
                                   <rect x="-54" y="-15" width="108" height="30" rx="15" fill="rgba(255,255,255,.94)" stroke="#d9eee9" />
                                   <text y="5" textAnchor="middle" fill="#173b36" fontSize="13" fontWeight="800">{point.label}</text>
                                 </g>
                               ))}
                             </>
                           )}
                         </svg>
                         <div className="route-mini-stops">
                           <span>起点：{startInput.trim()}</span>
                           <span>终点：{endInput.trim()}</span>
                         </div>
                       </div>
                       <div className="route-detail-metrics">
                         <span>{selectedRouteDetail.route.distance_km} km</span>
                         <span>{formatDuration(selectedRouteDetail.route.duration_minutes)}</span>
                         <span>{selectedRouteDetail.route.source}</span>
                       </div>
                     </article>

                     <article className="route-detail-section">
                       <div className="route-detail-title">
                         <Car size={18} />
                         <strong>费用预估</strong>
                         <small>约 ¥{routeDetailCostTotal}</small>
                       </div>
                       <div className="route-cost-chart">
                         {routeDetailCosts.map(item => (
                           <div className="route-cost-row" key={item.label}>
                             <span>{item.label}</span>
                             <div><i style={{ width: `${Math.max(6, (item.value / routeDetailCostMax) * 100)}%` }} /></div>
                             <b>¥{item.value}</b>
                           </div>
                         ))}
                       </div>
                     </article>
                   </div>

                   <article className="route-detail-section route-step-section">
                     <div className="route-detail-title">
                       <Navigation size={18} />
                       <strong>关键步骤</strong>
                     </div>
                     <ol>
                       {(selectedRouteDetail.route.steps || []).map(step => <li key={step}>{step}</li>)}
                     </ol>
                   </article>
                 </section>
               </div>
             )}
          </div>
        )}

        {activeTab === 'weather' && (
           <div className="weather-layout stack">
              <form className="search-row panel weather-search-form" onSubmit={handleSearch}>
                 <label className="sr-only" htmlFor="weather-city">城市名称</label>
                 <input id="weather-city" name="city" defaultValue={searchCity} placeholder="输入城市名称，如：杭州市" />
                 <button type="submit" className="primary-btn">查询天气</button>
              </form>

              {weatherLoading ? (
                 <EmptyState title="正在获取天气信息..." />
              ) : weatherCurrent ? (
                 <>
                    <div className="panel weather-dashboard-card">
                       <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap: 24, flexWrap: 'wrap'}}>
                          <div>
                             <h2 style={{fontSize: '36px', margin: '0 0 10px 0'}}>{weatherCurrent.city || searchCity}</h2>
                             <div style={{fontSize: '56px', fontWeight: 'bold', color: 'var(--color-primary)'}}>{weatherCurrent.current?.temp}°C</div>
                             <div style={{fontSize: '20px', color: 'var(--color-muted)', marginTop: '10px'}}>{weatherCurrent.current?.condition} | 体感 {weatherCurrent.current?.feelsLike || weatherCurrent.current?.temp}°C</div>
                             <div style={{marginTop: 10, color: 'var(--color-muted)'}}>{weatherCurrent.provider} · {weatherCurrent.source}</div>
                          </div>
                          <div className="weather-metric-grid">
                             <article><Wind size={18}/><span>风向风力</span><strong>{weatherCurrent.current?.wind || '暂未接入'}</strong></article>
                             <article><Droplets size={18}/><span>相对湿度</span><strong>{weatherCurrent.current?.humidity || '--'}</strong></article>
                             <article><ThermometerSun size={18}/><span>空气质量</span><strong>{weatherCurrent.current?.air || '--'}</strong></article>
                             <article><Umbrella size={18}/><span>出行提示</span><strong>{weatherCurrent.travelAdvice?.[0] || '适合出行'}</strong></article>
                          </div>
                       </div>
                    </div>

                    {weatherInsights && (
                      <section className="weather-insight-grid">
                        <article className="panel weather-judgement-card">
                          <div className="weather-judgement-head">
                            <span><ShieldCheck size={20} /></span>
                            <div>
                              <small>实时综合判断</small>
                              <h3>今日出行判断</h3>
                            </div>
                          </div>
                          <div className="weather-score-row">
                            <strong>{weatherInsights.score}</strong>
                            <span>/ 100</span>
                          </div>
                          <p>{weatherInsights.summary}</p>
                          <div className="weather-tip-list">
                            {weatherInsights.tips.map(tip => <span key={tip}>{tip}</span>)}
                          </div>
                        </article>

                        <div className="weather-index-panel">
                          {weatherInsights.indexes.map(item => {
                            const Icon = weatherInsightIcons[item.key] || CloudSun
                            return (
                              <article className="weather-index-card" key={item.key}>
                                <Icon size={20} />
                                <span>{item.label}</span>
                                <strong>{item.value}</strong>
                                <p>{item.detail}</p>
                              </article>
                            )
                          })}
                        </div>

                        <article className="panel weather-alert-card">
                          <div className="weather-alert-title">
                            <AlertTriangle size={20} />
                            <strong>风险与准备</strong>
                          </div>
                          <ul>
                            {weatherInsights.alerts.map(alert => <li key={alert}>{alert}</li>)}
                          </ul>
                        </article>
                      </section>
                    )}

                    {forecast.length > 0 && (
                       <div className="panel" style={{padding: '24px'}}>
                          <SectionHeader title="未来 7 日趋势" />
                          <div style={{height: 260, marginTop: 12}}>
                            <ResponsiveContainer width="100%" height="100%">
                              <LineChart data={forecast}>
                                <CartesianGrid strokeDasharray="3 3" stroke="#d8ece7" />
                                <XAxis dataKey="day" tick={{ fill: '#6b7f7b', fontSize: 12 }} />
                                <YAxis tick={{ fill: '#6b7f7b', fontSize: 12 }} unit="°C" />
                                <Tooltip formatter={(value) => `${value}°C`} />
                                <Line type="monotone" dataKey="high" name="最高温" stroke="#0b9f8a" strokeWidth={3} dot={{ r: 4 }} />
                                <Line type="monotone" dataKey="low" name="最低温" stroke="#38bdf8" strokeWidth={3} dot={{ r: 4 }} />
                              </LineChart>
                            </ResponsiveContainer>
                          </div>
                          <div className="weather-forecast-strip">
                            {forecast.map(day => (
                              <article key={day.day}>
                                <strong>{day.day}</strong>
                                <span>{day.condition}</span>
                                <b>{day.low}-{day.high}°C</b>
                              </article>
                            ))}
                          </div>
                       </div>
                    )}
                 </>
              ) : (
                 <EmptyState title="未能获取到天气数据" text="请检查城市名称或网络连接。" />
              )}
           </div>
        )}
      </div>
    </div>
  )
}
