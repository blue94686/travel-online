import { Clock, MapPin, Navigation, TrendingUp } from 'lucide-react'
import { imageFallback } from '../../api/fallback.js'
import './RouteCard.css'

export default function RouteCard({ 
  route, 
  variant = 'overview', 
  onClick 
}) {
  const { title, summary, duration, distance, tags, stops, image, elevation } = route

  if (variant === 'timeline') {
    return (
      <article className="route-card variant-timeline" onClick={onClick}>
        <div className="route-header">
          <h3>{title}</h3>
          <div className="route-stats">
            <span><Navigation size={14} /> {distance || '12.5km'}</span>
            <span><Clock size={14} /> {duration || '4.5h'}</span>
            {elevation && <span><TrendingUp size={14} /> 累计爬升 {elevation}</span>}
          </div>
        </div>
        <div className="route-timeline">
          {(stops || ['起点', '途经点1', '途经点2', '终点']).map((stop, index, arr) => (
            <div className="timeline-stop" key={index}>
              <div className="stop-marker">
                <span className={index === 0 ? 'marker start' : index === arr.length - 1 ? 'marker end' : 'marker'} />
                {index < arr.length - 1 && <div className="stop-line" />}
              </div>
              <div className="stop-content">
                <strong>{stop.name || stop}</strong>
                {stop.desc && <p>{stop.desc}</p>}
              </div>
            </div>
          ))}
        </div>
        {tags && (
          <div className="tag-row">
            {tags.map(tag => <span className="tag" key={tag}>{tag}</span>)}
          </div>
        )}
      </article>
    )
  }

  // Default: overview
  return (
    <article className="route-card variant-overview" onClick={onClick}>
      <div className="card-image-wrapper">
        <img src={image || imageFallback} alt={title} onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = imageFallback }} />
        <div className="route-duration-badge"><Clock size={12} /> {duration || '半日游'}</div>
      </div>
      <div className="route-card-body">
        <h4>{title}</h4>
        <div className="route-flow">
          {(stops || ['起点', '终点']).slice(0, 4).map((stop, i, arr) => (
            <span key={i}>
              {stop.name || stop}
              {i < arr.length - 1 && <span className="arrow">→</span>}
            </span>
          ))}
        </div>
        {summary && <p className="summary">{summary}</p>}
        <div className="meta-line text-muted">
          <span><Navigation size={14} /> {distance || '5km'}</span>
          {tags?.[0] && <span className="tag-pill">{tags[0]}</span>}
        </div>
      </div>
    </article>
  )
}
