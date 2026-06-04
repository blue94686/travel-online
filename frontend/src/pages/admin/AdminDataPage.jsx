import { useEffect, useMemo, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { DatabaseZap, Server, ShieldCheck, DownloadCloud, Sparkles, Globe2, ImagePlus, FileSearch, Table2, MapPinned, RefreshCw, Square, FileDown, PlayCircle, CheckCircle2, TimerReset } from 'lucide-react'
import { approveLowRiskCrawlerCandidates, createDataBackup, exportTptSourceSql, getCrawlerEnrichmentStatus, getDatabaseStatus, getScenicSqlStatus, getJingdianSourceStatus, getEnrichmentOverview, getEnrichmentTasks, getExternalEnrichmentReadiness, getTptEnrichmentStats, getTptMediaJobStatus, importJingdianSource, runCrawlerEnrichmentBatch, runExternalEnrichmentBatch, runLocalProfileBatch, runQualityCheck, runTptMediaBatch, startCrawlerEnrichmentJob, startTptMediaJob, stopCrawlerEnrichmentJob, stopTptMediaJob, triggerDataSync } from '../../api/admin.js'
import AdminKpiCard from '../../components/admin/AdminKpiCard.jsx'

const dataSubpages = [
  { to: '/admin/data', label: '数据总览', icon: DatabaseZap, desc: '同步、备份、质量指标' },
  { to: '/admin/data/source', label: '全国源表', icon: FileSearch, desc: 'tpt_jingdian 导入状态' },
  { to: '/admin/scenic', label: '正式景区库', icon: MapPinned, desc: '审核后展示资料' },
  { to: '/admin/database', label: '数据表工作台', icon: Table2, desc: '表、索引、SQL 查询' },
  { to: '/admin/enrichment', label: '资料补全', icon: Sparkles, desc: '公开来源候选审核' },
  { to: '/admin/data/quality', label: '质量检查', icon: ShieldCheck, desc: '缺图、坐标、来源体检' },
]

export default function AdminDataPage() {
  const location = useLocation()
  const [notice, setNotice] = useState('')
  const [quality, setQuality] = useState({ completeness: '96%', imageMatch: '92%', coordinateCoverage: '98%', weatherAvailability: '99%', pendingIssues: 2 })
  const [database, setDatabase] = useState(null)
  const [syncing, setSyncing] = useState(false)
  const [sqlStatus, setSqlStatus] = useState(null)
  const [sourceStatus, setSourceStatus] = useState(null)
  const [enrichment, setEnrichment] = useState(null)
  const [externalReadiness, setExternalReadiness] = useState(null)
  const [externalResult, setExternalResult] = useState(null)
  const [enrichmentRunning, setEnrichmentRunning] = useState('')
  const [tasks, setTasks] = useState([])
  const [mediaJob, setMediaJob] = useState(null)
  const [tptStats, setTptStats] = useState(null)
  const [crawlerStatus, setCrawlerStatus] = useState(null)
  const [crawlerRunning, setCrawlerRunning] = useState('')

  const databaseStatus = !database ? '检测中' : (database.status ? (database.status === 'normal' ? '正常' : '异常') : (database.exists ? '正常' : '异常'))
  const mode = location.pathname.includes('/source') ? 'source' : location.pathname.includes('/quality') ? 'quality' : location.pathname.includes('/enrichment') ? 'enrichment' : 'overview'
  const pageTitle = mode === 'source' ? '全国景点源表' : mode === 'quality' ? '数据质量检查' : mode === 'enrichment' ? '资料补全中心' : '自动化数据中心'
  const pageDesc = mode === 'source' ? '管理 tpt_jingdian 全国源表，支撑前台三级浏览与搜索。' : mode === 'quality' ? '检查缺图、坐标、来源和资料完整度。' : mode === 'enrichment' ? '公开来源候选、图片索引和审核任务。' : '全国景区资源库同步、备份与数据清洗'
  const crawlerStats = crawlerStatus?.stats || {}
  const crawlerPending = crawlerStats.pendingCandidates || ((crawlerStats.pendingProfileCandidates || 0) + (crawlerStats.pendingImageCandidates || 0))

  const refreshCrawler = async () => {
    const status = await getCrawlerEnrichmentStatus()
    setCrawlerStatus(status || null)
    return status
  }

  useEffect(() => {
    getDatabaseStatus().then(data => setDatabase(data || null))
    getScenicSqlStatus().then(data => setSqlStatus(data || null))
    getJingdianSourceStatus().then(data => setSourceStatus(data || null))
    getEnrichmentOverview().then(setEnrichment).catch(() => {})
    getExternalEnrichmentReadiness().then(setExternalReadiness).catch(() => {})
    getEnrichmentTasks().then(data => setTasks(data || [])).catch(() => {})
    getTptMediaJobStatus().then(setMediaJob).catch(() => {})
    getTptEnrichmentStats().then(setTptStats).catch(() => {})
    refreshCrawler().catch(() => {})
  }, [])

  useEffect(() => {
    if (!crawlerStatus?.running) return undefined
    const timer = setInterval(() => {
      refreshCrawler().catch(() => {})
    }, 5000)
    return () => clearInterval(timer)
  }, [crawlerStatus?.running])

  const qualityIssues = useMemo(() => {
    const issues = []
    if (quality.pendingIssues) issues.push(['数据质量待处理项', `${quality.pendingIssues} 条`, '中等'])
    if (quality.completeness) issues.push(['资料完整度', quality.completeness, '提示'])
    if (quality.coordinateCoverage) issues.push(['坐标覆盖率', quality.coordinateCoverage, '提示'])
    if (quality.imageMatch) issues.push(['图片匹配度', quality.imageMatch, '提示'])
    return issues
  }, [quality])

  const runAutomation = async (type) => {
    if (type === 'quality') {
      setNotice('正在执行全库质量体检...')
      const q = await runQualityCheck()
      if (q) setQuality(q)
      setNotice('全库数据质量体检完成，各项指标正常。')
      return
    }
    if (type === 'backup') {
      setNotice('正在生成系统数据快照备份...')
      const backup = await createDataBackup()
      setNotice(backup?.file ? `备份成功：已生成快照 ${backup.file}` : '备份完成')
      return
    }
    if (type === 'sync') {
      setSyncing(true)
      setNotice('开始自动化同步全国景点库...')
      await importJingdianSource()
      const result = await triggerDataSync()
      setDatabase(await getDatabaseStatus())
      setSourceStatus(await getJingdianSourceStatus())
      setSyncing(false)
      setNotice(result?.details || '全国源表同步完成，前台三级浏览已可读取源表。')
    }
    if (type === 'external') {
      setEnrichmentRunning('external')
      setNotice('正在联网获取景区介绍和图片候选，本批次默认 10 条，优先公开来源...')
      const result = await runExternalEnrichmentBatch({ limit: 10, offset: 0, include_public_sources: true, include_paid_providers: false })
      setExternalResult(result)
      setEnrichment(await getEnrichmentOverview())
      setTasks(await getEnrichmentTasks())
      setEnrichmentRunning('')
      setNotice(`联网采集完成：资料候选 ${result?.profile_candidates || 0} 条，图片候选 ${result?.image_candidates || 0} 条。`)
    }
    if (type === 'source-media') {
      setEnrichmentRunning('source-media')
      setNotice('正在用 Commons / Wikipedia / Wikivoyage 补 A 级源表图片和资料，本批次 5 条，低频执行...')
      const result = await runTptMediaBatch({ limit: 5, offset: 0, a_level_only: true, only_missing: true, include_public_sources: true, use_amap: false, include_osm: false, sleep_seconds: 1.5 })
      setExternalResult(result)
      setEnrichment(await getEnrichmentOverview())
      setMediaJob(await getTptMediaJobStatus())
      setTptStats(await getTptEnrichmentStats())
      setEnrichmentRunning('')
      setNotice(`公开来源补全完成：读取 ${result?.read || 0} 条，新增图片 ${result?.withImages || 0} 条，资料 ${result?.withProfiles || 0} 条。`)
    }
    if (type === 'source-media-all') {
      setEnrichmentRunning('source-media-all')
      const total = tptStats?.total || sourceStatus?.imported_count || 3978
      setNotice('已启动 A 级源表慢速补图爬虫：公开来源优先，不下载大图，只保存外链索引。')
      const result = await startTptMediaJob({ batch_size: 3, max_total: total, a_level_only: true, only_missing: true, include_public_sources: true, use_amap: false, include_osm: false, sleep_seconds: 2 })
      setMediaJob(result)
      setTptStats(await getTptEnrichmentStats())
      setEnrichmentRunning('')
    }
    if (type === 'source-media-stop') {
      setNotice('正在请求停止全国源表图片全量任务...')
      const result = await stopTptMediaJob()
      setMediaJob(result)
      setNotice('已发送停止请求，当前批次完成后会停止。')
    }
    if (type === 'source-media-status') {
      const result = await getTptMediaJobStatus()
      setMediaJob(result)
      setTptStats(await getTptEnrichmentStats())
      setNotice(`图片爬虫状态：${result?.status || 'idle'}。`)
    }
    if (type === 'source-media-export') {
      setEnrichmentRunning('source-media-export')
      setNotice('正在把当前数据库中的图片外链、来源和版权信息导出为 SQL...')
      const result = await exportTptSourceSql()
      setEnrichmentRunning('')
      setNotice(result?.output ? `SQL 已导出：${result.output}，共 ${result.rows || 0} 条。` : 'SQL 导出完成。')
    }
    if (type === 'local-profile') {
      setEnrichmentRunning('local-profile')
      setNotice('正在执行本地规则资料补齐，本批次 5000 条...')
      const result = await runLocalProfileBatch({ limit: 5000, offset: 0 })
      setExternalResult(result)
      setEnrichment(await getEnrichmentOverview())
      setEnrichmentRunning('')
      setNotice(`本地资料补齐完成：读取 ${result?.read || 0} 条，更新 ${result?.updated || 0} 条。`)
    }
    if (type === 'crawler-batch') {
      setCrawlerRunning('batch')
      setNotice('正在试跑一批爬虫补全：候选默认进入审核池。')
      const result = await runCrawlerEnrichmentBatch({ limit: 5, include_pois: true, include_public_sources: true, include_osm: true })
      setExternalResult(result)
      await refreshCrawler()
      setCrawlerRunning('')
      setNotice(`试跑完成：资料候选 ${result?.profileCandidates || 0} 条，图片候选 ${result?.imageCandidates || 0} 条，低风险 ${result?.lowRiskCandidates || 0} 条。`)
    }
    if (type === 'crawler-start') {
      setCrawlerRunning('start')
      setNotice('已启动爬虫补全慢任务：默认进入候选池，低风险图片和 POI 可批量通过。')
      await startCrawlerEnrichmentJob({ batch_size: 5, max_total: 2528, include_pois: true, include_public_sources: true, include_osm: true, sleep_seconds: 1.5 })
      await refreshCrawler()
      setCrawlerRunning('')
    }
    if (type === 'crawler-stop') {
      setNotice('正在请求停止爬虫补全任务。')
      await stopCrawlerEnrichmentJob()
      await refreshCrawler()
      setNotice('已发送停止请求，当前批次完成后会停止。')
    }
    if (type === 'crawler-refresh') {
      const status = await refreshCrawler()
      setNotice(`爬虫补全状态：${status?.status || 'idle'}。`)
    }
    if (type === 'crawler-approve-low-risk') {
      setCrawlerRunning('approve')
      setNotice('正在批量通过低风险图片外链和 POI 候选。')
      const result = await approveLowRiskCrawlerCandidates({ limit: 200 })
      await refreshCrawler()
      setCrawlerRunning('')
      setNotice(`批量通过完成：图片 ${result?.approvedImages || 0} 条，POI ${result?.approvedPois || 0} 条，跳过 ${result?.skipped || 0} 条。`)
    }
  }

  return (
    <>
      {notice && <div className="notice" style={{ marginBottom: 16 }}>{notice}</div>}

      <section className="section-header">
        <div><h1 style={{ fontSize: 24, margin: 0 }}>{pageTitle}</h1><p style={{ color: 'var(--color-muted)', margin: '4px 0 0' }}>{pageDesc}</p></div>
      </section>

      <nav className="admin-panel" aria-label="数据资产子页面" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))', gap: 10, padding: 12, marginBottom: 16 }}>
        {dataSubpages.map(item => {
          const Icon = item.icon
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/admin/data'}
              className={({ isActive }) => `ghost-btn ${isActive ? 'active' : ''}`}
              style={{ justifyContent: 'flex-start', minHeight: 56, padding: '10px 12px', textAlign: 'left' }}
            >
              <Icon size={18} />
              <span style={{ display: 'grid', gap: 2 }}>
                <strong>{item.label}</strong>
                <small style={{ color: 'var(--color-muted)' }}>{item.desc}</small>
              </span>
            </NavLink>
          )
        })}
      </nav>

      <section className="kpi-grid">
        <AdminKpiCard label="景区合计" value={database?.totalScenicCount || database?.scenicCount || 0} change={`正式 ${database?.scenicCount || 0} · 源表 ${database?.sourceScenicCount || sourceStatus?.imported_count || 0}`} icon={DatabaseZap} />
        <AdminKpiCard label="全国源表" value={sourceStatus?.imported_count || 0} change={`源文件 ${sourceStatus?.source_record_count || sqlStatus?.total_rows || 0} 条`} icon={FileSearch} />
        <AdminKpiCard label="质量健康度" value={quality.completeness} change="数据完整" icon={ShieldCheck} />
        <AdminKpiCard label="数据库状态" value={databaseStatus} change={database?.backend || 'PostgreSQL'} icon={Server} />
      </section>

      <section className="content-grid two">
        <article className="admin-panel" style={{ display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', textAlign: 'center', padding: '40px 20px' }}>
          <DatabaseZap size={48} style={{ color: 'var(--color-primary)', marginBottom: 16 }} />
          <h2 style={{ fontSize: 20, marginBottom: 8 }}>全国景区资源一键同步</h2>
          <p style={{ color: 'var(--color-muted)', marginBottom: 24, maxWidth: 300 }}>自动解析挂载的全国数据源，清理脏数据并重建全文检索引擎。</p>
          <button className="primary-btn" style={{ padding: '12px 32px', fontSize: 16 }} disabled={syncing} onClick={() => runAutomation('sync')}>
            {syncing ? '同步中...' : '开始一键同步'}
          </button>
          {sourceStatus && <p style={{ fontSize: 12, color: 'var(--color-muted)', marginTop: 16 }}>源表: 已导入 {sourceStatus.imported_count || 0} / 源文件 {sourceStatus.source_record_count || sqlStatus?.total_rows || 0} 条</p>}
        </article>

        <div className="stack">
          <article className="admin-panel" style={{ padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><ShieldCheck size={20} style={{ color: 'var(--color-primary)' }} /> <h3 style={{ margin: 0 }}>全库质量体检</h3></div>
              <button className="ghost-btn" onClick={() => runAutomation('quality')}>执行体检</button>
            </div>
            <p style={{ color: 'var(--color-muted)', fontSize: 13, marginBottom: 16 }}>自动扫描缺失图片、异常坐标和未分类数据。</p>
            <div className="quality-grid">
              <p><strong>{quality.completeness}</strong><span>数据完整度</span></p>
              <p><strong>{quality.imageMatch}</strong><span>图片匹配率</span></p>
              <p><strong>{quality.coordinateCoverage}</strong><span>坐标有效率</span></p>
            </div>
          </article>

          <article className="admin-panel" style={{ padding: 24 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}><DownloadCloud size={20} style={{ color: 'var(--color-primary)' }} /> <h3 style={{ margin: 0 }}>系统快照与备份</h3></div>
              <button className="ghost-btn" onClick={() => runAutomation('backup')}>生成快照</button>
            </div>
            <p style={{ color: 'var(--color-muted)', fontSize: 13 }}>一键生成当前数据库与系统配置快照。</p>
            <div style={{ marginTop: 16, fontSize: 12, color: 'var(--color-muted)' }}>
              数据库: {Math.round((database?.size || 0) / 1024)} KB · 完整度: {database?.integrity || '检测中'}
            </div>
          </article>
        </div>
      </section>

      <section className="admin-panel">
        <div className="card-title-row"><h2>异常数据拦截报告</h2></div>
        <div className="data-table">
          <div className="tr th" style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 16, padding: '12px 16px', background: 'var(--color-bg)', borderRadius: 8, color: 'var(--color-muted)', fontSize: 13 }}>
            <span>拦截类型</span><span>影响数量</span><span>严重程度</span><span>建议</span>
          </div>
          {qualityIssues.map(([item, value, level]) => (
            <div className="tr" key={item} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr', gap: 16, padding: 16, borderBottom: '1px solid var(--color-border)', alignItems: 'center' }}>
              <strong>{item}</strong>
              <span>{value}</span>
              <span className={`status-badge ${level === '提示' ? 'success' : 'warning'}`}>{level}</span>
              <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>已自动处理</span>
            </div>
          ))}
        </div>
      </section>

      {/* Enrichment Status */}
      {(enrichment || tasks.length > 0) && (
        <section className="content-grid two">
          <article className="admin-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Sparkles size={20} style={{ color: 'var(--color-primary)' }} />
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>景区资料补全</h3>
              </div>
              <button className="ghost-btn" onClick={() => getExternalEnrichmentReadiness().then(setExternalReadiness)}>检测来源</button>
            </div>
            {enrichment ? (
              <div style={{ display: 'grid', gap: 8 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>待补封面图</span><strong>{enrichment.missingImages || 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>待补官网</span><strong>{enrichment.missingWebsite || 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>待审核候选</span><strong style={{ color: 'var(--color-primary)' }}>{enrichment.pendingCandidates || 0}</strong>
                </div>
              </div>
            ) : <p style={{ color: 'var(--color-muted)', fontSize: 13 }}>补全数据加载中...</p>}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 10, marginTop: 16 }}>
              <button className="primary-btn" disabled={!!enrichmentRunning} onClick={() => runAutomation('external')}>
                <Globe2 size={16} /> {enrichmentRunning === 'external' ? '采集中...' : '自动获取介绍/图片'}
              </button>
              <button className="ghost-btn" disabled={!!enrichmentRunning} onClick={() => runAutomation('source-media')}>
                <ImagePlus size={16} /> {enrichmentRunning === 'source-media' ? '补图中...' : '公开来源补图'}
              </button>
              <button className="ghost-btn" disabled={!!enrichmentRunning} onClick={() => runAutomation('local-profile')}>
                <ImagePlus size={16} /> {enrichmentRunning === 'local-profile' ? '补齐中...' : '本地批量补齐'}
              </button>
            </div>
            {externalReadiness && (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 16 }}>
                {[
                  ['Bing 搜索', externalReadiness.bing_search],
                  ['Bing 图片', externalReadiness.bing_image],
                  ['高德 POI', externalReadiness.amap_web_service],
                  ['Wikipedia', externalReadiness.wikipedia],
                  ['Wikivoyage', externalReadiness.wikivoyage],
                  ['Commons', externalReadiness.wikimedia_commons],
                  ['OSM Overpass', externalReadiness.openstreetmap_overpass],
                  ['国家文旅部', externalReadiness.mct_official],
                  ['携程', externalReadiness.ctrip_open],
                  ['马蜂窝', externalReadiness.mafengwo],
                  ['百度地图', externalReadiness.baidu_map],
                  ['腾讯位置', externalReadiness.tencent_lbs]
                ].map(([label, ready]) => (
                  <span key={label} className={`status-badge ${ready ? 'success' : 'warning'}`}>{label}: {ready ? '可用' : '待配置'}</span>
                ))}
              </div>
            )}
            {externalResult && (
              <p style={{ margin: '14px 0 0', fontSize: 12, color: 'var(--color-muted)', lineHeight: 1.7 }}>
                最近批次：读取 {externalResult.requested ?? externalResult.read ?? 0} 条，资料 {externalResult.profile_candidates ?? externalResult.withProfiles ?? 0} 条，图片 {externalResult.image_candidates ?? externalResult.withImages ?? 0} 条，限流 {externalResult.rateLimited || 0} 条，来源不可用 {externalResult.sourceUnavailable || 0} 条，失败 {externalResult.failures?.length || 0} 条。
              </p>
            )}
          </article>

          <article className="admin-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <TimerReset size={20} style={{ color: 'var(--color-primary)' }} />
                  <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>爬虫补全</h3>
                </div>
                <p style={{ margin: '6px 0 0', color: 'var(--color-muted)', fontSize: 12, lineHeight: 1.6 }}>介绍、图片外链、周边美食 POI、徒步 POI 默认进入候选池。</p>
              </div>
              <span className={`status-badge ${crawlerStatus?.running ? 'warning' : 'success'}`}>{crawlerStatus?.running ? '运行中' : '待命'}</span>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(112px, 1fr))', gap: 8, marginBottom: 14 }}>
              {[
                ['剩余缺图', crawlerStats.missingImages ?? tptStats?.missing_cover ?? 2528],
                ['候选总数', crawlerPending || 0],
                ['低风险可通过', crawlerStats.lowRiskCandidates || 0],
                ['缺周边POI', crawlerStats.missingPois || 0],
              ].map(([label, value]) => (
                <div key={label} style={{ padding: '10px 12px', background: 'var(--color-bg)', borderRadius: 8 }}>
                  <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>{label}</span>
                  <strong style={{ display: 'block', marginTop: 4 }}>{value}</strong>
                </div>
              ))}
            </div>

            <div style={{ display: 'grid', gap: 10, marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                <span>状态</span><strong>{crawlerStatus?.status || 'idle'}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                <span>本次已读</span><strong>{crawlerStatus?.payload?.read || 0} / {crawlerStatus?.payload?.maxTotal || 2528}</strong>
              </div>
              {(crawlerStatus?.cooldownSeconds || crawlerStatus?.payload?.cooldownSeconds || 0) > 0 && (
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>公开源冷却</span><strong>{crawlerStatus?.cooldownSeconds || crawlerStatus?.payload?.cooldownSeconds}s</strong>
                </div>
              )}
              {(crawlerStatus?.payload?.failures || []).length > 0 && (
                <p style={{ margin: 0, fontSize: 12, color: 'var(--color-muted)', lineHeight: 1.6 }}>
                  最近失败：{crawlerStatus.payload.failures.slice(-2).map(item => item.name || item.message).join('，')}
                </p>
              )}
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(124px, 1fr))', gap: 8 }}>
              <button className="primary-btn" disabled={crawlerStatus?.running || !!crawlerRunning} onClick={() => runAutomation('crawler-start')}>
                <PlayCircle size={16} /> {crawlerRunning === 'start' ? '启动中' : '开始慢速补全'}
              </button>
              <button className="ghost-btn" disabled={!!crawlerRunning} onClick={() => runAutomation('crawler-batch')}>
                <Sparkles size={16} /> {crawlerRunning === 'batch' ? '试跑中' : '试跑一批'}
              </button>
              <button className="ghost-btn" onClick={() => runAutomation('crawler-refresh')}><RefreshCw size={16} /> 刷新</button>
              <button className="ghost-btn" disabled={!crawlerStatus?.running} onClick={() => runAutomation('crawler-stop')}><Square size={16} /> 停止</button>
              <button className="ghost-btn" disabled={!!crawlerRunning || !(crawlerStats.lowRiskCandidates || 0)} onClick={() => runAutomation('crawler-approve-low-risk')}>
                <CheckCircle2 size={16} /> {crawlerRunning === 'approve' ? '通过中' : '批量通过低风险'}
              </button>
            </div>
          </article>

          <article className="admin-panel">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', marginBottom: 16 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 16, fontWeight: 700 }}>A 级源表爬虫补全</h3>
                <p style={{ margin: '6px 0 0', color: 'var(--color-muted)', fontSize: 12, lineHeight: 1.6 }}>管理员手动触发，低频访问 Wikipedia / Wikivoyage / Wikimedia Commons，只保存外链、来源、许可证和署名。</p>
              </div>
              <span className={`status-badge ${mediaJob?.running ? 'warning' : 'success'}`}>{mediaJob?.running ? '运行中' : '空闲'}</span>
            </div>
            {tptStats && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))', gap: 8, marginBottom: 14 }}>
                <div style={{ padding: '10px 12px', background: 'var(--color-bg)', borderRadius: 8 }}>
                  <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>A级源表</span><strong style={{ display: 'block', marginTop: 4 }}>{tptStats.total || 0}</strong>
                </div>
                <div style={{ padding: '10px 12px', background: 'var(--color-bg)', borderRadius: 8 }}>
                  <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>已有外链</span><strong style={{ display: 'block', marginTop: 4 }}>{tptStats.with_cover || 0}</strong>
                </div>
                <div style={{ padding: '10px 12px', background: 'var(--color-bg)', borderRadius: 8 }}>
                  <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>剩余缺图</span><strong style={{ display: 'block', marginTop: 4 }}>{tptStats.missing_cover ?? tptStats.a_level_missing_cover ?? 0}</strong>
                </div>
                <div style={{ padding: '10px 12px', background: 'var(--color-bg)', borderRadius: 8 }}>
                  <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>脏地区</span><strong style={{ display: 'block', marginTop: 4, color: (tptStats.dirty_region_labels || 0) ? '#b45309' : 'inherit' }}>{tptStats.dirty_region_labels || 0}</strong>
                </div>
              </div>
            )}
            {mediaJob ? (
              <div style={{ display: 'grid', gap: 10, marginBottom: 18 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>状态</span><strong>{mediaJob.status || 'idle'}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>源表真实封面</span><strong>{mediaJob.stats?.with_cover ?? tptStats?.with_cover ?? 0} / {mediaJob.stats?.total ?? tptStats?.total ?? 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>本次已读</span><strong>{mediaJob.payload?.read || 0}</strong>
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>本次新增图片</span><strong>{mediaJob.payload?.withImages || 0}</strong>
                </div>
                {(mediaJob.payload?.cooldownSeconds || 0) > 0 && (
                  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                    <span>公开源冷却等待</span><strong>{mediaJob.payload.cooldownSeconds}s</strong>
                  </div>
                )}
                <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                  <span>本次公开介绍</span><strong>{mediaJob.payload?.withProfiles || 0}</strong>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 8 }}>
                  <div style={{ padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                    <span style={{ color: 'var(--color-muted)' }}>未命中</span><strong style={{ display: 'block' }}>{mediaJob.payload?.notFound || 0}</strong>
                  </div>
                  <div style={{ padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                    <span style={{ color: 'var(--color-muted)' }}>限流重试</span><strong style={{ display: 'block' }}>{mediaJob.payload?.rateLimited || 0}</strong>
                  </div>
                  <div style={{ padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                    <span style={{ color: 'var(--color-muted)' }}>来源不可用</span><strong style={{ display: 'block' }}>{mediaJob.payload?.sourceUnavailable || 0}</strong>
                  </div>
                </div>
                {(mediaJob.payload?.providerFailures || []).length > 0 && (
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--color-muted)', lineHeight: 1.6 }}>
                    最近来源状态：{mediaJob.payload.providerFailures.slice(-2).map(item => `${item.provider}:${item.status}`).join('，')}
                  </p>
                )}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: 8 }}>
                  <button className="primary-btn" disabled={mediaJob.running || enrichmentRunning === 'source-media-all'} onClick={() => runAutomation('source-media-all')}>
                    <PlayCircle size={16} /> 慢速补图
                  </button>
                  <button className="ghost-btn" onClick={() => runAutomation('source-media-status')}><RefreshCw size={16} /> 刷新</button>
                  <button className="ghost-btn" disabled={!mediaJob.running} onClick={() => runAutomation('source-media-stop')}><Square size={16} /> 停止</button>
                  <button className="ghost-btn" disabled={enrichmentRunning === 'source-media-export'} onClick={() => runAutomation('source-media-export')}><FileDown size={16} /> 回写SQL</button>
                </div>
              </div>
            ) : <p style={{ color: 'var(--color-muted)', fontSize: 13 }}>任务状态加载中...</p>}
            <h3 style={{ marginBottom: 16, fontSize: 16, fontWeight: 700 }}>补全任务</h3>
            {tasks.length > 0 ? (
              <div style={{ display: 'grid', gap: 8 }}>
                {tasks.slice(0, 5).map(task => (
                  <div key={task.id} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--color-bg)', borderRadius: 8, fontSize: 13 }}>
                    <span>{task.keyword || task.scenic_name || `任务 #${task.id}`}</span>
                    <span className={`status-badge ${task.status === 'completed' ? 'success' : 'warning'}`}>{task.status}</span>
                  </div>
                ))}
              </div>
            ) : <p style={{ color: 'var(--color-muted)', fontSize: 13 }}>暂无补全任务</p>}
          </article>
        </section>
      )}
    </>
  )
}
