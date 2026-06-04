export default function EmptyState({ title = '暂无数据', text = '稍后再来看看。' }) {
  return <div className="empty-state"><strong>{title}</strong><p>{text}</p></div>
}
