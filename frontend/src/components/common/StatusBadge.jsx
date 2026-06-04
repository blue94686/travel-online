export default function StatusBadge({ children, tone = 'primary' }) {
  return <span className={`status-badge ${tone}`}>{children}</span>
}
