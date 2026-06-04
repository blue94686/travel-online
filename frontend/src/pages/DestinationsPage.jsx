import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Building2, Filter, MapPinned, RotateCcw, Search, Compass, MapPin, Sparkles, X } from 'lucide-react'
import { getRegionCities, getScenicRegions, getSyncedScenicList } from '../api/scenic.js'
import { saveFavorite } from '../api/user.js'
import { request } from '../api/client.js'
import EmptyState from '../components/common/EmptyState.jsx'
import ScenicCard from '../components/common/ScenicCard.jsx'
import ChinaProvinceMap from '../components/common/ChinaProvinceMap.jsx'
import HeroSection from '../components/common/HeroSection.jsx'
import SectionHeader from '../components/common/SectionHeader.jsx'
import { locationTitle, nearbyDistricts, normalizeFilterChange, popularProvinces, readScenicState, scenicParams, scopedOptions } from '../utils/scenicSync.js'

export default function DestinationsPage({ initialTab: initialTabProp }) {
  const location = useLocation()
  const navigate = useNavigate()

  // Parse URL search params to determine the active tab
  const searchParams = new URLSearchParams(location.search)
  const normalizeTab = (value) => (value === 'provinces' || value === 'scenic') ? value : 'scenic'
  const initialTab = normalizeTab(searchParams.get('tab') || initialTabProp || 'scenic')
  const [activeTab, setActiveTab] = useState(initialTab)

  // Scenic List State
  const routeState = useMemo(() => readScenicState(location.search), [location.search])
  const [items, setItems] = useState([])
  const [keyword, setKeyword] = useState(routeState.keyword)
  const [page, setPage] = useState(1)
  const [sortBy, setSortBy] = useState('default')
  const [favorites, setFavorites] = useState({})
  const [message, setMessage] = useState('')
  const [filters, setFilters] = useState(routeState.filters)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [remoteOptions, setRemoteOptions] = useState(null)
  const [totalCount, setTotalCount] = useState(0)
  
  // Provinces State
  const [provincesData, setProvincesData] = useState(null)
  const [selectedProvince, setSelectedProvince] = useState(null)
  const [provinceCities, setProvinceCities] = useState([])
  const [provinceScenic, setProvinceScenic] = useState([])
  const [provinceModalLoading, setProvinceModalLoading] = useState(false)

  const options = remoteOptions || scopedOptions(filters.province)
  const title = locationTitle(filters)
  const districtRecommendations = nearbyDistricts(items, filters.district)
  const provinceRecommendations = popularProvinces(items)

  // Sync tab state with URL without reloading
  useEffect(() => {
    const currentTab = normalizeTab(searchParams.get('tab') || 'scenic')
    if (activeTab !== currentTab) {
      setActiveTab(currentTab)
    }
  }, [location.search])

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    // Update URL to reflect tab change, preserving other params if returning to scenic
    const newParams = new URLSearchParams(location.search)
    newParams.set('tab', tab)
    navigate(`/destinations?${newParams.toString()}`)
  }

  // Effect for fetching region options
  useEffect(() => {
    if (activeTab !== 'scenic') return
    const params = new URLSearchParams()
    if (routeState.filters.province) params.set('province', routeState.filters.province)
    if (routeState.filters.city) params.set('city', routeState.filters.city)
    getScenicRegions(params.toString() ? `?${params.toString()}` : '').then(data => {
      if (data) setRemoteOptions({
        provinces: data.provinces || [],
        cities: data.cities || [],
        districts: data.districts || []
      })
    })
  }, [routeState.filters.province, routeState.filters.city, activeTab])

  // Effect for fetching scenic list
  useEffect(() => {
    if (activeTab !== 'scenic') return
    const params = scenicParams(routeState.keyword, routeState.filters)
    if (sortBy && sortBy !== 'default') params.set('sort', sortBy)
    setLoading(true)
    setLoadError('')
    getSyncedScenicList(params.toString() ? `?${params.toString()}` : '').then(data => {
      if (!data) {
        setItems([])
        setLoadError('景区接口未连接，请启动后端服务后重试。')
        return
      }
      // Handle new API format {items, total, page, limit} or legacy array
      const nextItems = Array.isArray(data) ? data : (data.items || [])
      setItems(nextItems)
      setTotalCount(Array.isArray(data) ? nextItems.length : Number(data.total || nextItems.length))
    }).finally(() => setLoading(false))
    setPage(1)
  }, [routeState, activeTab, sortBy])

  // Effect for fetching provinces data
  useEffect(() => {
    if (activeTab !== 'provinces') return
    request('/api/regions/provinces').then(data => {
      if (data && data.groups) {
        setProvincesData(data.groups)
      } else {
         // Fallback if the specific endpoint isn't working as expected
         request('/api/provinces').then(fallbackData => {
            if(fallbackData && fallbackData.groups) setProvincesData(fallbackData.groups)
         })
      }
    })
  }, [activeTab])

  const filtered = items.filter(item => {
    const text = `${item.name}${item.province}${item.city}${item.district}${item.summary}${(item.tags || []).join('')}`
    return !keyword.trim() || text.includes(keyword.trim())
  })
  const pageItems = filtered.slice((page - 1) * 6, page * 6)
  const totalPages = Math.max(1, Math.ceil(filtered.length / 6))

  const pushState = (nextKeyword, nextFilters) => {
    const params = scenicParams(nextKeyword, nextFilters)
    params.set('tab', 'scenic')
    navigate(`/destinations${params.toString() ? `?${params.toString()}` : ''}`)
  }
  const applyFilter = (key, value) => {
    const next = normalizeFilterChange(filters, key, value)
    setFilters(next)
    pushState(keyword, next)
  }
  const submit = (event) => {
    event.preventDefault()
    pushState(keyword, filters)
  }
  const reset = () => {
    setKeyword('')
    setFilters({ province: '', city: '', district: '', theme: '' })
    navigate('/destinations?tab=scenic')
  }
  const toggleFavorite = (item, nextFav) => {
    const willFav = nextFav !== undefined ? nextFav : !favorites[item.id]
    setFavorites(current => ({ ...current, [item.id]: willFav }))
    saveFavorite({ scenic_id: item.id }).catch(() => {})
    setMessage(`${item.name} ${willFav ? '已加入收藏' : '已取消收藏'}`)
  }

  const handleProvinceSelect = async (provinceItem) => {
    if (!provinceItem?.province) return
    setSelectedProvince(provinceItem)
    setProvinceCities([])
    setProvinceScenic([])
    setProvinceModalLoading(true)
    try {
      const [citiesResult, scenicResult] = await Promise.all([
        getRegionCities(provinceItem.province).catch(() => []),
        getSyncedScenicList(`?province=${encodeURIComponent(provinceItem.province)}&limit=8&offset=0`).catch(() => null),
      ])
      setProvinceCities(Array.isArray(citiesResult) ? citiesResult : [])
      const nextScenic = Array.isArray(scenicResult) ? scenicResult : (scenicResult?.items || [])
      setProvinceScenic(nextScenic)
    } finally {
      setProvinceModalLoading(false)
    }
  }

  const closeProvinceModal = () => {
    setSelectedProvince(null)
    setProvinceCities([])
    setProvinceScenic([])
  }

  const locationBreadcrumb = '探索中国 〉 ' + ([filters.province, filters.city, filters.district].filter(Boolean).join(' 〉 ') || '全国')

  return (
    <div className="destinations-page">
      <HeroSection
        variant="display"
        images={[
          'https://images.unsplash.com/photo-1469854523086-cc02fe5d8800?auto=format&fit=crop&w=1920&q=80',
          'https://images.unsplash.com/photo-1548013146-72479768bada?auto=format&fit=crop&w=1920&q=80',
          'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?auto=format&fit=crop&w=1920&q=80'
        ]}
        title={activeTab === 'scenic' ? title : '省份漫游'}
        subtitle={activeTab === 'scenic' ? locationBreadcrumb : '发现 34 个省级行政区的独特魅力'}
        capsules={activeTab === 'scenic' ? [
          { title: String(filtered.length), subtitle: '当前加载' },
          { title: String(totalCount), subtitle: '全国总数' },
          { title: String(filtered.filter(item => item.source === 'jingdian').length), subtitle: '全国数据' },
          { title: String(filtered.filter(item => item.source === 'amap').length), subtitle: '高德补充' }
        ] : []}
      />

      <div className="floating-tab-shell">
        <div className="tab-nav panel app-tab-nav" role="tablist" aria-label="目的地浏览方式">
           <button className={`ghost-btn ${activeTab === 'scenic' ? 'active' : ''}`} type="button" role="tab" aria-selected={activeTab === 'scenic'} onClick={() => handleTabChange('scenic')}>
             <Compass size={18}/> 景区推荐
           </button>
           <button className={`ghost-btn ${activeTab === 'provinces' ? 'active' : ''}`} type="button" role="tab" aria-selected={activeTab === 'provinces'} onClick={() => handleTabChange('provinces')}>
             <MapPin size={18}/> 省份浏览
           </button>
        </div>
      </div>

      <div className="page-content page-content-wide">
        {message && <div className="notice" style={{marginBottom: '20px'}}>{message}</div>}

        {activeTab === 'scenic' && (
          <div className="scenic-browser-layout">
            <aside className="filter-panel scenic-filter">
              <form className="search-row" onSubmit={submit} style={{marginBottom: '20px'}}>
                <Search size={18} />
                <input value={keyword} onChange={e => setKeyword(e.target.value)} placeholder="搜索景区、城市..." style={{width:'100%', border:'none', outline:'none'}}/>
              </form>
              
              <h3><Filter size={18} /> 三级浏览</h3>
              <label>选择省份<select value={filters.province} onChange={e => applyFilter('province', e.target.value)}><option value="">全部省份</option>{options.provinces.map(item => <option key={item}>{item}</option>)}</select></label>
              <label>选择城市<select value={filters.city} onChange={e => applyFilter('city', e.target.value)}><option value="">全部城市</option>{options.cities.map(item => <option key={item}>{item}</option>)}</select></label>
              <label>选择区县<select value={filters.district} onChange={e => applyFilter('district', e.target.value)}><option value="">全部区县</option>{options.districts.map(item => <option key={item}>{item}</option>)}</select></label>
              
              <div className="filter-group">
                <div className="card-title-row"><strong>快捷筛选</strong></div>
                <div className="chip-row">
                  {['5A 景区', '4A 景区', '自然风光', '人文古迹', '摄影打卡'].map(tag => (
                    <button key={tag} className={filters.theme === tag ? 'active' : ''} type="button" onClick={() => applyFilter('theme', tag === filters.theme ? '' : tag)}>{tag}</button>
                  ))}
                </div>
              </div>

              <div className="filter-group">
                <div className="card-title-row"><strong>热门城市</strong></div>
                <div className="chip-row">
                  {['杭州', '苏州', '成都', '西安', '厦门'].map(city => (
                    <button key={city} className={filters.city === city ? 'active' : ''} type="button" onClick={() => applyFilter('city', city === filters.city ? '' : city)}>{city}</button>
                  ))}
                </div>
              </div>
              
              <button type="button" className="primary-btn" onClick={reset} style={{width:'100%', marginTop: '10px'}}><RotateCcw size={16} /> 重置全部筛选</button>
            </aside>

            <main className="stack">
              {/* Collection Highlight */}
              {!keyword && !filters.province && (
                <div className="collection-highlight">
                  <img src="https://images.unsplash.com/photo-1506744038136-46273834b3fb?auto=format&fit=crop&w=1200&q=80" alt="山湖避暑景观" loading="lazy" />
                  <div className="collection-highlight-content">
                    <div>
                      <h3>热门必去榜单</h3>
                      <p>精选 15 个全国最佳避暑胜地</p>
                    </div>
	                    <button className="primary-btn collection-highlight-btn" type="button" onClick={() => navigate('/rankings')}>立即查看</button>
                  </div>
                </div>
              )}

              <div className="list-toolbar">
                <strong>{loading ? '正在同步数据...' : `共找到 ${filtered.length} 个景区`}</strong>
                <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
                  <option value="default">综合排序</option>
                  <option value="rating">评分最高</option>
                  <option value="name">名称 A-Z</option>
                </select>
              </div>
              
              {loadError ? (
                 <div className="notice danger">{loadError}</div>
              ) : (
                <>
                  <div className="scenic-result-list">
                    {pageItems.length ? pageItems.map(item => (
                      <ScenicCard key={item.id} scenic={item} variant="list" onFavorite={() => toggleFavorite(item)} />
                    )) : <EmptyState title={loading ? '正在加载' : '没有匹配的结果'} text="换个关键词或清空筛选条件后再试。" />}
                  </div>
                  <div className="pagination">{Array.from({ length: totalPages }).map((_, index) => <button className={page === index + 1 ? 'active' : ''} onClick={() => setPage(index + 1)} key={index}>{index + 1}</button>)}</div>
                </>
              )}
            </main>
          </div>
        )}

        {activeTab === 'provinces' && (
           <div className="provinces-content">
             {provincesData ? (
                <div className="stack destination-province-stack">
                  <ChinaProvinceMap
                    groups={provincesData}
                    selectedProvince={selectedProvince?.province}
                    onProvinceSelect={handleProvinceSelect}
                  />
                   {Object.entries(provincesData).map(([groupName, provinces]) => (
                      <section key={groupName} className="province-group panel destination-province-group">
                         <SectionHeader title={groupName} eyebrow="Region" />
                         <div className="tag-row" style={{marginTop: '16px', display: 'flex', flexWrap: 'wrap', gap: '12px'}}>
                            {provinces.map(p => (
                               <button 
                                 key={p.province} 
                                 className="ghost-btn" 
                                 onClick={() => handleProvinceSelect(p)}
                                 style={{display:'flex', justifyContent:'space-between', width:'200px', border:'1px solid var(--color-border)'}}
                               >
                                 <span>{p.province}</span>
                                 <span style={{color:'var(--color-muted)'}}>{p.scenic_count} 景区</span>
                               </button>
                            ))}
                         </div>
                      </section>
                   ))}
                </div>
             ) : (
                <EmptyState title="正在加载省份数据..." text="" />
             )}
           </div>
        )}

        {selectedProvince && (
          <div className="province-map-modal-backdrop" role="presentation" onMouseDown={event => event.target === event.currentTarget && closeProvinceModal()}>
            <section className="province-map-modal" role="dialog" aria-modal="true" aria-label={`${selectedProvince.province}景区信息`}>
              <header className="province-map-modal-head">
                <div>
                  <span><MapPinned size={15} /> 省区景区概览</span>
                  <h2>{selectedProvince.province}</h2>
                  <p>从全国源表、正式景区库和地区索引汇总，继续进入省份详情或三级浏览。</p>
                </div>
                <button className="icon-btn" type="button" aria-label="关闭省区弹窗" onClick={closeProvinceModal}>
                  <X size={18} />
                </button>
              </header>

              <div className="province-map-metrics">
                <article>
                  <Sparkles size={18} />
                  <strong>{Number(selectedProvince.scenic_count || 0).toLocaleString()}</strong>
                  <span>景区信息</span>
                </article>
                <article>
                  <Building2 size={18} />
                  <strong>{Number(selectedProvince.city_count || provinceCities.length || 0).toLocaleString()}</strong>
                  <span>城市入口</span>
                </article>
                <article>
                  <MapPin size={18} />
                  <strong>{provinceScenic.filter(item => String(item.level || '').includes('5A')).length || '-'}</strong>
                  <span>本批 5A</span>
                </article>
              </div>

              <div className="province-map-modal-grid">
                <section>
                  <div className="card-title-row">
                    <strong>代表景区</strong>
                    {provinceModalLoading && <span>加载中...</span>}
                  </div>
                  <div className="province-map-scenic-grid">
                    {provinceScenic.length ? provinceScenic.slice(0, 6).map(item => (
                      <Link key={item.id} to={`/scenic/${item.id}`} className="province-map-scenic-card">
                        <strong>{item.name}</strong>
                        <span>{[item.city, item.district, item.level].filter(Boolean).join(' · ') || '景区资料待补全'}</span>
                      </Link>
                    )) : (
                      <div className="province-map-empty-state">{provinceModalLoading ? '正在读取代表景区...' : '该省份代表景区暂未返回，可进入三级浏览查看全部。'}</div>
                    )}
                  </div>
                </section>

                <aside>
                  <div className="card-title-row"><strong>城市入口</strong></div>
                  <div className="province-map-city-row">
                    {provinceCities.slice(0, 18).map(city => (
                      <Link key={city} to={`/destinations?province=${encodeURIComponent(selectedProvince.province)}&city=${encodeURIComponent(city)}&tab=scenic`}>
                        {city}
                      </Link>
                    ))}
                    {!provinceCities.length && <span>{provinceModalLoading ? '城市加载中...' : '暂无城市索引'}</span>}
                  </div>
                </aside>
              </div>

              <footer className="province-map-modal-actions">
                <Link className="primary-btn" to={`/provinces/${encodeURIComponent(selectedProvince.province)}`}>
                  进入省份详情 <ArrowRight size={16} />
                </Link>
                <Link className="ghost-btn" to={`/destinations?province=${encodeURIComponent(selectedProvince.province)}&tab=scenic`}>
                  三级浏览 <ArrowRight size={16} />
                </Link>
                <button className="ghost-btn" type="button" onClick={closeProvinceModal}>关闭</button>
              </footer>
            </section>
          </div>
        )}

      </div>
    </div>
  )
}
