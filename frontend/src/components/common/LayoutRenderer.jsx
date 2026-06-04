import { useEffect, useMemo, useState } from 'react'
import { request } from '../../api/client.js'
import EmptyState from './EmptyState.jsx'

const role = () => localStorage.getItem('scenic-role') || 'guest'

function fallbackLayout(pageKey) {
  return {
    pageKey,
    theme: 'fresh-scenic',
    modules: [
      { id: `${pageKey}-hero`, type: 'hero', title: '今天去哪玩？', subtitle: '极客旅行 · 精准规划 · 实时掌握', visible: true, width: 'full', roleVisible: ['guest', 'user', 'admin', 'super_admin'], dataSource: 'scenic' },
      { id: `${pageKey}-list`, type: 'scenic_cards', title: '精选内容', visible: true, width: 'half', roleVisible: ['guest', 'user', 'admin', 'super_admin'], dataSource: 'scenic' }
    ]
  }
}

export default function LayoutRenderer({ pageKey, renderModule, emptyAction }) {
  const [layout, setLayout] = useState(fallbackLayout(pageKey))
  const [error, setError] = useState('')

  useEffect(() => {
    request(`/api/layouts/${pageKey}`, {}, null).then(data => {
      const next = data?.layout
      if (!next || (!Array.isArray(next.modules) && !Array.isArray(next.components))) {
        setLayout(fallbackLayout(pageKey))
        setError('布局损坏，已回退默认布局')
        return
      }
      setLayout({ ...next, modules: next.modules || next.components || [] })
      setError('')
    })
  }, [pageKey])

  const modules = useMemo(() => {
    const currentRole = role()
    return (layout.modules || []).filter(item => item.visible !== false && (!item.roleVisible || item.roleVisible.includes(currentRole)))
  }, [layout])

  if (!modules.length) {
    return <EmptyState title="当前页面暂无启用模块" text={error || '可以在后台页面编排中恢复默认或发布布局。'} action={emptyAction} />
  }

  return (
    <div className={`layout-renderer theme-${layout.theme || 'fresh-scenic'}`}>
      {error && <div className="notice">{error}</div>}
      {modules.map((item, index) => {
        try {
          return renderModule ? renderModule(item, index) : <section className={`panel width-${item.width || 'full'}`} key={item.id}><h2>{item.title}</h2><p>{item.subtitle || item.dataSource}</p></section>
        } catch (moduleError) {
          return <section className="panel" key={item.id}><h2>{item.title}</h2><p>模块渲染异常，其他模块不受影响。</p></section>
        }
      })}
    </div>
  )
}
