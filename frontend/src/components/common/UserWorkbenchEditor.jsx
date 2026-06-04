import { Copy, Eye, EyeOff, GripVertical } from 'lucide-react'

export default function UserWorkbenchEditor({ modules = [], onMove, onToggle, onCopy, onWidthChange }) {
  return (
    <div className="user-compose-canvas">
      {modules.map((item, index) => {
        const width = item.width || 'half'
        return (
          <article
            className={`user-compose-module width-${width} ${item.visible === false ? 'muted' : ''}`}
            draggable
            key={item.id}
            onDragStart={event => event.dataTransfer.setData('text/plain', String(index))}
            onDragOver={event => event.preventDefault()}
            onDrop={event => onMove?.(Number(event.dataTransfer.getData('text/plain')), index)}
          >
            <div className="user-compose-toolbar">
              <span><GripVertical size={15} /> {item.title}</span>
              <div>
                <button type="button" onClick={() => onToggle?.(item)}>{item.visible === false ? <EyeOff size={15} /> : <Eye size={15} />}</button>
                <button type="button" onClick={() => onCopy?.(item)}><Copy size={15} /></button>
              </div>
            </div>
            <div className="user-compose-preview"><div className="compose-lines"><span /><span /><span /></div></div>
            <label>宽度<select value={width} onChange={event => onWidthChange?.(item, event.target.value)}>{['full', 'half', 'third', 'quarter'].map(value => <option value={value} key={value}>{value}</option>)}</select></label>
          </article>
        )
      })}
    </div>
  )
}
