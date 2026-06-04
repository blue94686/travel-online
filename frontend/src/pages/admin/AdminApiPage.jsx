import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, Copy, Plus, RefreshCw, Zap, Activity, Globe } from 'lucide-react'
import { checkApiHealth, getApiConfig, getApiLogs, saveApiConfig } from '../../api/admin.js'
import AdminKpiCard from '../../components/admin/AdminKpiCard.jsx'

const tabs = ['已接入服务', '调用日志']
const serviceLabels = {
  amap: '高德地图前端 JS API',
  amap_js_security: '高德地图安全密钥',
  amap_web_service: '高德 Web 服务 API',
  map: '地图服务',
  mapbox: 'Mapbox 地图',
  weather: '天气服务',
  qweather: '和风天气 API',
  image: '图片搜索服务',
  scenic: '景区内容服务',
  object_storage: '对象存储',
  mail_sms: '邮件/短信通知',
  webhook: 'Webhook 回调',
  bing_search: 'Bing Search API',
  bing_image: 'Bing Image Search',
  amap_weather: '高德天气',
  wikimedia_commons: 'Wikimedia Commons 图片',
  wikipedia: 'Wikipedia 景区介绍',
  wikivoyage: 'Wikivoyage 徒步与攻略',
  openstreetmap_overpass: 'OpenStreetMap Overpass',
  mct_official: '国家文旅部官方名录',
  ctrip_open: '携程开放平台',
  mafengwo: '马蜂窝 API',
  baidu_map: '百度地图 POI',
  tencent_lbs: '腾讯位置服务',
  scenic_enrichment: '景区资料补全',
  earth_check: '地球 Online 检测',
  image_candidate: '图片候选审核',
}

export default function AdminApiPage() {
  const [configs, setConfigs] = useState([])
  const [logs, setLogs] = useState([])
  const [activeTab, setActiveTab] = useState('已接入服务')
  const [notice, setNotice] = useState('')
  const [checking, setChecking] = useState('')
  const [refreshing, setRefreshing] = useState(false)
  const [editing, setEditing] = useState(null)

  const refreshData = async (showNotice = false) => {
    setRefreshing(true)
    try {
      const [nextConfigs, nextLogs] = await Promise.all([getApiConfig(), getApiLogs()])
      setConfigs(nextConfigs || [])
      setLogs(nextLogs || [])
      if (showNotice) setNotice(`已刷新 ${nextConfigs?.length || 0} 个服务配置和 ${nextLogs?.length || 0} 条日志`)
    } catch (error) {
      setNotice(`刷新失败：${error.message || '请检查后端服务'}`)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => { refreshData() }, [])

  const overview = useMemo(() => ({
    connected: configs.filter(item => item.enabled).length,
    total: configs.length,
  }), [configs])

  const save = async (item, patch = {}) => {
    const next = { ...item, ...patch }
    const saved = await saveApiConfig(next)
    const savedRow = { ...next, provider: saved?.provider || next.provider, label: saved?.label || next.label, api_key_masked: saved?.api_key_masked || next.api_key_masked }
    setConfigs(current => item.provider === 'new' ? [savedRow, ...current] : current.map(row => row.provider === item.provider ? savedRow : row))
    setNotice(`${serviceLabels[item.provider] || item.label} 已保存`)
    setEditing(null)
  }

  const health = async (provider) => {
    setChecking(provider)
    const result = await checkApiHealth(provider)
    setNotice(result?.message || `测试完成: ${result?.status}`)
    getApiLogs().then(data => setLogs(data || []))
    setChecking('')
  }

  return (
    <>
      {notice && <div className="notice" style={{ marginBottom: 16 }}>{notice}</div>}

      <section className="section-header">
        <div><h1 style={{ fontSize: 24, margin: 0 }}>API 与服务接入</h1><p style={{ color: 'var(--color-muted)', margin: '4px 0 0' }}>统一管理外部 API Keys 与服务状态</p></div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="ghost-btn" onClick={() => refreshData(true)} disabled={refreshing}>
            <RefreshCw size={16} /> {refreshing ? '刷新中...' : '刷新'}
          </button>
          <button className="primary-btn" onClick={() => setEditing({ provider: 'new', label: '自定义服务', enabled: 1, endpoint: '', api_key_masked: '' })}><Plus size={16} /> 新增服务</button>
        </div>
      </section>

      <section className="kpi-grid">
        <AdminKpiCard label="已启用服务" value={overview.connected} change={`共 ${overview.total} 个`} icon={Zap} />
        <AdminKpiCard label="服务健康" value="99.1%" change="正常运行" icon={Activity} />
        <AdminKpiCard label="平均延迟" value="54ms" change="全部服务" icon={Globe} />
      </section>

      <div className="tab-nav panel" style={{ display: 'flex', gap: 10, padding: 10, marginBottom: 24 }}>
        {tabs.map(tab => <button className={`ghost-btn ${activeTab === tab ? 'active' : ''}`} style={activeTab === tab ? { background: 'var(--color-primary-soft)', color: 'var(--color-primary)' } : {}} onClick={() => setActiveTab(tab)} key={tab}>{tab}</button>)}
      </div>

      {editing && <form className="modal-panel" onSubmit={(e) => { e.preventDefault(); save(editing) }}>
        <h2>{editing.provider === 'new' ? '新增服务' : `编辑 ${serviceLabels[editing.provider] || editing.label}`}</h2>
        <div className="input-group">
          <label>服务名称</label>
          <input className="form-input" value={editing.label} onChange={e => setEditing({ ...editing, label: e.target.value })} disabled={editing.provider !== 'new'} style={{ background: editing.provider !== 'new' ? '#f5f8fb' : '#fff' }} />
        </div>
        <div className="input-group">
          <label>Endpoint</label>
          <input className="form-input" value={editing.endpoint || ''} onChange={e => setEditing({ ...editing, endpoint: e.target.value })} placeholder="https://restapi.amap.com" />
        </div>
        <div className="input-group">
          <label>API Key / Secret</label>
          <input className="form-input" type="password" value={editing.api_key_masked || ''} onChange={e => setEditing({ ...editing, api_key_masked: e.target.value })} placeholder="输入 Key" />
        </div>
        <label className="switch-row" style={{ marginTop: 16, background: 'var(--color-bg)', padding: 12, borderRadius: 8 }}>
          启用
          <input type="checkbox" checked={Boolean(editing.enabled)} onChange={(e) => setEditing({ ...editing, enabled: e.target.checked ? 1 : 0 })} />
        </label>
        <div className="admin-actions" style={{ marginTop: 24 }}><button className="primary-btn">保存</button><button type="button" onClick={() => setEditing(null)}>取消</button></div>
      </form>}

      {activeTab === '已接入服务' && <section className="admin-panel">
        <div className="data-table">
          <div className="tr th" style={{ display: 'grid', gridTemplateColumns: '2fr 3fr 1fr 2fr', gap: 16, padding: '12px 16px', background: 'var(--color-bg)', borderRadius: 8, color: 'var(--color-muted)', fontSize: 13 }}>
            <span>服务名称</span><span>API Key</span><span>状态</span><span style={{ textAlign: 'right' }}>操作</span>
          </div>
          {configs.map(item => (
            <div className="tr" key={item.provider} style={{ display: 'grid', gridTemplateColumns: '2fr 3fr 1fr 2fr', gap: 16, padding: 16, borderBottom: '1px solid var(--color-border)', alignItems: 'center' }}>
              <span style={{ fontWeight: 600 }}>{serviceLabels[item.provider] || item.label}</span>
              <span style={{ color: 'var(--color-muted)', fontFamily: 'monospace' }}>{item.api_key_masked || '-'}</span>
              <span>{item.enabled ? <span className="status-badge success">已启用</span> : <span className="status-badge">未启用</span>}</span>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button className="ghost-btn" disabled={checking === item.provider} onClick={() => health(item.provider)}>{checking === item.provider ? '测试中...' : '测试'}</button>
                <button className="ghost-btn" onClick={() => setEditing(item)}>编辑</button>
              </div>
            </div>
          ))}
        </div>
      </section>}

      {activeTab === '调用日志' && <section className="admin-panel">
        <div className="data-table">
          <div className="tr th" style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 80px 80px 3fr', gap: 16, padding: '12px 16px', background: 'var(--color-bg)', borderRadius: 8, color: 'var(--color-muted)', fontSize: 13 }}>
            <span>服务</span><span>端点</span><span>状态</span><span>延迟</span><span>结果</span>
          </div>
          {logs.slice(0, 15).map(log => (
            <div className="tr" key={log.id} style={{ display: 'grid', gridTemplateColumns: '1fr 2fr 80px 80px 3fr', gap: 16, padding: 12, borderBottom: '1px solid var(--color-border)', fontSize: 13, alignItems: 'center' }}>
              <strong>{serviceLabels[log.provider] || log.provider}</strong>
              <span style={{ color: 'var(--color-muted)', fontFamily: 'monospace' }}>{log.endpoint}</span>
              <span style={{ color: log.status_code === 200 ? 'var(--color-primary)' : 'var(--color-danger)' }}>{log.status_code}</span>
              <span>{log.latency_ms}ms</span>
              <span style={{ color: 'var(--color-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }} title={log.result}>{log.result}</span>
            </div>
          ))}
          {logs.length === 0 && <div style={{ padding: 40, textAlign: 'center', color: 'var(--color-muted)' }}>暂无调用日志</div>}
        </div>
      </section>}
    </>
  )
}
