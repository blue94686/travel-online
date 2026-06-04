export default function VersionHistoryModal({ versions = [], onSelect }) {
  return <div className="version-list">{versions.map(item => <button key={item.id} type="button" onClick={() => onSelect?.(item)}>v{item.version} · {item.created_at}</button>)}</div>
}
