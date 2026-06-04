import { imageFallback } from '../../api/fallback.js'
import './UserStatsCard.css'

export default function UserStatsCard({ profile, stats, variant = 'dashboard' }) {
  const { name = '景小游', level = 'Lv.6 探索家', desc = '用脚步丈量世界，用镜头记录美好', avatar = imageFallback } = profile || {}
  const { visited = 36, favorites = 12, comments = 28, routes = 3, likes = '1.2w' } = stats || {}

  if (variant === 'sidebar') {
    return (
      <article className="user-stats-card variant-sidebar">
        <img src={avatar} alt={name} />
        <div className="sidebar-info">
          <h3>{name}</h3>
          <span className="level-badge">{level}</span>
        </div>
        <div className="sidebar-stats">
          <div><strong>{visited}</strong><span>足迹</span></div>
          <div><strong>{favorites}</strong><span>收藏</span></div>
          <div><strong>{routes}</strong><span>路线</span></div>
        </div>
      </article>
    )
  }

  // Default: dashboard
  return (
    <article className="user-stats-card variant-dashboard">
      <div className="dashboard-profile">
        <img src={avatar} alt={name} className="dashboard-avatar" />
        <div className="dashboard-info">
          <div className="title-row">
            <h1>{name}</h1>
            <span className="level-badge">{level}</span>
          </div>
          <p>{desc}</p>
          <div className="stats-row">
            <span><strong>{visited}</strong>已去景区</span>
            <span><strong>{favorites}</strong>收藏景区</span>
            <span><strong>{comments}</strong>评论数</span>
            <span><strong>{routes}</strong>路线数</span>
            <span><strong>{likes}</strong>获赞</span>
          </div>
        </div>
      </div>
      <div className="dashboard-level-box">
        <div className="title-row">
          <h3>{level}</h3>
          <span className="exp-text">2680 / 3500</span>
        </div>
        <div className="progress-bar"><div className="progress-fill" style={{ width: '76%' }}></div></div>
        <p className="level-hint">再获得 820 经验值升级到 Lv.7 旅行家</p>
      </div>
    </article>
  )
}
