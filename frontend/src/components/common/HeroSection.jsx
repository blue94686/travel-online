import { Search } from 'lucide-react'
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './HeroSection.css'

export default function HeroSection({ 
  variant = 'search', 
  title, 
  subtitle, 
  image, 
  images = [],
  children,
  capsules = [],
  leftContent,
  bottomBar,
  searchCity = ''
}) {
  const [keyword, setKeyword] = useState('')
  const navigate = useNavigate()
  const [currentIndex, setCurrentIndex] = useState(0)

  // Use images array if provided, otherwise fallback to image or default
  const carouselImages = images.length > 0 ? images : [image || '/images/hero-mountain-lake.jpg']

  useEffect(() => {
    if (carouselImages.length <= 1) return
    const timer = setInterval(() => {
      setCurrentIndex(prev => (prev + 1) % carouselImages.length)
    }, 6000)
    return () => clearInterval(timer)
  }, [carouselImages.length])

  const submit = (event) => {
    event.preventDefault()
    const value = keyword.trim()
    const params = new URLSearchParams()
    if (value) params.set('q', value)
    navigate(`/search${params.toString() ? `?${params.toString()}` : ''}`)
  }

  const renderBackgrounds = () => (
    <div className="hero-carousel-container">
      {carouselImages.map((src, idx) => (
        <div 
          key={`${src}-${idx}`}
          className={`hero-slide ${idx === currentIndex ? 'active' : ''}`}
          style={{ backgroundImage: `url(${src})` }}
        />
      ))}
      <div className="hero-overlay" />
    </div>
  )

  if (variant === 'home') {
    return (
      <section className="hero-section variant-home">
        {renderBackgrounds()}
        <div className="hero-content">
          <h1>{title || '今天去哪玩？'}</h1>
          <p>{subtitle || '极客旅行 · 精准规划 · 实时掌握'}</p>
          
          {capsules.length > 0 && (
            <div className="home-capsules">
              {capsules.map((cap, i) => (
                <div className="home-capsule" key={i}>
                  {cap.icon && <span className="capsule-icon">{cap.icon}</span>}
                  <div className="capsule-text">
                    <strong>{cap.title}</strong>
                    {cap.subtitle && <small>{cap.subtitle}</small>}
                  </div>
                </div>
              ))}
            </div>
          )}

          <form className="hero-search" onSubmit={submit}>
            <Search size={24} className="search-icon" />
            <input 
              value={keyword} 
              onChange={e => setKeyword(e.target.value)} 
              placeholder="搜索景区、路线、攻略、美食、目的地..." 
            />
            <div className="search-actions">
              <button type="submit" className="primary-btn">搜索</button>
            </div>
          </form>
          {children}
        </div>
        {bottomBar && <div className="hero-bottom-bar">{bottomBar}</div>}
      </section>
    )
  }

  if (variant === 'split') {
    return (
      <section className="hero-section variant-split">
        <div className="hero-split-image">
          {renderBackgrounds()}
          <div className="hero-split-content">
            {capsules.length > 0 && (
              <div className="capsules">
                {capsules.map((cap, i) => <span key={i}>{cap}</span>)}
              </div>
            )}
            <h1>{title}</h1>
            <p>{subtitle}</p>
            {leftContent}
          </div>
        </div>
        <div className="hero-split-form">
          {children}
        </div>
      </section>
    )
  }

  if (variant === 'display') {
    return (
      <section className="hero-section variant-display">
        {renderBackgrounds()}
        <div className="hero-content">
          <div className="title-group">
            <p>{subtitle}</p>
            <h1>{title}</h1>
          </div>
          {capsules.length > 0 && (
            <div className="display-capsules">
              {capsules.map((cap, i) => (
                <div className="display-capsule" key={i}>
                  <strong>{cap.title}</strong>
                  <small>{cap.subtitle}</small>
                </div>
              ))}
            </div>
          )}
          {children}
        </div>
      </section>
    )
  }

  // Default: Search focus (Home)
  return (
    <section className="hero-section variant-search">
      {renderBackgrounds()}
      <div className="hero-content">
        {capsules.length > 0 && (
          <div className="capsules">
            {capsules.map((cap, i) => <span key={i}>{cap}</span>)}
          </div>
        )}
        <h1>{title || '今天去哪玩？'}</h1>
        <p>{subtitle || '极客旅行 · 精准规划 · 实时掌握'}</p>
        <form className="hero-search" onSubmit={submit}>
          <Search size={24} className="search-icon" />
          <input 
            value={keyword} 
            onChange={e => setKeyword(e.target.value)} 
            placeholder="搜索景区、路线、攻略、美食、目的地..." 
          />
          <div className="search-actions">
            <button type="submit" className="primary-btn">搜索</button>
          </div>
        </form>
        {children}
      </div>
    </section>
  )
}
