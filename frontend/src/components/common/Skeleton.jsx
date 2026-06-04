import './Skeleton.css'

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <div className="skeleton skeleton-img" />
      <div className="skeleton-body">
        <div className="skeleton skeleton-line medium" />
        <div className="skeleton skeleton-line short" />
        <div className="skeleton skeleton-line" />
      </div>
    </div>
  )
}

export function SkeletonList({ count = 6 }) {
  return (
    <div className="card-grid two">
      {Array.from({ length: count }).map((_, i) => <SkeletonCard key={i} />)}
    </div>
  )
}

export function SkeletonText({ lines = 3 }) {
  return (
    <div className="skeleton-text-block">
      {Array.from({ length: lines }).map((_, i) => (
        <div className="skeleton skeleton-line" key={i} style={{ width: i === lines - 1 ? '60%' : '100%' }} />
      ))}
    </div>
  )
}

export function SkeletonDetail() {
  return (
    <div style={{ display: 'grid', gap: 24 }}>
      <div className="skeleton skeleton-detail-hero" />
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 24 }}>
        <div style={{ display: 'grid', gap: 16 }}>
          <div className="skeleton" style={{ height: 28, width: '50%' }} />
          <SkeletonText lines={4} />
        </div>
        <div style={{ display: 'grid', gap: 16 }}>
          <div className="skeleton" style={{ height: 200 }} />
          <div className="skeleton" style={{ height: 120 }} />
        </div>
      </div>
    </div>
  )
}
