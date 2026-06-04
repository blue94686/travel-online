import StatusBadge from './StatusBadge.jsx'

export default function ReviewCard({ item }) {
  return (
    <article className="review-card">
      <div className="avatar">{item.nickname?.slice(0, 1) || '游'}</div>
      <div>
        <div className="card-title-row"><strong>{item.nickname}</strong><StatusBadge tone={item.status === 'approved' ? 'primary' : 'orange'}>{item.status === 'approved' ? '已公开' : '审核中'}</StatusBadge></div>
        <p>{item.content}</p>
        <small>{item.rating ? `评分 ${item.rating} · ` : ''}点赞 {item.likes ?? 256} · 评论 {item.replies ?? 18}</small>
      </div>
    </article>
  )
}
