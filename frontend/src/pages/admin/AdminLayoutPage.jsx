import { useEffect, useState } from 'react'
import { Layout, Move, Plus, Trash2, Save, Eye, CheckCircle2, ChevronDown, ChevronUp, Globe, Settings, Sidebar, PanelTop, MousePointer2 } from 'lucide-react'
import { getPageLayout, savePageLayout, publishPageLayout, resetPageLayout, getComponentTemplates } from '../../api/admin.js'

export default function AdminLayoutPage() {
  const [scope, setScope] = useState('home')
  const [layout, setLayout] = useState(null)
  const [templates, setTemplates] = useState([])
  const [loading, setLoading] = useState(false)
  const [notice, setNotice] = useState('')

  const scopes = [
    { id: 'home', name: '推荐首页' },
    { id: 'scenic', name: '探索中国' },
    { id: 'themes', name: '主题旅行' },
    { id: 'map', name: '地图规划' },
    { id: 'community', name: '游客社区' },
    { id: 'user_center', name: '用户中心' },
  ]

  useEffect(() => {
    loadLayout(scope)
    getComponentTemplates().then(setTemplates)
  }, [scope])

  const loadLayout = async (s) => {
    setLoading(true)
    const res = await getPageLayout(s)
    setLayout(res?.layout || null)
    setLoading(false)
  }

  const moveModule = (index, direction) => {
    const nextModules = [...layout.modules]
    const targetIndex = index + direction
    if (targetIndex < 0 || targetIndex >= nextModules.length) return
    
    const temp = nextModules[index]
    nextModules[index] = nextModules[targetIndex]
    nextModules[targetIndex] = temp
    
    setLayout({ ...layout, modules: nextModules })
  }

  const toggleVisible = (index) => {
    const nextModules = [...layout.modules]
    nextModules[index].visible = !nextModules[index].visible
    setLayout({ ...layout, modules: nextModules })
  }

  const removeModule = (index) => {
    if (!confirm('确定移除该组件？')) return
    const nextModules = layout.modules.filter((_, i) => i !== index)
    setLayout({ ...layout, modules: nextModules })
  }

  const addModule = (template) => {
    const newMod = {
      ...template.config_json,
      id: `${scope}-${Date.now()}`,
      title: template.name,
      visible: true,
      order: layout.modules.length + 1
    }
    setLayout({ ...layout, modules: [...layout.modules, newMod] })
    setNotice(`已添加组件: ${template.name}`)
    setTimeout(() => setNotice(''), 3000)
  }

  const handleSave = async () => {
    setLoading(true)
    await savePageLayout(scope, layout)
    setNotice('草稿已保存')
    setLoading(false)
    setTimeout(() => setNotice(''), 3000)
  }

  const handlePublish = async () => {
    if (!confirm('发布后将立即对前台所有用户生效，确定发布？')) return
    setLoading(true)
    await publishPageLayout(scope)
    setNotice('页面布局已发布！')
    setLoading(false)
    setTimeout(() => setNotice(''), 3000)
  }

  return (
    <div className="dashboard-page admin-backstage-page admin-layout-workbench">
      {notice && <div className="notice">{notice}</div>}

      <section className="admin-command-hero">
        <div>
          <span className="admin-eyebrow"><Layout size={15} /> 可视化编排</span>
          <h1>页面可视化编排</h1>
          <p>自由调整前台页面模块顺序、显示状态和组件模板，让后台配置效果更直观。</p>
        </div>
        <div className="admin-command-actions">
          <button className="ghost-btn" onClick={() => resetPageLayout(scope).then(() => loadLayout(scope))}>重置默认</button>
          <button className="primary-btn" onClick={handleSave} disabled={loading}>保存草稿</button>
          <button className="primary-btn success" onClick={handlePublish} disabled={loading}>发布生效</button>
        </div>
      </section>

      <div className="admin-editor-grid">
        <aside className="admin-panel admin-page-switcher">
          <div className="admin-card-title">
            <Globe size={18} />
            <h3>目标页面</h3>
          </div>
          {scopes.map(s => (
            <button 
              key={s.id} 
              className={scope === s.id ? 'active' : ''}
              onClick={() => setScope(s.id)}
            >
              <span>{s.name}</span>
              <small>{s.id}</small>
            </button>
          ))}
          <div className="admin-editor-hint">
            <MousePointer2 size={17} />
            <span>使用上移/下移调整模块位置，发布后前台实时生效。</span>
          </div>
        </aside>

        <main className="admin-panel admin-layout-canvas">
          <div className="admin-card-title split">
            <div>
              <PanelTop size={20} />
              <h2>当前布局：{scopes.find(s => s.id === scope)?.name}</h2>
            </div>
            <span>{layout?.modules?.filter(mod => mod.visible).length || 0} 个模块可见</span>
          </div>

          <div className="admin-module-list">
            {layout?.modules?.map((mod, index) => (
              <article 
                key={mod.id} 
                className={`admin-module-card ${mod.visible ? '' : 'muted'}`}
              >
                <span className="admin-module-order">{String(index + 1).padStart(2, '0')}</span>
                <div className="admin-module-grip"><Move size={18} /></div>
                <div>
                  <strong>{mod.title}</strong>
                  <code>ID: {mod.id} · Type: {mod.type}</code>
                </div>
                <div className="admin-module-actions">
                  <button className="icon-btn" onClick={() => moveModule(index, -1)} disabled={index === 0} aria-label="上移模块"><ChevronUp size={16} /></button>
                  <button className="icon-btn" onClick={() => moveModule(index, 1)} disabled={index === layout.modules.length - 1} aria-label="下移模块"><ChevronDown size={16} /></button>
                  <button className={`icon-btn ${mod.visible ? 'active' : ''}`} onClick={() => toggleVisible(index)} aria-label="切换模块显示">
                    <Eye size={16} />
                  </button>
                  <button className="icon-btn danger" onClick={() => removeModule(index)} aria-label="删除模块"><Trash2 size={16} /></button>
                </div>
              </article>
            ))}
            {!layout?.modules?.length && <div className="admin-empty-result">该页面暂无组件</div>}
          </div>
        </main>

        <aside className="admin-panel admin-template-library">
          <div className="admin-card-title">
            <Plus size={20} />
            <h3>组件库</h3>
          </div>
          <div className="admin-template-list">
            {templates.map(tpl => (
              <article key={tpl.id} className="admin-template-card">
                <div>
                  <strong>{tpl.name}</strong>
                  <span>{tpl.category}</span>
                </div>
                <button 
                  className="ghost-btn" 
                  onClick={() => addModule(tpl)}
                >
                  添加至页面
                </button>
              </article>
            ))}
          </div>
        </aside>
      </div>
    </div>
  )
}
