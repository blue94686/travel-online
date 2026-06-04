export default function ComponentTemplatePanel({ templates = [], onAdd }) {
  return (
    <div className="component-group template-panel">
      <h3>已保存模板</h3>
      {templates.map(item => <button key={item.id} type="button" onClick={() => onAdd?.(item)}>{item.name}</button>)}
    </div>
  )
}
