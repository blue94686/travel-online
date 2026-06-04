import { useEffect, useMemo, useState } from 'react'
import { CheckCircle2, ExternalLink, Globe2, Plus, RefreshCw, ShieldAlert, Trash2 } from 'lucide-react'
import {
  approveAdminEarthSource,
  bulkCheckAdminEarthSources,
  checkAdminEarthSource,
  createAdminEarthSource,
  deleteAdminEarthSource,
  disableAdminEarthSource,
  getAdminEarthSources,
  rejectAdminEarthSource,
} from '../../api/admin.js'
import DataTable from '../../components/common/DataTable.jsx'

const emptyForm = {
  name: '',
  slug: '',
  category: 'weather_earth',
  country: '中国',
  province: '',
  city: '',
  source_platform: '公开网站',
  source_url: '',
  embed_url: '',
  thumbnail_url: '',
  description: '',
  authorization_note: '公开来源，需人工审核授权边界',
  license_note: '待审核',
  review_status: 'candidate',
  availability_status: 'unknown',
  risk_level: 'low',
  is_live: false,
  is_embeddable: false,
}

export default function AdminEarthOnlinePage() {
  const [sources, setSources] = useState([])
  const [notice, setNotice] = useState('')
  const [editing, setEditing] = useState(null)
  const [busy, setBusy] = useState('')

  const refresh = () => getAdminEarthSources().then(data => setSources(data || []))

  useEffect(() => { refresh() }, [])

  const stats = useMemo(() => ({
    total: sources.length,
    approved: sources.filter(item => item.review_status === 'approved').length,
    safe: sources.filter(item => item.review_status === 'approved' && item.risk_level === 'low').length,
    pending: sources.filter(item => ['candidate', 'pending'].includes(item.review_status)).length,
  }), [sources])

  const run = async (label, action) => {
    setBusy(label)
    const result = await action()
    setNotice(result?.message || `${label}完成`)
    await refresh()
    setBusy('')
  }

  const submit = async event => {
    event.preventDefault()
    const payload = {
      ...emptyForm,
      ...editing,
      slug: editing.slug || editing.name.trim().toLowerCase().replace(/\s+/g, '-'),
      linked_scenic_id: editing.linked_scenic_id || null,
    }
    await createAdminEarthSource(payload)
    setEditing(null)
    setNotice('来源已加入候选池')
    refresh()
  }

  const columns = [
    { key: 'name', label: '来源', render: row => <div><strong>{row.name}</strong><br /><small>{row.category} · {row.source_platform}</small></div> },
    { key: 'review_status', label: '审核', render: row => <span className={`status-badge ${row.review_status === 'approved' ? 'success' : 'warning'}`}>{row.review_status}</span> },
    { key: 'availability_status', label: '可用性', render: row => <span className={`status-badge ${row.availability_status === 'online' ? 'success' : 'warning'}`}>{row.availability_status}</span> },
    { key: 'risk_level', label: '风险', render: row => <span className={`status-badge ${row.risk_level === 'low' ? 'success' : 'warning'}`}>{row.risk_level}</span> },
    { key: 'actions', label: '操作', render: row => (
      <div className="admin-inline-actions">
        <button className="ghost-btn" onClick={() => run('检测来源', () => checkAdminEarthSource(row.id))} disabled={busy}>检测</button>
        <button className="primary-btn" onClick={() => run('审核通过', () => approveAdminEarthSource(row.id))} disabled={busy || row.risk_level !== 'low'} title={row.risk_level !== 'low' ? '只有 low risk 来源可进入前台' : '审核通过'}>通过</button>
        <button className="ghost-btn" onClick={() => run('驳回来源', () => rejectAdminEarthSource(row.id))} disabled={busy}>驳回</button>
        <button className="ghost-btn" onClick={() => run('下架来源', () => disableAdminEarthSource(row.id))} disabled={busy}>下架</button>
        <a className="ghost-btn" href={row.source_url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> 查看</a>
        <button className="ghost-btn danger" onClick={() => window.confirm('确定删除该来源？') && run('删除来源', () => deleteAdminEarthSource(row.id))} disabled={busy}><Trash2 size={14} /></button>
      </div>
    ) },
  ]

  return (
    <div className="dashboard-page admin-backstage-page">
      {notice && <div className="notice">{notice}</div>}

      <section className="admin-command-hero">
        <div>
          <span className="admin-eyebrow"><Globe2 size={15} /> 地球 Online</span>
          <h1>地球 Online 来源管理</h1>
          <p>公开来源进入候选池，审核通过且 low risk 后才会在前台展示。</p>
        </div>
        <div className="admin-command-actions">
          <button className="ghost-btn" onClick={() => run('批量检测', bulkCheckAdminEarthSources)} disabled={busy}><RefreshCw size={16} /> 批量检测</button>
          <button className="primary-btn" onClick={() => setEditing(emptyForm)}><Plus size={16} /> 新增来源</button>
        </div>
      </section>

      <section className="admin-status-strip">
        <article><span><Globe2 size={19} /></span><div><strong>{stats.total}</strong><em>来源总数</em></div></article>
        <article><span><CheckCircle2 size={19} /></span><div><strong>{stats.approved}</strong><em>已审核</em></div></article>
        <article><span><ShieldAlert size={19} /></span><div><strong>{stats.safe}</strong><em>前台可展示</em></div></article>
        <article><span><RefreshCw size={19} /></span><div><strong>{stats.pending}</strong><em>待审核</em></div></article>
      </section>

      {editing && (
        <form className="admin-panel admin-earth-form" onSubmit={submit}>
          <div className="admin-card-title split">
            <div><Globe2 size={20} /><h2>新增公开来源候选</h2></div>
            <button type="button" className="ghost-btn" onClick={() => setEditing(null)}>取消</button>
          </div>
          <div className="admin-form-grid">
            {[
              ['name', '来源名称'],
              ['slug', 'Slug'],
              ['category', '分类'],
              ['source_platform', '平台'],
              ['source_url', '来源 URL'],
              ['thumbnail_url', '缩略图 URL'],
              ['province', '省份'],
              ['city', '城市'],
            ].map(([key, label]) => (
              <label key={key}>
                <span>{label}</span>
                <input className="form-input" value={editing[key] || ''} onChange={event => setEditing({ ...editing, [key]: event.target.value })} required={['name', 'source_url', 'category', 'source_platform'].includes(key)} />
              </label>
            ))}
            <label>
              <span>风险等级</span>
              <select className="form-input" value={editing.risk_level} onChange={event => setEditing({ ...editing, risk_level: event.target.value })}>
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </label>
            <label>
              <span>说明</span>
              <input className="form-input" value={editing.description || ''} onChange={event => setEditing({ ...editing, description: event.target.value })} />
            </label>
          </div>
          <button className="primary-btn">保存为候选</button>
        </form>
      )}

      <section className="admin-panel">
        <div className="card-title-row"><h2>来源审核队列</h2></div>
        <DataTable columns={columns} rows={sources} pagination pageSize={10} />
      </section>
    </div>
  )
}
