export default function AdminKpiCard({ label, value, change, icon: Icon }) {
  return (
    <article className="kpi-card">
      <div className="kpi-head">
        {Icon && <span className="kpi-icon"><Icon size={18} /></span>}
        <span>{label}</span>
      </div>
      <strong>{value}</strong>
      <em>{change || '+0.0%'} 较昨日</em>
    </article>
  )
}
