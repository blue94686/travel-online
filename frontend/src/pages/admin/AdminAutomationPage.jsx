import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Bot, CheckCircle2, Database, RefreshCw, Server, ShieldCheck, Trash2, Zap } from 'lucide-react'
import { triggerDataSync, createDataBackup, runQualityCheck } from '../../api/admin.js'

export default function AdminAutomationPage() {
  const [tasks, setTasks] = useState([
    { id: 'sync', name: '全国景区数据同步', desc: '从云端同步最新的景区、天气及实况数据', lastRun: '2小时前', status: 'success', icon: RefreshCw },
    { id: 'backup', name: '系统全量备份', desc: '备份数据库、配置文件及用户上传资源', lastRun: '1天前', status: 'success', icon: Database },
    { id: 'quality', name: '数据质量巡检', desc: '检查景区资料完整度、图片有效性及坐标精度', lastRun: '3小时前', status: 'warning', icon: CheckCircle2 },
    { id: 'cleanup', name: '冗余资源清理', desc: '自动清理未引用的临时文件及过期缓存', lastRun: '12小时前', status: 'success', icon: Trash2 },
  ])
  const [running, setRunning] = useState(null)
  const [notice, setNotice] = useState('')
  const mergedEntries = [
    { label: '同步任务', desc: '景区、天气、主题数据批量更新', icon: RefreshCw, to: '/admin/automation' },
    { label: 'AI 管理', desc: '路线生成、内容增强、知识库同步', icon: Bot, to: '/admin/automation' },
    { label: 'API 接入', desc: '地图、天气、外部服务密钥配置', icon: Zap, to: '/admin/integration' },
    { label: '服务巡检', desc: '微服务状态、延迟与调用日志', icon: Server, to: '/admin/services' },
  ]

  const runTask = async (taskId) => {
    setRunning(taskId)
    try {
      if (taskId === 'sync') await triggerDataSync()
      if (taskId === 'backup') await createDataBackup()
      if (taskId === 'quality') await runQualityCheck()
      
      setNotice(`任务 ${taskId} 执行成功`)
      setTimeout(() => setNotice(''), 3000)
    } catch (err) {
      setNotice(`任务 ${taskId} 执行失败`)
    } finally {
      setRunning(null)
    }
  }

  return (
    <div className="dashboard-page admin-backstage-page admin-automation-console">
      {notice && <div className="notice">{notice}</div>}
      
      <section className="admin-command-hero">
        <div>
          <span className="admin-eyebrow"><Bot size={15} /> 自动化与服务</span>
          <h1>自动化与服务</h1>
          <p>合并 AI 管理、订单票务、API 服务、同步任务和系统维护流。</p>
        </div>
        <div className="admin-command-actions">
          <span className="status-badge success"><ShieldCheck size={14} /> 服务正常</span>
        </div>
      </section>

      <section className="admin-merged-entry-grid">
        {mergedEntries.map(entry => {
          const Icon = entry.icon
          return (
            <Link to={entry.to} key={entry.label}>
              <span><Icon size={20} /></span>
              <div><strong>{entry.label}</strong><em>{entry.desc}</em></div>
            </Link>
          )
        })}
      </section>

      <div className="content-grid two">
        <section className="admin-panel">
          <div className="card-title-row"><h2>任务工作流</h2></div>
          <div style={{ display: 'grid', gap: 16 }}>
            {tasks.map(task => (
              <div key={task.id} className="panel" style={{ padding: 20, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
                  <div style={{ padding: 12, background: 'var(--color-bg)', borderRadius: 12, color: 'var(--color-primary)' }}>
                    <task.icon size={24} />
                  </div>
                  <div>
                    <strong style={{ display: 'block', fontSize: 16 }}>{task.name}</strong>
                    <span style={{ fontSize: 13, color: 'var(--color-muted)' }}>{task.desc}</span>
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ marginBottom: 8 }}>
                    <span style={{ fontSize: 12, color: 'var(--color-muted)', marginRight: 12 }}>上次运行: {task.lastRun}</span>
                    <span className={`status-badge ${task.status === 'success' ? 'success' : 'warning'}`}>
                      {task.status === 'success' ? '就绪' : '待检查'}
                    </span>
                  </div>
                  <button 
                    className="primary-btn" 
                    style={{ padding: '6px 16px', fontSize: 13 }}
                    onClick={() => runTask(task.id)}
                    disabled={running === task.id}
                  >
                    {running === task.id ? '执行中...' : '立即执行'}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="admin-panel">
          <div className="card-title-row"><h2>自动化配置</h2></div>
          <div className="panel" style={{ padding: 20 }}>
            <div className="form-group" style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', marginBottom: 8 }}>全局同步周期</label>
              <select className="form-input" style={{ width: '100%' }}>
                <option>每 6 小时</option>
                <option>每天凌晨 2:00</option>
                <option>每周日凌晨 4:00</option>
                <option>仅手动触发</option>
              </select>
            </div>
            <div className="form-group" style={{ marginBottom: 20 }}>
              <label style={{ display: 'block', marginBottom: 8 }}>备份保留策略</label>
              <select className="form-input" style={{ width: '100%' }}>
                <option>保留最近 7 天</option>
                <option>保留最近 30 天</option>
                <option>永久保留 (注意磁盘空间)</option>
              </select>
            </div>
            <div className="admin-toggle-list">
              <label>
                <span>失败后自动重试</span>
                <input type="checkbox" defaultChecked />
                <i />
              </label>
              <label>
                <span>完成后发送邮件通知</span>
                <input type="checkbox" />
                <i />
              </label>
            </div>
            <button className="primary-btn" style={{ width: '100%', marginTop: 24 }}>保存自动化设置</button>
          </div>
        </section>
      </div>
    </div>
  )
}
