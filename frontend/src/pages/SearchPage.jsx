import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { Search, X, Clock, TrendingUp, MapPin, Mountain, Compass, BookOpen, Tag, ArrowRight, Sparkles } from 'lucide-react'
import { searchAll, getSearchSuggestions, getHotSearches, getSearchHistory, clearSearchHistory } from '../api/search.js'
import { useAuth } from '../hooks/useAuth.jsx'
import { useToast } from '../hooks/useToast.jsx'
import ScenicCard from '../components/common/ScenicCard.jsx'
import '../styles/search.css'

const TABS = [
  { key: 'all', label: '综合', icon: Sparkles },
  { key: 'scenic', label: '景区', icon: Mountain },
  { key: 'city', label: '城市', icon: MapPin },
  { key: 'theme', label: '主题', icon: Tag },
  { key: 'route', label: '路线', icon: Compass },
  { key: 'community', label: '攻略', icon: BookOpen },
]

export default function SearchPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const { isLoggedIn } = useAuth()
  const toast = useToast()

  const [keyword, setKeyword] = useState(searchParams.get('q') || '')
  const [activeTab, setActiveTab] = useState(searchParams.get('category') || 'all')
  const [results, setResults] = useState(null)
  const [loading, setLoading] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [hotSearches, setHotSearches] = useState([])
  const [history, setHistory] = useState([])
  const [showHistory, setShowHistory] = useState(false)

  const inputRef = useRef(null)
  const suggestionTimer = useRef(null)
  const wrapperRef = useRef(null)

  // Load hot searches on mount
  useEffect(() => {
    getHotSearches().then(data => { if (data) setHotSearches(data) })
    if (isLoggedIn) {
      getSearchHistory().then(data => { if (data) setHistory(data) })
    }
  }, [isLoggedIn])

  // Execute search on mount if keyword in URL
  useEffect(() => {
    const q = searchParams.get('q') || ''
    if (q) {
      setKeyword(q)
      executeSearch(q, searchParams.get('category') || 'all')
    }
    // eslint-disable-next-line
  }, [])

  // Close dropdowns on outside click
  useEffect(() => {
    const handler = (e) => {
      if (wrapperRef.current && !wrapperRef.current.contains(e.target)) {
        setShowSuggestions(false)
        setShowHistory(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const executeSearch = useCallback(async (q, category = 'all') => {
    if (!q.trim()) return
    setLoading(true)
    setShowSuggestions(false)
    setShowHistory(false)

    const params = `?q=${encodeURIComponent(q.trim())}&category=${category}&limit=20`
    const data = await searchAll(params)
    setResults(data)
    setLoading(false)

    // Update URL
    const urlParams = new URLSearchParams()
    urlParams.set('q', q.trim())
    if (category !== 'all') urlParams.set('category', category)
    setSearchParams(urlParams, { replace: true })

    // Refresh history if logged in
    if (isLoggedIn) {
      getSearchHistory().then(h => { if (h) setHistory(h) })
    }
  }, [setSearchParams, isLoggedIn])

  const handleInputChange = (e) => {
    const val = e.target.value
    setKeyword(val)

    // Debounced suggestions
    if (suggestionTimer.current) clearTimeout(suggestionTimer.current)
    if (val.trim().length >= 1) {
      suggestionTimer.current = setTimeout(async () => {
        const data = await getSearchSuggestions(val)
        if (data) {
          setSuggestions(data)
          setShowSuggestions(true)
        }
      }, 200)
    } else {
      setSuggestions([])
      setShowSuggestions(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (keyword.trim()) {
      executeSearch(keyword, activeTab)
    }
  }

  const handleSuggestionClick = (suggestion) => {
    setKeyword(suggestion.text)
    executeSearch(suggestion.text, activeTab)
  }

  const handleHotClick = (hot) => {
    setKeyword(hot.keyword)
    executeSearch(hot.keyword, activeTab)
  }

  const handleHistoryClick = (item) => {
    setKeyword(item.keyword)
    executeSearch(item.keyword, activeTab)
  }

  const handleClearHistory = async () => {
    await clearSearchHistory()
    setHistory([])
    toast.show('搜索历史已清空')
  }

  const handleTabChange = (tab) => {
    setActiveTab(tab)
    if (keyword.trim()) {
      executeSearch(keyword, tab)
    }
  }

  const handleFocus = () => {
    if (!keyword.trim() && (history.length > 0 || hotSearches.length > 0)) {
      setShowHistory(true)
      setShowSuggestions(false)
    }
  }

  const correction = results?.correction

  return (
    <div className="search-page">
      {/* Search Header */}
      <div className="search-header">
        <div className="search-header-inner">
          <h1>全站搜索</h1>
          <p>搜索景区、城市、主题、路线、攻略</p>

          <form className="search-input-wrapper" onSubmit={handleSubmit} ref={wrapperRef}>
            <div className="search-input-bar">
              <Search size={20} className="search-input-icon" />
              <input
                ref={inputRef}
                type="text"
                value={keyword}
                onChange={handleInputChange}
                onFocus={handleFocus}
                placeholder="输入景区名、城市、主题关键词..."
                autoComplete="off"
              />
              {keyword && (
                <button type="button" className="search-clear-btn" onClick={() => { setKeyword(''); setResults(null); inputRef.current?.focus() }}>
                  <X size={16} />
                </button>
              )}
              <button type="submit" className="search-submit-btn">
                搜索
              </button>
            </div>

            {/* Suggestions Dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div className="search-dropdown">
                {suggestions.map((s, i) => (
                  <div key={i} className="suggestion-item" onClick={() => handleSuggestionClick(s)}>
                    <span className={`suggestion-type suggestion-type-${s.type}`}>
                      {s.type === 'scenic' && <Mountain size={14} />}
                      {s.type === 'city' && <MapPin size={14} />}
                      {s.type === 'theme' && <Tag size={14} />}
                      {s.type === 'province' && <MapPin size={14} />}
                    </span>
                    <span className="suggestion-text">{s.text}</span>
                    <span className="suggestion-subtitle">{s.subtitle}</span>
                    {s.level && <span className="suggestion-badge">{s.level}</span>}
                  </div>
                ))}
              </div>
            )}

            {/* History & Hot Dropdown (when no keyword) */}
            {showHistory && !keyword && (
              <div className="search-dropdown search-dropdown-wide">
                {isLoggedIn && history.length > 0 && (
                  <div className="dropdown-section">
                    <div className="dropdown-section-header">
                      <span><Clock size={14} /> 搜索历史</span>
                      <button onClick={handleClearHistory} className="dropdown-clear-btn">清空</button>
                    </div>
                    <div className="history-tags">
                      {history.slice(0, 10).map((h, i) => (
                        <button key={i} className="history-tag" onClick={() => handleHistoryClick(h)}>
                          {h.keyword}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
                {hotSearches.length > 0 && (
                  <div className="dropdown-section">
                    <div className="dropdown-section-header">
                      <span><TrendingUp size={14} /> 热门搜索</span>
                    </div>
                    <div className="hot-tags">
                      {hotSearches.map((h, i) => (
                        <button key={i} className={`hot-tag hot-tag-${h.category}`} onClick={() => handleHotClick(h)}>
                          {i < 3 && <span className="hot-rank">{i + 1}</span>}
                          {h.keyword}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </form>
        </div>
      </div>

      {/* Search Body */}
      <div className="search-body">
        {/* Correction Hint */}
        {correction && (
          <div className="search-correction">
            <Sparkles size={16} />
            <span>你是不是要搜 <button className="correction-link" onClick={() => { setKeyword(correction); executeSearch(correction, activeTab) }}>{correction}</button>？</span>
          </div>
        )}

        {/* No keyword: show hot + history landing */}
        {!results && !loading && (
          <div className="search-landing">
            {/* Hot Searches */}
            {hotSearches.length > 0 && (
              <section className="search-section">
                <h2><TrendingUp size={20} /> 热门搜索</h2>
                <div className="hot-grid">
                  {hotSearches.map((h, i) => (
                    <button key={i} className="hot-card" onClick={() => handleHotClick(h)}>
                      <span className="hot-index">{i + 1}</span>
                      <span className="hot-keyword">{h.keyword}</span>
                      <span className={`hot-category cat-${h.category}`}>
                        {h.category === 'scenic' ? '景区' : h.category === 'city' ? '城市' : '主题'}
                      </span>
                    </button>
                  ))}
                </div>
              </section>
            )}

            {/* Search History */}
            {isLoggedIn && history.length > 0 && (
              <section className="search-section">
                <div className="section-header-row">
                  <h2><Clock size={20} /> 搜索历史</h2>
                  <button onClick={handleClearHistory} className="clear-btn">清空</button>
                </div>
                <div className="history-tags">
                  {history.map((h, i) => (
                    <button key={i} className="history-tag" onClick={() => handleHistoryClick(h)}>
                      {h.keyword}
                    </button>
                  ))}
                </div>
              </section>
            )}

            {!isLoggedIn && (
              <div className="search-hint">
                <Clock size={16} />
                <span>登录后可保存搜索记录</span>
              </div>
            )}
          </div>
        )}

        {/* Loading */}
        {loading && (
          <div className="search-loading">
            <div className="loading-spinner" />
            <p>正在搜索中...</p>
          </div>
        )}

        {/* Results */}
        {results && !loading && (
          <>
            {/* Tabs */}
            <div className="search-tabs">
              {TABS.map(tab => {
                const count = tab.key === 'all' ? results.total : (results.categories?.[tab.key]?.count || 0)
                return (
                  <button
                    key={tab.key}
                    className={`search-tab ${activeTab === tab.key ? 'active' : ''}`}
                    onClick={() => handleTabChange(tab.key)}
                  >
                    <tab.icon size={16} />
                    {tab.label}
                    {count > 0 && <span className="tab-count">{count}</span>}
                  </button>
                )
              })}
            </div>

            {/* No Results */}
            {results.total === 0 && results.recommendations && (
              <div className="search-no-results">
                <div className="no-results-header">
                  <h3>未找到「{keyword}」的相关结果</h3>
                  <p>试试其他关键词，或看看以下推荐</p>
                </div>

                {results.recommendations.popular_scenic?.length > 0 && (
                  <section className="recommend-section">
                    <h3>热门景区推荐</h3>
                    <div className="recommend-grid">
                      {results.recommendations.popular_scenic.map(s => (
                        <div key={s.id} className="recommend-card" onClick={() => navigate(s.url)}>
                          <span className="recommend-name">{s.name}</span>
                          <span className="recommend-meta">{s.province} {s.city} · {s.level}</span>
                          <ArrowRight size={14} />
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {results.recommendations.themes?.length > 0 && (
                  <section className="recommend-section">
                    <h3>主题路线</h3>
                    <div className="theme-tags">
                      {results.recommendations.themes.map((t, i) => (
                        <button key={i} className="theme-tag" onClick={() => navigate(t.url)}>
                          {t.text}
                        </button>
                      ))}
                    </div>
                  </section>
                )}

                {results.recommendations.nearby_cities?.length > 0 && (
                  <section className="recommend-section">
                    <h3>相近城市</h3>
                    <div className="city-tags">
                      {results.recommendations.nearby_cities.map((c, i) => (
                        <button key={i} className="city-tag" onClick={() => navigate(c.url)}>
                          <MapPin size={14} /> {c.text}
                        </button>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            )}

            {/* Result Groups */}
            {results.total > 0 && (
              <div className="search-results">
                {/* Scenic Results */}
                {results.categories?.scenic?.items?.length > 0 && (
                  <section className="result-section">
                    <h3><Mountain size={18} /> 景区 ({results.categories.scenic.count})</h3>
                    <div className="scenic-result-grid">
                      {results.categories.scenic.items.slice(0, activeTab === 'scenic' ? 20 : 6).map(item => (
                        <ScenicCard key={item.id || item.slug} item={item} />
                      ))}
                    </div>
                    {activeTab === 'all' && results.categories.scenic.count > 6 && (
                      <button className="more-btn" onClick={() => handleTabChange('scenic')}>
                        查看全部 {results.categories.scenic.count} 个景区 <ArrowRight size={14} />
                      </button>
                    )}
                  </section>
                )}

                {/* City Results */}
                {results.categories?.city?.items?.length > 0 && (
                  <section className="result-section">
                    <h3><MapPin size={18} /> 城市 ({results.categories.city.count})</h3>
                    <div className="city-result-grid">
                      {results.categories.city.items.map((item, i) => (
                        <div key={i} className="city-result-card" onClick={() => navigate(item.url)}>
                          <div className="city-result-name">{item.text}</div>
                          <div className="city-result-meta">{item.province} · {item.scenic_count} 个景区</div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Theme Results */}
                {results.categories?.theme?.items?.length > 0 && (
                  <section className="result-section">
                    <h3><Tag size={18} /> 主题 ({results.categories.theme.count})</h3>
                    <div className="theme-result-grid">
                      {results.categories.theme.items.map((item, i) => (
                        <div key={i} className="theme-result-card" onClick={() => navigate(item.url)}>
                          <Tag size={16} />
                          <span>{item.text}</span>
                          <ArrowRight size={14} />
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Route Results */}
                {results.categories?.route?.items?.length > 0 && (
                  <section className="result-section">
                    <h3><Compass size={18} /> 路线 ({results.categories.route.count})</h3>
                    <div className="route-result-grid">
                      {results.categories.route.items.map((item, i) => (
                        <div key={i} className="route-result-card" onClick={() => navigate(item.url)}>
                          <Compass size={16} />
                          <div>
                            <div className="route-result-name">{item.text}</div>
                            <div className="route-result-meta">{item.province}</div>
                          </div>
                          <ArrowRight size={14} />
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Community Results */}
                {results.categories?.community?.items?.length > 0 && (
                  <section className="result-section">
                    <h3><BookOpen size={18} /> 攻略 ({results.categories.community.count})</h3>
                    <div className="community-result-grid">
                      {results.categories.community.items.map((item, i) => (
                        <div key={i} className="community-result-card" onClick={() => navigate(item.url)}>
                          <div className="community-result-title">{item.text}</div>
                          <div className="community-result-meta">
                            {item.author} · {item.category} · {item.likes} 赞
                          </div>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
