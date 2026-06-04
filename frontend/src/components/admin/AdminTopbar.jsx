import { useMemo, useState } from 'react'
import { Bell, ChevronDown, CircleHelp, Database, FileText, LayoutTemplate, RefreshCw, Search, ShieldCheck, Sparkles, X } from 'lucide-react'
import { useLocation, useNavigate } from 'react-router-dom'

const titleMap = {
  '/admin': ['欢迎回来，超级管理员', '景区在线管理后台总览'],
  '/admin/content': ['内容运营', '内容发布、图片审核、评论治理与页面推荐'],
  '/admin/images': ['图片审核', '图库、候选图片、版权来源与封面管理'],
  '/admin/comments': ['评论审核', '游客评论、风险识别、拉黑与治理'],
  '/admin/data': ['数据总览', '质量、同步、备份和全国景区数据资产'],
  '/admin/data/source': ['全国源表', '26 万景点源表、导入状态与三级浏览支撑'],
  '/admin/data/quality': ['质量检查', '缺图、坐标、来源和资料完整度体检'],
  '/admin/scenic': ['正式景区库', '审核后展示的景区资料和媒体索引'],
  '/admin/automation': ['自动化与服务', '同步任务、AI 能力、API 接入与服务巡检'],
  '/admin/integration': ['API 与服务接入', '地图、高德、天气与外部服务管理'],
  '/admin/api': ['API 与服务接入', '地图、高德、天气与外部服务密钥配置'],
  '/admin/services': ['服务巡检', '微服务状态、接口延迟与调用日志'],
  '/admin/earth-online': ['地球 Online 管理', '实况来源、授权状态与可用性检测'],
  '/admin/enrichment': ['资料补全', '外部来源、候选审核和源表补图任务'],
  '/admin/web-enrichment': ['全网更新中心', '旅游景区图片、介绍、周边和 POI 自动管理'],
  '/admin/database': ['数据资产', '景区数据、导入任务、SQL 终端与质量治理'],
  '/admin/layout': ['页面编排', '模块布局、组件模板与发布管理'],
  '/admin/workbench': ['页面工作台', '模块组合、草稿预览和发布版本'],
  '/admin/system': ['系统与安全', '权限审计、用户管理与微服务监控'],
  '/admin/users': ['用户管理', '用户列表、角色状态和账号治理'],
  '/admin/roles': ['权限矩阵', '角色权限、后台访问和操作边界'],
  '/admin/security': ['安全策略', '路由守卫、Key 脱敏和风险控制'],
  '/admin/settings': ['系统配置', '站点默认值、图片策略和资料补全开关'],
  '/admin/logs': ['操作日志', '后台操作、API 检查和审计记录'],
}

const roleLabelMap = {
  super_admin: '超级管理员',
  admin: '管理员',
  user: '普通用户',
}

const commandItems = [
  { label: '管理总览', desc: '查看核心指标、审核队列、系统日志', path: '/admin', icon: Sparkles, keywords: 'dashboard kpi 总览 审核 日志' },
  { label: '内容运营', desc: '处理文章、Banner 与攻略内容', path: '/admin/content', icon: FileText, keywords: '内容 文章 banner 攻略 公告' },
  { label: '图片审核', desc: '处理图库候选、封面和版权来源', path: '/admin/images', icon: FileText, keywords: '图片 图库 候选 版权 封面' },
  { label: '数据资产', desc: '景区数据、批量导入、SQL 查询与备份', path: '/admin/database', icon: Database, keywords: '数据库 景区 导入 SQL 备份' },
  { label: '资料补全', desc: '公开来源、高德 POI 与图片补全候选', path: '/admin/enrichment', icon: Sparkles, keywords: '资料补全 高德 图片 候选 来源' },
  { label: '全网更新中心', desc: '全网更新景区图片、介绍、周边和 POI 候选', path: '/admin/web-enrichment', icon: Sparkles, keywords: '全网更新 爬虫 图片 介绍 周边 POI 美食 徒步' },
  { label: '页面编排', desc: '配置前台模块、组件模板和发布版本', path: '/admin/layout', icon: LayoutTemplate, keywords: '页面 模块 组件 发布 版本' },
  { label: '自动化与服务', desc: '同步任务、AI、地图天气 API 与服务巡检', path: '/admin/automation', icon: Sparkles, keywords: '自动化 AI API 地图 天气 服务' },
  { label: '系统与安全', desc: '用户、权限、黑名单、系统日志和健康监控', path: '/admin/system', icon: ShieldCheck, keywords: '系统 安全 用户 权限 黑名单 监控' },
]

const notifications = [
  { title: '待审核图片', text: '2 张景区图片等待处理', tone: 'warning', path: '/admin/images' },
  { title: '数据同步完成', text: '景区基础数据已完成增量同步', tone: 'success', path: '/admin/automation' },
  { title: '数据库备份建议', text: '建议今天完成一次手动备份', tone: 'info', path: '/admin/database' },
]

export default function AdminTopbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const [title, subtitle] = titleMap[location.pathname] || ['运营控制台', '数据、审核、接口与安全状态']
  const [query, setQuery] = useState('')
  const [searchOpen, setSearchOpen] = useState(false)
  const [noticeOpen, setNoticeOpen] = useState(false)
  const [helpOpen, setHelpOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const user = (() => {
    try { return JSON.parse(localStorage.getItem('scenic-user') || '{}') } catch { return {} }
  })()
  const role = user.role || localStorage.getItem('mock_user_role') || 'super_admin'
  const roleLabel = roleLabelMap[role] || role
  const filteredCommands = useMemo(() => {
    const keyword = query.trim().toLowerCase()
    if (!keyword) return commandItems.slice(0, 5)
    return commandItems.filter(item => `${item.label} ${item.desc} ${item.keywords}`.toLowerCase().includes(keyword)).slice(0, 6)
  }, [query])

  const runCommand = (path) => {
    setSearchOpen(false)
    setNoticeOpen(false)
    setHelpOpen(false)
    setQuery('')
    navigate(path)
  }

  const refreshPage = () => {
    setRefreshing(true)
    window.setTimeout(() => window.location.reload(), 600)
  }

  const submitSearch = (event) => {
    event.preventDefault()
    if (filteredCommands[0]) runCommand(filteredCommands[0].path)
  }

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-title"><strong>{title}</strong><span>{subtitle}</span></div>
      <form className="admin-topbar-search" role="search" onSubmit={submitSearch}>
        <Search size={17} />
        <input
          value={query}
          placeholder="搜索功能、数据、用户、日志"
          aria-label="搜索后台功能"
          onChange={event => {
            setQuery(event.target.value)
            setSearchOpen(true)
          }}
          onFocus={() => setSearchOpen(true)}
        />
        {query && <button type="button" className="admin-search-clear" aria-label="清空搜索" onClick={() => setQuery('')}><X size={14} /></button>}
        {searchOpen && (
          <div className="admin-command-palette">
            <div className="admin-command-palette-head">
              <strong>快速跳转</strong>
              <span>Enter 打开第一个结果</span>
            </div>
            {filteredCommands.length ? filteredCommands.map(item => {
              const Icon = item.icon
              return (
                <button type="button" key={item.path} onMouseDown={event => event.preventDefault()} onClick={() => runCommand(item.path)}>
                  <Icon size={17} />
                  <span><b>{item.label}</b><small>{item.desc}</small></span>
                </button>
              )
            }) : <div className="admin-command-empty">没有找到相关后台功能</div>}
          </div>
        )}
      </form>
      <div className="admin-topbar-meta">
        <span>在线服务 12</span>
        <span>待处理 {notifications.length + 1}</span>
      </div>
      <div className="admin-topbar-actions">
        <div className="admin-popover-wrap">
          <button type="button" className="icon-btn admin-bell-btn" title="通知中心" aria-expanded={noticeOpen} onClick={() => { setNoticeOpen(value => !value); setHelpOpen(false); setSearchOpen(false) }}>
            <Bell size={18} /><span>{notifications.length}</span>
          </button>
          {noticeOpen && (
            <div className="admin-popover admin-notice-popover">
              <div className="admin-popover-head"><strong>通知中心</strong><button type="button" aria-label="关闭通知" onClick={() => setNoticeOpen(false)}><X size={15} /></button></div>
              {notifications.map(item => (
                <button type="button" key={item.title} className={`admin-notice-item ${item.tone}`} onClick={() => runCommand(item.path)}>
                  <i />
                  <span><b>{item.title}</b><small>{item.text}</small></span>
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="admin-popover-wrap">
          <button type="button" className="ghost-btn" aria-expanded={helpOpen} onClick={() => { setHelpOpen(value => !value); setNoticeOpen(false); setSearchOpen(false) }}><CircleHelp size={17} /> 帮助中心</button>
          {helpOpen && (
            <div className="admin-popover admin-help-popover">
              <div className="admin-popover-head"><strong>帮助中心</strong><button type="button" aria-label="关闭帮助" onClick={() => setHelpOpen(false)}><X size={15} /></button></div>
              <div className="admin-help-grid">
                {[
                  ['内容审核', '图片和评论在内容运营中集中处理。', '/admin/content'],
                  ['数据维护', '景区导入、SQL 查询、备份在数据资产中执行。', '/admin/database'],
                  ['页面发布', '首页和功能模块通过页面编排发布。', '/admin/layout'],
                ].map(([name, text, path]) => (
                  <button type="button" key={name} onClick={() => runCommand(path)}><b>{name}</b><span>{text}</span></button>
                ))}
              </div>
            </div>
          )}
        </div>
        <button type="button" className="ghost-btn" onClick={refreshPage} disabled={refreshing} aria-busy={refreshing}>
          <RefreshCw size={17} /> {refreshing ? '刷新中...' : '刷新'}
        </button>
        <div className="admin-user-chip">
          <span className="admin-avatar">管</span>
          <div><strong>{roleLabel}</strong><span>{user.nickname || '系统管理员'}</span></div>
          <ChevronDown size={15} />
        </div>
      </div>
    </header>
  )
}
