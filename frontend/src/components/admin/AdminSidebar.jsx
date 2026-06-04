import { NavLink, useLocation } from 'react-router-dom'
import { BarChart3, Bot, ClipboardCheck, Database, FileSearch, Image, LayoutTemplate, MapPinned, PanelLeftClose, PanelLeftOpen, ShieldCheck, Sparkles, Table2 } from 'lucide-react'

const navGroups = [
  {
    title: '后台功能',
    items: [
      { to: '/admin', label: '管理总览', desc: '指标 · 审核 · 日志', icon: BarChart3, match: ['/admin'] },
      { to: '/admin/content', label: '内容运营', desc: '文章 · Banner', icon: LayoutTemplate, match: ['/admin/content'] },
      { to: '/admin/images', label: '图片审核', desc: '图库 · 候选 · 版权', icon: Image, match: ['/admin/images'] },
      { to: '/admin/comments', label: '评论审核', desc: '评论 · 拉黑 · 风险', icon: ClipboardCheck, match: ['/admin/comments'] },
      { to: '/admin/data', label: '数据总览', desc: '质量 · 同步 · 备份', icon: Database, match: ['/admin/data'] },
      { to: '/admin/data/source', label: '全国源表', desc: '26 万景点 · 导入', icon: FileSearch, match: ['/admin/data/source'] },
      { to: '/admin/scenic', label: '正式景区库', desc: '审核后景区资料', icon: MapPinned, match: ['/admin/scenic'] },
      { to: '/admin/database', label: '数据表工作台', desc: 'SQL · 表 · 索引', icon: Table2, match: ['/admin/database'] },
      { to: '/admin/enrichment', label: '资料补全', desc: '外部来源 · 候选', icon: Sparkles, match: ['/admin/enrichment'] },
      { to: '/admin/web-enrichment', label: '全网更新', desc: '图片 · 介绍 · POI', icon: Sparkles, match: ['/admin/web-enrichment'] },
      { to: '/admin/data/quality', label: '质量检查', desc: '缺图 · 坐标 · 来源', icon: ShieldCheck, match: ['/admin/data/quality'] },
      { to: '/admin/layout', label: '页面编排', desc: '模块 · 组件 · 发布', icon: Sparkles, match: ['/admin/layout', '/admin/workbench'] },
      { to: '/admin/automation', label: '自动化与服务', desc: '任务 · AI · API', icon: Bot, match: ['/admin/automation', '/admin/integration', '/admin/api', '/admin/services', '/admin/earth-online'] },
      { to: '/admin/system', label: '系统与安全', desc: '用户 · 监控 · 日志', icon: ShieldCheck, match: ['/admin/system', '/admin/users', '/admin/roles', '/admin/security', '/admin/settings', '/admin/logs'] },
    ],
  },
]

export default function AdminSidebar({ collapsed = false, onToggle }) {
  const location = useLocation()
  const isActive = (item) => item.match.includes(location.pathname)

  return (
    <aside className="admin-sidebar admin-shell-polish">
      <div className="admin-brand">
        <div>景区在线<span>Scenic Online</span></div>
        <button className="admin-collapse-btn" type="button" onClick={onToggle} title={collapsed ? '展开侧边栏' : '收起侧边栏'}>
          {collapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
        </button>
      </div>

      <nav className="admin-nav-sections" aria-label="后台导航">
        {navGroups.map(group => (
          <section className="admin-nav-group" key={group.title}>
            <small>{group.title}</small>
            <div className="admin-nav-group-items">
              {group.items.map(item => {
                const Icon = item.icon
                return (
                <NavLink
                  key={item.to}
                  end={item.to === '/admin'}
                  to={item.to}
                  title={`${item.label}：${item.desc}`}
                  className={() => (isActive(item) ? 'active' : '')}
                >
                  <Icon size={19} />
                  <span><b>{item.label}</b><small>{item.desc}</small></span>
                </NavLink>
                )
              })}
            </div>
          </section>
        ))}
      </nav>

      <div className="admin-sidebar-health">
        <div className="admin-sidebar-health-title">
          <i />
          <strong>系统运行正常</strong>
        </div>
        <dl>
          <div><dt>当前版本</dt><dd>v2.5.0</dd></div>
          <div><dt>最后登录</dt><dd>今天 12:00</dd></div>
          <div><dt>服务状态</dt><dd>100%</dd></div>
        </dl>
      </div>
    </aside>
  )
}
