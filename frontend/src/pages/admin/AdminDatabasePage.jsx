import { useEffect, useMemo, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  Columns3,
  Database,
  Download,
  Eye,
  FileSearch,
  Files,
  HardDrive,
  Play,
  RefreshCw,
  Search,
  ShieldCheck,
  Table,
  Terminal,
} from 'lucide-react'
import { executeSql, getDatabaseFiles, getDatabaseOverview, getDatabaseStatus, getDatabaseTable } from '../../api/admin.js'

const formatBytes = value => {
  const size = Number(value || 0)
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(2)} MB`
}

const stringifyCell = value => {
  if (value === null || value === undefined || value === '') return '-'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

export default function AdminDatabasePage() {
  const [dbStatus, setDbStatus] = useState(null)
  const [overview, setOverview] = useState(null)
  const [files, setFiles] = useState([])
  const [tableDetail, setTableDetail] = useState(null)
  const [activeTable, setActiveTable] = useState('')
  const [mode, setMode] = useState('browse')
  const [sql, setSql] = useState('SELECT id, name, province, city, level FROM scenic_spots LIMIT 20;')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('')

  useEffect(() => {
    refreshAll()
  }, [])

  const refreshAll = async () => {
    setError('')
    const [status, nextOverview, nextFiles] = await Promise.all([
      getDatabaseStatus(),
      getDatabaseOverview(),
      getDatabaseFiles(),
    ])
    setDbStatus(status)
    setOverview(nextOverview)
    setFiles(nextFiles || nextOverview?.files || [])
    const defaultTable = activeTable || nextOverview?.tables?.find(item => item.name === 'scenic_spots')?.name || nextOverview?.tables?.[0]?.name
    if (defaultTable) loadTable(defaultTable)
  }

  const loadTable = async name => {
    setLoading(true)
    setError('')
    setActiveTable(name)
    const detail = await getDatabaseTable(name, '?limit=80&offset=0')
    if (!detail) {
      setError('数据表读取失败，请确认后端服务正在运行。')
    }
    setTableDetail(detail)
    setLoading(false)
  }

  const runSql = async () => {
    if (!sql.trim()) return
    setLoading(true)
    setError('')
    const res = await executeSql(sql)
    if (res) {
      setResult(res)
      setMode('sql')
    } else {
      setError('SQL 执行失败，请检查语句或后端服务状态。')
      setResult(null)
    }
    setLoading(false)
  }

  const exportJson = (name, payload) => {
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${name}.json`
    link.click()
    URL.revokeObjectURL(url)
  }

  const tables = overview?.tables || dbStatus?.tables || []
  const dbSize = Number(overview?.size || dbStatus?.size || 0)
  const filteredTables = useMemo(() => {
    const keyword = filter.trim().toLowerCase()
    if (!keyword) return tables
    return tables.filter(table => table.name.toLowerCase().includes(keyword))
  }, [filter, tables])
  const visibleColumns = tableDetail?.columns?.map(column => column.name) || []
  const previewColumns = visibleColumns.slice(0, 10)
  const quickQueries = [
    ['景区数据', 'SELECT id, name, province, city, level FROM scenic_spots LIMIT 20;'],
    ['主题旅行', 'SELECT id, name, season, audience FROM scenic_themes LIMIT 20;'],
    ['地区索引', 'SELECT province, city, district FROM regions LIMIT 30;'],
    ['最近日志', 'SELECT id, module, action, result, created_at FROM audit_logs ORDER BY id DESC LIMIT 30;'],
  ]

  return (
    <div className="dashboard-page admin-backstage-page admin-database-console">
      <section className="admin-command-hero">
        <div>
          <span className="admin-eyebrow"><Database size={15} /> 数据中枢</span>
          <h1>数据库与文件浏览</h1>
          <p>不用命令行即可查看数据库表、字段、样例数据、SQLite 文件和本地 SQL 数据源。</p>
        </div>
        <div className="admin-command-actions">
          <span className={`status-badge ${overview?.status === 'normal' || dbStatus?.status === 'normal' ? 'success' : 'warning'}`}>
            <ShieldCheck size={14} /> {overview?.integrity || dbStatus?.integrity || '检测中'}
          </span>
          <button className="ghost-btn" onClick={refreshAll}><RefreshCw size={16} /> 刷新</button>
        </div>
      </section>

      <section className="admin-status-strip">
        <article>
          <span><Table size={19} /></span>
          <div><strong>{tables.length}</strong><em>数据表</em></div>
        </article>
        <article>
          <span><HardDrive size={19} /></span>
          <div><strong>{formatBytes(dbSize)}</strong><em>数据库大小</em></div>
        </article>
        <article>
          <span><Activity size={19} /></span>
          <div><strong>{overview?.journalMode || dbStatus?.journalMode || 'WAL'}</strong><em>日志模式</em></div>
        </article>
        <article>
          <span><Files size={19} /></span>
          <div><strong>{files.filter(file => file.exists).length}</strong><em>可见文件</em></div>
        </article>
      </section>

      <div className="admin-console-layout">
        <aside className="admin-table-sidebar">
          <section className="admin-panel">
            <div className="admin-card-title">
              <Table size={18} />
              <h3>数据表</h3>
            </div>
            <label className="admin-db-search">
              <Search size={15} />
              <input value={filter} onChange={event => setFilter(event.target.value)} placeholder="搜索表名" />
            </label>
            <div className="admin-table-nav">
              {filteredTables.map(table => (
                <button
                  key={table.name}
                  className={activeTable === table.name ? 'active' : ''}
                  onClick={() => {
                    setMode('browse')
                    loadTable(table.name)
                  }}
                >
                  <span>{table.name}</span>
                  <small>{table.rowsLabel || table.rows || table.count || '-'}</small>
                </button>
              ))}
            </div>
          </section>

          <section className="admin-panel admin-engine-card">
            <div className="admin-card-title">
              <FileSearch size={18} />
              <h3>文件查看</h3>
            </div>
            <div className="admin-file-list">
              {files.map(file => (
                <article key={`${file.kind}-${file.path}`} className={file.exists ? '' : 'muted'}>
                  <div>
                    <strong>{file.label}</strong>
                    <span>{file.kind} · {file.exists ? formatBytes(file.size) : '未检测到'}</span>
                  </div>
                  <code>{file.path}</code>
                </article>
              ))}
            </div>
          </section>
        </aside>

        <main className="admin-sql-workspace">
          <section className="admin-panel admin-db-browser-card">
            <div className="admin-card-title split">
              <div>
                <Eye size={20} />
                <h2>可视化浏览</h2>
              </div>
              <div className="admin-segmented">
                <button className={mode === 'browse' ? 'active' : ''} onClick={() => setMode('browse')}>表浏览</button>
                <button className={mode === 'sql' ? 'active' : ''} onClick={() => setMode('sql')}>SQL 终端</button>
              </div>
            </div>

            {mode === 'browse' && (
              <>
                {tableDetail ? (
                  <div className="admin-db-table-detail">
                    <div className="admin-db-detail-head">
                      <div>
                        <span>当前数据表</span>
                        <h3>{tableDetail.name}</h3>
                        <p>{tableDetail.totalLabel || tableDetail.total} 行 · {tableDetail.columns.length} 个字段 · {tableDetail.indexes.length} 个索引</p>
                      </div>
                      <button className="ghost-btn" onClick={() => exportJson(`${tableDetail.name}-preview`, tableDetail)}>
                        <Download size={14} /> 导出当前视图
                      </button>
                    </div>

                    <div className="admin-schema-grid">
                      {tableDetail.columns.map(column => (
                        <article key={column.name}>
                          <Columns3 size={16} />
                          <div>
                            <strong>{column.name}</strong>
                            <span>{column.type || 'TEXT'}{column.pk ? ' · 主键' : ''}{column.notnull ? ' · 必填' : ''}</span>
                          </div>
                        </article>
                      ))}
                    </div>

                    <div className="admin-result-table-wrap">
                      <table className="admin-result-table">
                        <thead>
                          <tr>
                            {previewColumns.map(column => <th key={column}>{column}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {tableDetail.rows.map((row, index) => (
                            <tr key={index}>
                              {previewColumns.map(column => <td key={column}>{stringifyCell(row[column])}</td>)}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                ) : (
                  <div className="admin-empty-result">{loading ? '正在读取数据表...' : '请选择左侧数据表'}</div>
                )}
              </>
            )}

            {mode === 'sql' && (
              <div className="admin-sql-inline">
                <div className="admin-query-chips">
                  {quickQueries.map(([label, query]) => (
                    <button key={label} type="button" onClick={() => setSql(query)}>{label}</button>
                  ))}
                </div>
                <textarea
                  className="admin-code-editor"
                  value={sql}
                  onChange={event => setSql(event.target.value)}
                  onKeyDown={event => event.ctrlKey && event.key === 'Enter' && runSql()}
                  placeholder="请输入 SQL 语句..."
                />
                <div className="admin-command-actions">
                  <button className="ghost-btn" onClick={() => setSql('')}>清空</button>
                  <button className="primary-btn" onClick={runSql} disabled={loading}>
                    <Play size={14} /> {loading ? '执行中...' : '运行查询'}
                  </button>
                </div>
              </div>
            )}
          </section>

          {error && (
            <div className="admin-alert danger">
              <AlertTriangle size={20} />
              <div><strong>操作失败</strong><p>{error}</p></div>
            </div>
          )}

          {mode === 'sql' && result && (
            <section className="admin-panel admin-result-card">
              <div className="admin-result-head">
                <div>
                  <CheckCircle2 size={18} />
                  <strong>查询结果</strong>
                  {result.rows && <span>({result.rows.length} 行)</span>}
                  {result.affected_rows !== undefined && <span>(影响 {result.affected_rows} 行)</span>}
                </div>
                <button className="ghost-btn" onClick={() => exportJson('sql-result', result)}><Download size={14} /> 导出 JSON</button>
              </div>

              <div className="admin-result-table-wrap">
                {result.type === 'select' ? (
                  <table className="admin-result-table">
                    <thead>
                      <tr>
                        {result.columns.map(column => <th key={column}>{column}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {result.rows.map((row, index) => (
                        <tr key={index}>
                          {result.columns.map(column => <td key={column}>{stringifyCell(row[column])}</td>)}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="admin-empty-result">
                    语句执行成功。影响行数：{result.affected_rows}
                  </div>
                )}
              </div>
            </section>
          )}
        </main>
      </div>
    </div>
  )
}
