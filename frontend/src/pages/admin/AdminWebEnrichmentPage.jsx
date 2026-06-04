import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  AlertTriangle,
  CheckCircle2,
  ExternalLink,
  Filter,
  Globe2,
  Image,
  MapPinned,
  PauseCircle,
  PlayCircle,
  RefreshCw,
  Route,
  Settings2,
  ShieldCheck,
  Sparkles,
  Utensils,
} from 'lucide-react'
import {
  approveLowRiskCrawlerCandidates,
  getCrawlerEnrichmentStatus,
  getWebEnrichmentCandidates,
  getWebEnrichmentOverview,
  runCrawlerEnrichmentBatch,
  startCrawlerEnrichmentJob,
  stopCrawlerEnrichmentJob,
} from '../../api/admin.js'

const metricDefs = [
  ['missingImages', '缺图景区', Image],
  ['missingProfiles', '缺介绍', Sparkles],
  ['missingFood', '缺美食 POI', Utensils],
  ['missingPois', '缺周边 POI', MapPinned],
  ['pendingCandidates', '待审核候选', Filter],
  ['lowRiskCandidates', '低风险可通过', ShieldCheck],
]

const tabs = [
  ['all', '全部候选'],
  ['image', '图片外链'],
  ['profile', '景区介绍'],
  ['food', '周边美食'],
  ['hiking', '徒步 POI'],
  ['high', '高风险'],
]

const targetOptions = [
  ['all', '全部缺失'],
  ['images', '只补图片'],
  ['profiles', '只补介绍'],
  ['food', '周边美食'],
  ['hiking', '徒步 POI'],
]

const valueOrDash = value => (value === undefined || value === null || value === '' ? '--' : Number(value).toLocaleString())
const jobStatus = job => job?.status || 'idle'
const riskLabel = risk => ({ low: '低风险', medium: '中风险', high: '高风险' }[risk] || '未分级')

function buildPolicy(policy) {
  return {
    batch_size: policy.batchSize,
    max_total: policy.maxTotal,
    province: policy.province,
    city: policy.city,
    only_missing: true,
    include_public_sources: policy.includePublicSources,
    include_pois: policy.includePois,
    include_paid_providers: policy.include_paid_providers,
    include_osm: policy.includeOsm,
    sleep_seconds: policy.sleepSeconds,
  }
}

export default function AdminWebEnrichmentPage() {
  const [overview, setOverview] = useState(null)
  const [crawler, setCrawler] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [activeTab, setActiveTab] = useState('all')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [policy, setPolicy] = useState({
    target: 'all',
    province: '',
    city: '',
    batchSize: 5,
    maxTotal: 2528,
    sleepSeconds: 1.5,
    includePublicSources: true,
    includePois: true,
    includeOsm: true,
    include_paid_providers: false,
  })

  const candidateQuery = useMemo(() => {
    if (activeTab === 'high') return { type: 'all', risk: 'high', limit: 40 }
    return { type: activeTab, risk: 'all', limit: 40 }
  }, [activeTab])

  const refresh = async () => {
    const [nextOverview, nextCrawler, nextCandidates] = await Promise.all([
      getWebEnrichmentOverview(),
      getCrawlerEnrichmentStatus(),
      getWebEnrichmentCandidates(candidateQuery),
    ])
    setOverview(nextOverview || null)
    setCrawler(nextCrawler || null)
    setCandidates(nextCandidates?.items || [])
  }

  useEffect(() => {
    refresh().catch(() => {})
  }, [candidateQuery])

  useEffect(() => {
    if (!crawler?.running) return undefined
    const timer = setInterval(() => refresh().catch(() => {}), 5000)
    return () => clearInterval(timer)
  }, [crawler?.running, candidateQuery])

  const runAction = async (action) => {
    setLoading(true)
    try {
      const payload = buildPolicy(policy)
      if (action === 'refresh') {
        await refresh()
        setNotice('状态已刷新。')
      }
      if (action === 'trial') {
        const result = await runCrawlerEnrichmentBatch({ ...payload, limit: policy.batchSize })
        setNotice(`试跑一批完成：资料候选 ${result?.profileCandidates || 0}，图片候选 ${result?.imageCandidates || 0}，低风险 ${result?.lowRiskCandidates || 0}。`)
      }
      if (action === 'start') {
        await startCrawlerEnrichmentJob(payload)
        setNotice('后台全网更新任务已启动，采集内容默认进入候选池。')
      }
      if (action === 'stop') {
        await stopCrawlerEnrichmentJob()
        setNotice('已请求停止任务，当前批次完成后会停止。')
      }
      if (action === 'approve') {
        const result = await approveLowRiskCrawlerCandidates({ limit: 200 })
        setNotice(`批量通过低风险完成：图片 ${result?.approvedImages || 0}，POI ${result?.approvedPois || 0}，跳过 ${result?.skipped || 0}。`)
      }
      await refresh()
    } finally {
      setLoading(false)
    }
  }

  const updatePolicy = (key, value) => setPolicy(current => ({ ...current, [key]: value }))
  const status = jobStatus(crawler || overview?.crawlerJob)
  const recentTasks = overview?.recentTasks || []

  return (
    <div className="dashboard-page admin-backstage-page admin-web-enrichment-page">
      {notice && <div className="notice">{notice}</div>}

      <section className="admin-command-hero web-enrichment-hero">
        <div>
          <span className="admin-eyebrow"><Globe2 size={15} /> 全网自动管理</span>
          <h1>全网更新中心</h1>
          <p>统一管理旅游景区图片、介绍、周边美食、周边 POI 和徒步 POI。所有采集内容默认进入候选池，低风险内容可批量通过。</p>
        </div>
        <div className="admin-command-actions">
          <span className={`status-badge ${status === 'running' ? 'success' : status === 'failed' ? 'danger' : 'warning'}`}>
            <CheckCircle2 size={14} /> {status}
          </span>
          <button className="ghost-btn" type="button" disabled={loading} onClick={() => runAction('refresh')}><RefreshCw size={16} /> 刷新状态</button>
          <button className="ghost-btn" type="button" disabled={loading} onClick={() => runAction('trial')}><PlayCircle size={16} /> 试跑一批</button>
          <button className="primary-btn" type="button" disabled={loading} onClick={() => runAction('start')}><PlayCircle size={16} /> 启动后台更新</button>
          <button className="ghost-btn danger" type="button" disabled={loading} onClick={() => runAction('stop')}><PauseCircle size={16} /> 停止任务</button>
        </div>
      </section>

      <section className="web-enrichment-strategy admin-panel">
        <div className="admin-card-title split">
          <div><Settings2 size={20} /><h2>策略配置</h2></div>
          <span>公开来源与 OSM 默认开启，付费来源默认关闭</span>
        </div>
        <div className="web-strategy-grid">
          <label>更新目标
            <select value={policy.target} onChange={event => updatePolicy('target', event.target.value)}>
              {targetOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <label>省份范围
            <input value={policy.province} onChange={event => updatePolicy('province', event.target.value)} placeholder="留空为全国" />
          </label>
          <label>城市范围
            <input value={policy.city} onChange={event => updatePolicy('city', event.target.value)} placeholder="留空为全部城市" />
          </label>
          <label>批次大小
            <input type="number" min="1" max="50" value={policy.batchSize} onChange={event => updatePolicy('batchSize', Number(event.target.value || 1))} />
          </label>
          <label>最大处理
            <input type="number" min="1" max="50000" value={policy.maxTotal} onChange={event => updatePolicy('maxTotal', Number(event.target.value || 1))} />
          </label>
          <label>间隔秒数
            <input type="number" min="0.5" max="5" step="0.5" value={policy.sleepSeconds} onChange={event => updatePolicy('sleepSeconds', Number(event.target.value || 0.5))} />
          </label>
        </div>
        <div className="web-source-toggles">
          {[
            ['includePublicSources', '公开来源', 'Wikipedia / Wikimedia / Wikivoyage'],
            ['includeOsm', 'OSM', '开放地图与徒步线索'],
            ['includePois', '周边 POI', '美食、周边、徒步候选'],
            ['include_paid_providers', '付费来源', '默认关闭，需管理员主动启用'],
          ].map(([key, title, desc]) => (
            <label key={key} className={key === 'include_paid_providers' ? 'paid-provider' : ''}>
              <input type="checkbox" checked={Boolean(policy[key])} onChange={event => updatePolicy(key, event.target.checked)} />
              <span><strong>{title}</strong><small>{desc}</small></span>
            </label>
          ))}
        </div>
      </section>

      <section className="admin-status-strip web-enrichment-metrics">
        {metricDefs.map(([key, label, Icon]) => (
          <article key={key}>
            <span><Icon size={19} /></span>
            <div><strong>{valueOrDash(overview?.[key])}</strong><em>{label}</em></div>
          </article>
        ))}
      </section>

      <section className="web-review-layout">
        <main className="admin-panel web-candidate-panel">
          <div className="admin-card-title split">
            <div><Filter size={20} /><h2>候选池</h2></div>
            <button className="primary-btn" type="button" disabled={loading} onClick={() => runAction('approve')}><ShieldCheck size={16} /> 批量通过低风险</button>
          </div>
          <div className="admin-segmented web-candidate-tabs">
            {tabs.map(([key, label]) => <button key={key} className={activeTab === key ? 'active' : ''} type="button" onClick={() => setActiveTab(key)}>{label}</button>)}
          </div>
          <div className="web-candidate-list">
            {candidates.length ? candidates.map(item => (
              <article className="web-candidate-card" key={`${item.candidate_kind}-${item.id}`}>
                <div>
                  <span className={`status-badge ${item.risk_level === 'low' ? 'success' : item.risk_level === 'high' ? 'danger' : 'warning'}`}>{riskLabel(item.risk_level)}</span>
                  <strong>{item.scenic_name || item.title || `候选 #${item.id}`}</strong>
                  <p>{item.preview || '暂无预览内容'}</p>
                  <small>{[item.province, item.city, item.candidate_type, item.source_name].filter(Boolean).join(' · ')}</small>
                </div>
                <div className="web-candidate-actions">
                  {item.source_url ? <a className="ghost-btn" href={item.source_url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> 查看来源</a> : <button className="ghost-btn" disabled>无来源</button>}
                  {item.scenic_id ? <Link className="ghost-btn" to={`/scenic/${item.scenic_id}`}><MapPinned size={14} /> 进入景区</Link> : <button className="ghost-btn" disabled>无景区</button>}
                  <button className="ghost-btn" disabled title="单条审核将在候选详情中开放">单条审核暂不可用</button>
                </div>
              </article>
            )) : (
              <div className="admin-empty-result">暂无候选，或后台接口暂不可用。</div>
            )}
          </div>
        </main>

        <aside className="admin-panel web-job-timeline">
          <div className="admin-card-title">
            <Route size={20} />
            <h2>任务时间线</h2>
          </div>
          <div className="web-task-list">
            {recentTasks.length ? recentTasks.map(task => (
              <article key={`${task.name}-${task.id || task.last_run_at}`}>
                <span className={`status-badge ${task.status === 'running' ? 'success' : task.status === 'failed' ? 'danger' : 'warning'}`}>{task.status}</span>
                <strong>{task.name || task.source || '更新任务'}</strong>
                <p>读取 {task.payload?.read ?? '--'} · 搜索 {task.payload?.searched ?? '--'} · 候选 {(task.payload?.imageCandidates || 0) + (task.payload?.profileCandidates || 0)}</p>
                {task.payload?.providerFailures?.length ? <small><AlertTriangle size={13} /> {task.payload.providerFailures[0].message || '来源暂不可用'}</small> : <small>{task.last_run_at || '暂无运行时间'}</small>}
              </article>
            )) : (
              <div className="admin-empty-result">暂无任务记录。</div>
            )}
          </div>
        </aside>
      </section>
    </div>
  )
}
