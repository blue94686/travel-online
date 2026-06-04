import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Activity, AlertTriangle, Database, FileText, HardDrive, RefreshCw, Server, Shield, ShieldCheck, Users } from 'lucide-react'
import { createDataBackup, getServicesStatus, getDashboard, getAdminUsers, getAuditLogs, getDatabaseStatus, runQualityCheck } from '../../api/admin.js'
import AdminKpiCard from '../../components/admin/AdminKpiCard.jsx'
import DataTable from '../../components/common/DataTable.jsx'

export default function AdminSystemPage() {
  const location = useLocation()
  const [activeTab, setActiveTab] = useState('服务监控')
  const [services, setServices] = useState([])
  const [data, setData] = useState(null)
  const [users, setUsers] = useState([])
  const [logs, setLogs] = useState([])
  const [dbStatus, setDbStatus] = useState(null)
  const [maintenanceStatus, setMaintenanceStatus] = useState('')
  const [maintenanceBusy, setMaintenanceBusy] = useState('')
  const [serviceRefreshing, setServiceRefreshing] = useState(false)
  const [serviceRefreshStatus, setServiceRefreshStatus] = useState('')

  useEffect(() => {
    refreshServices()
    getDashboard().then(setData)
    getAdminUsers().then(data => setUsers(data || []))
    getAuditLogs().then(data => setLogs(data || []))
    getDatabaseStatus().then(setDbStatus)
  }, [])

  useEffect(() => {
    if (location.pathname.includes('/admin/users')) setActiveTab('用户管理')
    else if (location.pathname.includes('/admin/logs')) setActiveTab('操作日志')
    else if (location.pathname.includes('/admin/services')) setActiveTab('服务监控')
    else if (location.pathname.includes('/admin/roles')) setActiveTab('权限矩阵')
    else if (location.pathname.includes('/admin/security')) setActiveTab('安全策略')
    else if (location.pathname.includes('/admin/settings')) setActiveTab('系统配置')
  }, [location.pathname])

  const tabs = ['服务监控', '数据库连接与管理', '用户管理', '权限矩阵', '安全策略', '系统配置', '操作日志']
  const healthyServices = services.filter(s => (s.status || '正常') === '正常').length
  const dbSize = Number(dbStatus?.size || 0)
  const dbBackendLabel = dbStatus?.backend === 'postgresql' ? 'PostgreSQL' : 'SQLite'

  const refreshServices = async (showStatus = false) => {
    setServiceRefreshing(true)
    if (showStatus) setServiceRefreshStatus('服务状态刷新中...')
    try {
      const nextServices = await getServicesStatus()
      setServices(nextServices || [])
      if (showStatus) setServiceRefreshStatus(`服务状态已刷新：${nextServices?.length || 0} 个服务`)
    } catch (error) {
      if (showStatus) setServiceRefreshStatus(`刷新失败：${error.message || '请检查后端服务'}`)
    } finally {
      setServiceRefreshing(false)
    }
  }

  const runMaintenance = async (label, action) => {
    setMaintenanceBusy(label)
    setMaintenanceStatus(`${label}执行中...`)
    try {
      const result = await action()
      const summary = result?.file
        ? `备份文件：${result.file.split('/').pop()}`
        : result?.completeness
          ? `完整度 ${result.completeness}，图片匹配 ${result.imageMatch}，坐标覆盖 ${result.coordinateCoverage}`
          : '操作已完成'
      setMaintenanceStatus(`${label}完成，${summary}`)
      getAuditLogs().then(data => setLogs(data || []))
      getDatabaseStatus().then(setDbStatus)
    } catch (error) {
      setMaintenanceStatus(`${label}失败：${error.message || '请检查后端服务'}`)
    } finally {
      setMaintenanceBusy('')
    }
  }

  const serviceColumns = [
    { key: 'name', label: '服务名称', sortable: true, render: row => <strong>{row.name}</strong> },
    { key: 'status', label: '状态', render: row => <span className="status-badge success">{row.status || '正常'}</span> },
    { key: 'latency', label: '延迟', sortable: true },
    { key: 'today_requests', label: '今日请求', render: row => `${row.today_requests || 0} 次` },
  ]

  const userColumns = [
    { key: 'id', label: 'ID', sortable: true },
    { key: 'nickname', label: '昵称', sortable: true, render: row => <strong>{row.nickname}</strong> },
    { key: 'email', label: '邮箱' },
    { key: 'role', label: '角色', render: row => <span className={`status-badge ${row.role === 'admin' ? 'orange' : 'success'}`}>{row.role}</span> },
    { key: 'status', label: '状态', render: row => <span className={`status-badge ${row.status === 'active' ? 'success' : ''}`}>{row.status || 'active'}</span> },
  ]

  const logColumns = [
    { key: 'created_at', label: '时间', sortable: true },
    { key: 'operator', label: '操作人', sortable: true },
    { key: 'module', label: '模块' },
    { key: 'action', label: '动作', render: row => `${row.action}${row.result ? ` - ${row.result}` : ''}` },
    { key: 'ip', label: 'IP' },
  ]

  return (
    <div className="dashboard-page admin-backstage-page admin-system-console">
      <section className="admin-command-hero">
        <div>
          <span className="admin-eyebrow"><ShieldCheck size={15} /> 系统治理</span>
          <h1>系统与安全</h1>
          <p>权限审计、用户管理、微服务健康和数据库连接状态集中呈现。</p>
        </div>
        <div className="admin-command-actions">
          <span className="status-badge success">运行稳定</span>
          <button className="ghost-btn" onClick={() => refreshServices(true)} disabled={serviceRefreshing}>
            <RefreshCw size={16} /> {serviceRefreshing ? '刷新中...' : '刷新服务'}
          </button>
          {serviceRefreshStatus && <span className="admin-inline-note" role="status">{serviceRefreshStatus}</span>}
        </div>
      </section>

      <section className="kpi-grid admin-system-kpis">
        <AdminKpiCard label="在线服务" value={healthyServices} change={`共 ${services.length} 个`} icon={Activity} />
        <AdminKpiCard label="注册用户" value={users.length || data?.kpis?.[4]?.value || 0} change="全部用户" icon={Users} />
        <AdminKpiCard label="系统健康" value="正常" change="运行稳定" icon={ShieldCheck} />
      </section>

      <section className="admin-health-overview">
        <article className="admin-panel">
          <span><Server size={20} /></span>
          <div><strong>{healthyServices}/{services.length || 0}</strong><em>服务在线</em></div>
        </article>
        <article className="admin-panel">
          <span><Database size={20} /></span>
          <div><strong>{dbStatus?.status === 'normal' ? '已连接' : '检查中'}</strong><em>数据库连接</em></div>
        </article>
        <article className="admin-panel">
          <span><Shield size={20} /></span>
          <div><strong>{logs.length || data?.operationLogs?.length || 0}</strong><em>审计记录</em></div>
        </article>
        <article className="admin-panel warning">
          <span><AlertTriangle size={20} /></span>
          <div><strong>0</strong><em>高危告警</em></div>
        </article>
      </section>

      <div className="admin-system-tabs">
        {tabs.map(tab => (
          <button key={tab} className={activeTab === tab ? 'active' : ''} onClick={() => setActiveTab(tab)}>
            {tab === '服务监控' && <Activity size={18} />}
            {tab === '数据库连接与管理' && <Database size={18} />}
            {tab === '用户管理' && <Users size={18} />}
            {tab === '权限矩阵' && <ShieldCheck size={18} />}
            {tab === '安全策略' && <Shield size={18} />}
            {tab === '系统配置' && <Database size={18} />}
            {tab === '操作日志' && <FileText size={18} />}
            <span>{tab}</span>
          </button>
        ))}
      </div>

      {activeTab === '服务监控' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>微服务状态</h2></div>
          <DataTable columns={serviceColumns} rows={services} pageSize={20} />
        </section>
      )}

      {activeTab === '用户管理' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>用户列表</h2></div>
          <DataTable columns={userColumns} rows={users} pagination pageSize={10} />
        </section>
      )}

      {activeTab === '权限矩阵' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>权限矩阵</h2></div>
          <div className="permission-grid">
            <strong>角色</strong><strong>浏览</strong><strong>收藏</strong><strong>评论</strong><strong>上传</strong><strong>审核</strong><strong>景区管理</strong><strong>API</strong><strong>安全</strong><strong>系统</strong>
            {[
              ['guest', '✓', '-', '-', '-', '-', '-', '-', '-', '-'],
              ['user', '✓', '✓', '✓', '✓', '-', '-', '-', '-', '-'],
              ['admin', '✓', '✓', '✓', '✓', '✓', '✓', '查看', '-', '-'],
              ['superadmin', '✓', '✓', '✓', '✓', '✓', '✓', '管理', '✓', '✓'],
            ].map(row => row.map((cell, index) => <span key={`${row[0]}-${index}`}>{cell}</span>))}
          </div>
        </section>
      )}

      {activeTab === '安全策略' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>登录安全与黑名单</h2></div>
          <div className="admin-definition-list">
            <span><em>后台路由守卫</em><strong className="success">已启用</strong></span>
            <span><em>后端角色校验</em><strong className="success">敏感接口已接入 require_role</strong></span>
            <span><em>API Key 展示</em><strong className="success">脱敏显示</strong></span>
            <span><em>IP 黑名单</em><strong>通过评论审核页拉黑</strong></span>
          </div>
        </section>
      )}

      {activeTab === '系统配置' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>系统配置</h2></div>
          <div className="admin-definition-list">
            <span><em>站点名称</em><strong>景区在线 Scenic Online</strong></span>
            <span><em>默认城市</em><strong>杭州</strong></span>
            <span><em>图片策略</em><strong>审核后展示</strong></span>
            <span><em>资料补全</em><strong>候选审核机制</strong></span>
          </div>
        </section>
      )}

      {activeTab === '操作日志' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>系统操作日志</h2></div>
          <DataTable columns={logColumns} rows={logs.length ? logs : (data?.operationLogs || [])} pagination pageSize={15} />
        </section>
      )}

      {activeTab === '数据库连接与管理' && (
        <section className="admin-panel">
          <div className="card-title-row">
            <h2>数据库连接配置</h2>
            <span className={`status-badge ${dbStatus?.status === 'normal' ? 'success' : 'warning'}`}>
              {dbStatus?.status === 'normal' ? '已连接' : '检查中'}
            </span>
          </div>
          
          <div className="admin-db-detail-grid">
            <div className="admin-panel">
              <div className="admin-card-title">
                <HardDrive size={20} />
                <h3>存储详情</h3>
              </div>
              <div className="admin-definition-list">
                <span><em>数据库类型</em><strong>{dbBackendLabel}</strong></span>
                <span><em>{dbStatus?.backend === 'postgresql' ? '连接地址' : '文件路径'}</em><code>{dbStatus?.path || './data/scenic_online.sqlite3'}</code></span>
                <span><em>{dbStatus?.backend === 'postgresql' ? '存储状态' : '文件大小'}</em><strong>{dbStatus?.backend === 'postgresql' ? '容器托管' : `${(dbSize / 1024 / 1024).toFixed(2)} MB`}</strong></span>
                <span><em>日志模式</em><strong>{dbStatus?.journalMode || dbStatus?.backend || 'WAL'}</strong></span>
              </div>
            </div>

            <div className="admin-panel">
              <div className="admin-card-title">
                <Database size={20} />
                <h3>统计概览</h3>
              </div>
              <div className="admin-definition-list">
                <span><em>数据表数量</em><strong>{dbStatus?.tables?.length || 0} 个</strong></span>
                <span><em>索引数量</em><strong>{dbStatus?.indexes?.length || 0} 个</strong></span>
                <span><em>正式景区</em><strong>{dbStatus?.scenicCount?.toLocaleString() || 0} 条</strong></span>
                <span><em>全国源表</em><strong>{dbStatus?.sourceScenicCount?.toLocaleString() || 0} 条</strong></span>
                <span><em>景区记录合计</em><strong>{dbStatus?.totalScenicCount?.toLocaleString() || dbStatus?.scenicCount?.toLocaleString() || 0} 条</strong></span>
                <span><em>审计日志数</em><strong>{dbStatus?.auditCount?.toLocaleString() || 0} 条</strong></span>
              </div>
            </div>
          </div>

          <div className="admin-maintenance-card">
            <div className="form-group">
              <label>数据库引擎切换 (实验性)</label>
              <select className="form-input" style={{ width: '100%' }}>
                <option>{dbBackendLabel} (当前环境)</option>
                <option disabled>SQLite (本地兼容模式，需要配置环境变量)</option>
                <option disabled>MySQL / MariaDB (需要配置环境变量)</option>
              </select>
            </div>
            
            <div>
              <button className="primary-btn" onClick={() => getDatabaseStatus().then(setDbStatus)} disabled={!!maintenanceBusy}>刷新状态</button>
              <button className="primary-btn" onClick={() => runMaintenance('完整性检查', runQualityCheck)} disabled={!!maintenanceBusy}>
                {maintenanceBusy === '完整性检查' ? '检查中...' : '完整性检查'}
              </button>
              <button className="ghost-btn" onClick={() => runMaintenance('导出数据备份', createDataBackup)} disabled={!!maintenanceBusy}>
                {maintenanceBusy === '导出数据备份' ? '备份中...' : '导出数据备份'}
              </button>
            </div>
            {maintenanceStatus && <p className="admin-inline-note">{maintenanceStatus}</p>}
          </div>
        </section>
      )}
    </div>
  )
}
