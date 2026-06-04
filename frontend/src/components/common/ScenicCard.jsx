import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Heart, MapPin, Star, Clock } from 'lucide-react'
import { getScenicImageOrPlaceholder } from '../../api/fallback.js'
import StatusBadge from './StatusBadge.jsx'
import './ScenicCard.css'

export default function ScenicCard({ scenic, variant = 'grid', onFavorite, isFavorited = false }) {
  const [favorite, setFavorite] = useState(isFavorited)
  const [imgSrc, setImgSrc] = useState(() => getScenicImageOrPlaceholder(scenic))

  const toggleFavorite = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setFavorite(value => !value)
    onFavorite?.(scenic, !favorite)
  }

  const handleError = (e) => {
    e.currentTarget.onerror = null
    setImgSrc(prev => prev?.startsWith('data:') ? prev : getScenicImageOrPlaceholder(scenic))
  }

  if (variant === 'list') {
    return (
      <Link to={`/scenic/${scenic.id}`} className="scenic-card variant-list">
        <div className="card-image-wrapper">
          <img src={imgSrc} onError={handleError} alt={scenic.name} loading="lazy" />
          {scenic.level && <div className="floating-badge"><StatusBadge tone="orange">{scenic.level}</StatusBadge></div>}
          <button className="icon-btn favorite-btn" type="button" aria-label={`${favorite ? '取消收藏' : '收藏'}${scenic.name}`} aria-pressed={favorite} onClick={toggleFavorite}>
            <Heart size={18} fill={favorite ? 'var(--color-danger)' : 'rgba(0,0,0,0.5)'} color={favorite ? 'var(--color-danger)' : 'white'} />
          </button>
        </div>
        <div className="scenic-card-body">
          <div className="card-title-row">
            <h3>{scenic.name}</h3>
            {scenic.ticket_price && <span className="price-tag">{scenic.ticket_price}</span>}
          </div>
          {scenic.summary && <p className="summary">{scenic.summary}</p>}
          <div className="meta-grid">
            {scenic.rating && <span className="meta-item rating"><Star size={16} fill="currentColor" /> <strong>{scenic.rating}</strong></span>}
            <span className="meta-item"><MapPin size={16} /> <span>{scenic.address || scenic.city || '中国'}</span></span>
            {scenic.opening_hours && <span className="meta-item"><Clock size={16} /> <span>{scenic.opening_hours}</span></span>}
          </div>
          {scenic.tags?.length > 0 && <div className="tag-row">{scenic.tags.slice(0, 4).map((tag, i) => <span className="tag" key={`${tag}-${i}`}>{tag}</span>)}</div>}
        </div>
      </Link>
    )
  }

  if (variant === 'compact') {
    return (
      <Link to={`/scenic/${scenic.id}`} className="scenic-card variant-compact">
        <img src={imgSrc} onError={handleError} alt={scenic.name} loading="lazy" />
        <div className="scenic-card-body">
          <h4>{scenic.name}</h4>
          <div className="meta-line">
            {scenic.rating && <><Star size={14} fill="currentColor" /> {scenic.rating}</>}
            {scenic.distance && <><span className="dot-sep">·</span>{scenic.distance}km</>}
          </div>
        </div>
      </Link>
    )
  }

  // Default: grid
  return (
    <Link to={`/scenic/${scenic.id}`} className="scenic-card variant-grid">
      <div className="card-image-wrapper">
        <img src={imgSrc} onError={handleError} alt={scenic.name} loading="lazy" />
        <div className="overlay-gradient"></div>
        {scenic.level && <div className="floating-badge"><StatusBadge tone="orange">{scenic.level}</StatusBadge></div>}
        <button className="icon-btn favorite-btn" type="button" aria-label={`${favorite ? '取消收藏' : '收藏'}${scenic.name}`} aria-pressed={favorite} onClick={toggleFavorite}>
          <Heart size={20} fill={favorite ? 'var(--color-danger)' : 'rgba(0,0,0,0.3)'} color={favorite ? 'var(--color-danger)' : 'white'} />
        </button>
      </div>
      <div className="scenic-card-body">
        <div className="card-title-row">
          <h3>{scenic.name}</h3>
          {scenic.rating && <span className="rating-pill"><Star size={14} fill="currentColor" /> {scenic.rating}</span>}
        </div>
        <div className="meta-line text-muted">
          <MapPin size={14} /> {scenic.address || scenic.city || scenic.province || '中国'}
        </div>
        {scenic.tags?.length > 0 && (
          <div className="tag-row">{scenic.tags.slice(0, 3).map((tag, i) => <span className="tag" key={`${tag}-${i}`}>{tag}</span>)}</div>
        )}
      </div>
    </Link>
  )
}
