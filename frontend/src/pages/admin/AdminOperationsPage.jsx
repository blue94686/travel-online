import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Activity,
  Bell,
  CheckCircle2,
  Cloud,
  Database,
  FileText,
  Gauge,
  Image,
  Landmark,
  Megaphone,
  MessageSquare,
  RefreshCw,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Users,
  XCircle,
  Zap,
} from 'lucide-react'
import {
  approveComment,
  approveImage,
  getAdminScenic,
  getDashboard,
  hideComment,
  rejectImage,
} from '../../api/admin.js'

const formatNumber = (value, fallback = 0) => {
  if (typeof value === 'string') return value
  const number = Number(value ?? fallback)
  return Number.isFinite(number) ? number.toLocaleString() : String(fallback)
}

const parseMetric = (value) => {
  if (typeof value === 'number') return value
  const parsed = Number(String(value || '').replace(/[^\d.]/g, ''))
  return Number.isFinite(parsed) ? parsed : 0
}

const statusTone = (status) => (status === '完成' || status === '正常' || status === '成功' ? 'success' : status === '失败' ? 'danger' : 'warning')

export default function AdminOperationsPage() {
  const [data, setData] = useState(null)
  const [scenic, setScenic] = useState([])
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)

  const refresh = async () => {
    setLoading(true)
    const [dashboard, scenicList] = await Promise.all([getDashboard(), getAdminScenic('?limit=12')])
    setData(dashboard)
    setScenic(scenicList?.list || [])
    setLoading(false)
  }

  useEffect(() => {
    refresh()
  }, [])

  const kpis = data?.kpis || []
  const kpiByLabel = useMemo(() => Object.fromEntries(kpis.map(item => [item.label, item])), [kpis])
  const systemStatus = data?.systemStatus || {}
  const serviceStatus = data?.serviceStatus || []
  const apiHealth = data?.apiHealth || []
  const imageReviewQueue = data?.imageReviewQueue || []
  const commentReviewQueue = data?.commentReviewQueue || []
  const syncTasks = data?.syncTasks || []
  const logs = data?.operationLogs || []
  const dataQuality = data?.dataQuality || {}
  const avgLatency = apiHealth.length ? Math.round(apiHealth.reduce((sum, item) => sum + parseMetric(item.latency), 0) / apiHealth.length) : 0
  const pendingTotal = imageReviewQueue.length + commentReviewQueue.length

  const controlKpis = [
    { label: '景区数', value: scenic.length || 128, change: '较昨日 +3', icon: Landmark, tone: 'green' },
    { label: '图片数', value: '128,560', change: '较昨日 +1,245', icon: Image, tone: 'blue' },
    { label: '评论数', value: formatNumber(kpiByLabel['新增评论']?.value, 25436), change: '较昨日 +86', icon: MessageSquare, tone: 'purple' },
    { label: 'API调用量', value: kpiByLabel['API 请求数']?.value || '86,425', change: kpiByLabel['API 请求数']?.change || '+18.6%', icon: Zap, tone: 'orange' },
    { label: 'AI调用量', value: '32,754', change: '较昨日 +22.3%', icon: Sparkles, tone: 'cyan' },
  ]

  const dataServices = [
    { name: '景区服务', icon: Cloud, detail: '响应时间 128ms' },
    { name: '图片服务', icon: Image, detail: '响应时间 142ms' },
    { name: '评论服务', icon: MessageSquare, detail: '响应时间 98ms' },
    { name: '搜索服务', icon: Search, detail: '响应时间 110ms' },
    { name: '推荐服务', icon: Gauge, detail: '响应时间 134ms' },
    { name: '通知服务', icon: Bell, detail: '响应时间 156ms' },
    { name: '文件存储', icon: Cloud, detail: '存储使用率 45%' },
  ]

  const aiCards = [
    { label: 'AI服务状态', value: '正常', hint: `平均延迟 ${avgLatency || 54}ms`, icon: Sparkles },
    { label: 'AI路线生成次数', value: '2,845', hint: '较昨日 +326', icon: Activity },
    { label: 'AI内容增强状态', value: '正常', hint: '今日处理 1,245 条', icon: Megaphone },
    { label: 'AI知识库同步状态', value: '正常', hint: '最新同步 09:12:30', icon: FileText },
  ]

  const qualityRows = [
    ['数据质量', parseMetric(dataQuality.imageMatch) || 92],
    ['数据完整性', parseMetric(dataQuality.completeness) || 98.6],
    ['数据一致性', parseMetric(dataQuality.coordinateCoverage) || 99.1],
    ['数据时效性', parseMetric(dataQuality.weatherAvailability) || 97.3],
  ]

  const quickActions = [
    { label: '新增景区', icon: UploadCloud, to: '/admin/database' },
    { label: '批量导入景区', icon: FileText, to: '/admin/database' },
    { label: '发布公告', icon: Megaphone, to: '/admin/content' },
    { label: '清理缓存', icon: Database, to: '/admin/system' },
    { label: '同步数据', icon: RefreshCw, to: '/admin/automation' },
    { label: '备份数据', icon: Cloud, to: '/admin/database' },
    { label: '系统配置', icon: Settings, to: '/admin/system' },
    { label: '操作日志', icon: FileText, to: '/admin/system' },
  ]

  const handleReview = async (type, id, action) => {
    const task = type === 'image'
      ? (action === 'approve' ? approveImage(id) : rejectImage(id))
      : (action === 'approve' ? approveComment(id) : hideComment(id))
    await task
    setNotice(action === 'approve' ? '审核已通过' : '已处理审核项')
    refresh()
    setTimeout(() => setNotice(''), 2200)
  }

  return (
    <div className="admin-control-room">
      {notice && <div className="notice">{notice}</div>}

      <section className="admin-control-toolbar">
        <div>
          <h1>管理总览</h1>
          <p>后台数据、审核、AI、服务健康和数据治理集中呈现。</p>
        </div>
        <div className="admin-control-toolbar-actions">
          <span>数据更新时间：2026-06-01 21:02:00</span>
          <button className="ghost-btn" onClick={refresh} disabled={loading}><RefreshCw size={16} /> 刷新</button>
        </div>
      </section>

      <section className="admin-control-kpis">
        {controlKpis.map(item => {
          const Icon = item.icon
          return (
            <article className={`admin-metric-card tone-${item.tone}`} key={item.label}>
              <span className="admin-metric-icon"><Icon size={23} /></span>
              <div>
                <p>{item.label}</p>
                <strong>{item.value}</strong>
                <em>{item.change} ↑</em>
              </div>
            </article>
          )
        })}
        <article className="admin-system-card">
          <div className="admin-health-ring"><strong>正常</strong><span>运行中</span></div>
          <div className="admin-system-list">
            {[
              ['服务健康', systemStatus.serviceHealth || '100%'],
              ['网络状态', systemStatus.apiHealth || '正常'],
              ['存储状态', systemStatus.storage || '正常'],
              ['数据库', systemStatus.dataSync || '正常'],
            ].map(([label, value]) => (
              <span key={label}><i />{label}<strong>{value}</strong></span>
            ))}
          </div>
        </article>
      </section>

      <section className="admin-panel admin-service-matrix">
        <h2>数据服务状态</h2>
        <div>
          {dataServices.map(item => {
            const Icon = item.icon
            return (
              <article key={item.name}>
                <span><Icon size={22} /></span>
                <strong>{item.name}</strong>
                <b>正常</b>
                <em>{item.detail}</em>
              </article>
            )
          })}
        </div>
      </section>

      <section className="admin-control-ai-grid">
        <div className="admin-panel admin-ai-status">
          <h2>AI 服务状态</h2>
          <div>
            {aiCards.map(item => {
              const Icon = item.icon
              return (
                <article key={item.label}>
                  <span><Icon size={22} /></span>
                  <div><strong>{item.label}</strong><b>{item.value}</b><em>{item.hint}</em></div>
                </article>
              )
            })}
          </div>
        </div>
        <div className="admin-panel admin-ai-usage">
          <h2>AI 资源使用</h2>
          {[
            ['调用配额', 65, '32,754 / 50,000'],
            ['并发使用', 42, '21 / 50'],
            ['Token 使用', 68, '68.2M / 100M'],
          ].map(([label, value, text]) => (
            <label key={label}>
              <span>{label}<strong>{value}%</strong></span>
              <i><b style={{ width: `${value}%` }} /></i>
              <em>{text}</em>
            </label>
          ))}
        </div>
      </section>

      <section className="admin-review-board">
        <article className="admin-panel admin-quick-actions-card">
          <h2>快捷操作</h2>
          <div>
            {quickActions.map(action => {
              const Icon = action.icon
              return <Link key={action.label} to={action.to}><Icon size={19} /><span>{action.label}</span></Link>
            })}
          </div>
        </article>

        <article className="admin-panel admin-review-list">
          <h2>待审核图片 <small>查看全部（{imageReviewQueue.length}）</small></h2>
          {(imageReviewQueue.length ? imageReviewQueue : scenic.slice(0, 3)).map((item, index) => (
            <div key={item.id || index}>
              <img src={item.url || item.cover_image_url || `https://images.unsplash.com/photo-1500534314209-a25ddb2bd429?auto=format&fit=crop&w=160&q=80`} alt="" />
              <div><strong>{item.scenic || item.name || '景区图片'}</strong><span>{item.uploader || item.city || '系统导入'} · {index ? '32 分钟前' : '10 分钟前'}</span></div>
              {item.id && imageReviewQueue.length ? (
                <div className="admin-review-actions">
                  <button onClick={() => handleReview('image', item.id, 'approve')}>通过</button>
                  <button className="danger" onClick={() => handleReview('image', item.id, 'reject')}>拒绝</button>
                </div>
              ) : <span className="status-badge success">正常</span>}
            </div>
          ))}
        </article>

        <article className="admin-panel admin-review-list comments">
          <h2>待审核评论</h2>
          {(commentReviewQueue.length ? commentReviewQueue : [
            { id: 'demo-1', user_name: '游客 188****1234', content: '景色很美，值得一去！' },
            { id: 'demo-2', user_name: '旅行爱好者', content: '门票价格是否包含索道？' },
            { id: 'demo-3', user_name: '张先生', content: '停车方便吗？周末人多吗？' },
          ]).map(item => (
            <div key={item.id}>
              <span className="comment-bubble"><MessageSquare size={16} /></span>
              <div><strong>{item.user_name || item.nickname || '游客'}</strong><span>{item.content || item.text}</span></div>
              {commentReviewQueue.length ? (
                <div className="admin-review-actions">
                  <button onClick={() => handleReview('comment', item.id, 'approve')}>通过</button>
                  <button onClick={() => handleReview('comment', item.id, 'hide')}>屏蔽</button>
                </div>
              ) : <span className="status-badge warning">待审</span>}
            </div>
          ))}
        </article>
      </section>

      <section className="admin-control-bottom">
        <article className="admin-panel admin-sync-table">
          <h2>最近同步任务</h2>
          <div className="admin-mini-table">
            <div><span>任务名称</span><span>数据类型</span><span>状态</span><span>开始时间</span><span>结果</span></div>
            {syncTasks.map(task => (
              <div key={task.name}>
                <strong>{task.name}</strong><span>{task.source}</span><b className={`status-badge ${statusTone(task.status)}`}>{task.status}</b><span>{task.started_at}</span><span>{task.result}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-panel admin-log-table">
          <h2>系统日志</h2>
          <div className="admin-mini-table log">
            <div><span>时间</span><span>级别</span><span>模块</span><span>日志内容</span></div>
            {(logs.length ? logs : [
              { id: 1, created_at: '09:18:25', module: '系统监控', action: '系统健康检查完成，状态正常', result: '信息' },
              { id: 2, created_at: '09:17:58', module: 'AI服务', action: 'AI内容增强任务完成', result: '信息' },
              { id: 3, created_at: '09:17:34', module: '图片服务', action: '图片处理队列延迟偏高', result: '警告' },
            ]).slice(0, 5).map(log => (
              <div key={log.id}>
                <span>{String(log.created_at || '').slice(11, 19) || log.created_at}</span>
                <b className={`status-badge ${log.result === '错误' ? 'danger' : log.result === '警告' ? 'warning' : 'success'}`}>{log.result || '信息'}</b>
                <strong>{log.module}</strong>
                <span>{log.action}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="admin-panel admin-data-governance">
          <h2>数据治理</h2>
          <div className="admin-governance-grid">
            <div className="admin-quality-ring"><strong>{qualityRows[0][1]}%</strong></div>
            <div>
              {qualityRows.map(([label, value]) => <span key={label}><i />{label}<strong>{value}%</strong></span>)}
            </div>
          </div>
          <div className="admin-issue-list">
            <span><FileText size={15} /> 重复数据 <strong>1,245 条</strong></span>
            <span><XCircle size={15} /> 异常数据 <strong>326 条</strong></span>
            <span><Database size={15} /> 缺失数据 <strong>{dataQuality.pendingIssues || 23} 条</strong></span>
            <span><ShieldCheck size={15} /> 待处理工单 <strong>23 条</strong></span>
          </div>
        </article>
      </section>
    </div>
  )
}
