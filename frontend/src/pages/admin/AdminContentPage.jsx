import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { Camera, MessageSquare, LayoutTemplate, CheckCircle2, AlertTriangle, FileText, Flag, Plus, Trash2, Edit2, ExternalLink } from 'lucide-react'
import {
  approveImage, rejectImage, approveComment, hideComment, deleteComment, addIpBlacklist, getDashboard,
  getBanners, createBanner, updateBanner, deleteBanner,
  getArticles, createArticle, updateArticle, deleteArticle
} from '../../api/admin.js'
import { imageFallback } from '../../api/fallback.js'
import DataTable from '../../components/common/DataTable.jsx'

export default function AdminContentPage() {
  const location = useLocation()
  const [data, setData] = useState(null)
  const [banners, setBanners] = useState([])
  const [articles, setArticles] = useState([])
  const [notice, setNotice] = useState('')
  const [activeTab, setActiveTab] = useState('图片库审核')
  const [rejectReason, setRejectReason] = useState('')
  const [rejectTarget, setRejectTarget] = useState(null)
  
  const [bannerEditing, setBannerEditing] = useState(null)
  const [articleEditing, setArticleEditing] = useState(null)

  useEffect(() => {
    getDashboard().then(setData)
    getBanners().then(setBanners)
    getArticles().then(setArticles)
  }, [])

  useEffect(() => {
    if (location.pathname.includes('/admin/comments')) setActiveTab('游客评论中心')
    else if (location.pathname.includes('/admin/images')) setActiveTab('图片库审核')
    else if (location.pathname.includes('/admin/content')) setActiveTab('内容发布管理')
  }, [location.pathname])

  const handleImage = async (item, action) => {
    if (action === 'approve') await approveImage(item.id)
    if (action === 'reject') await rejectImage(item.id)
    setData(current => ({ ...current, imageReviewQueue: current.imageReviewQueue.filter(row => row.id !== item.id) }))
    setNotice(action === 'approve' ? '图片已通过' : '图片已拒绝')
  }

  const handleRejectWithReason = async () => {
    if (!rejectTarget) return
    await rejectImage(rejectTarget.id)
    setData(current => ({ ...current, imageReviewQueue: current.imageReviewQueue.filter(row => row.id !== rejectTarget.id) }))
    setNotice(`图片已拒绝: ${rejectReason || '未填写原因'}`)
    setRejectTarget(null)
    setRejectReason('')
  }

  const handleComment = async (item, action) => {
    if (action === 'approve') await approveComment(item.id)
    if (action === 'hide') await hideComment(item.id)
    if (action === 'delete') await deleteComment(item.id)
    if (action === 'block_ip') {
      await addIpBlacklist({ ip: item.ip_address || '127.0.0.1', reason: '发布违规评论' })
      setNotice('已将该 IP 加入黑名单')
      await hideComment(item.id)
    }
    setData(current => ({ ...current, commentReviewQueue: current.commentReviewQueue.filter(row => row.id !== item.id) }))
    if (['approve', 'hide', 'delete'].includes(action)) {
      setNotice(action === 'approve' ? '评论已通过' : action === 'hide' ? '评论已隐藏' : '评论已删除')
    }
  }

  const handleSaveBanner = async (e) => {
    e.preventDefault()
    if (bannerEditing.id) {
      await updateBanner(bannerEditing.id, bannerEditing)
      setBanners(current => current.map(b => b.id === bannerEditing.id ? bannerEditing : b))
      setNotice('Banner 已更新')
    } else {
      const res = await createBanner(bannerEditing)
      setBanners(current => [...current, { ...bannerEditing, id: res.id }])
      setNotice('Banner 已创建')
    }
    setBannerEditing(null)
  }

  const handleDeleteBanner = async (id) => {
    if (!confirm('确定要删除这个 Banner 吗？')) return
    await deleteBanner(id)
    setBanners(current => current.filter(b => b.id !== id))
    setNotice('Banner 已删除')
  }

  const handleSaveArticle = async (e) => {
    e.preventDefault()
    if (articleEditing.id) {
      await updateArticle(articleEditing.id, articleEditing)
      setArticles(current => current.map(a => a.id === articleEditing.id ? articleEditing : a))
      setNotice('文章已更新')
    } else {
      const res = await createArticle(articleEditing)
      setArticles(current => [{ ...articleEditing, id: res.id, created_at: new Date().toISOString() }, ...current])
      setNotice('文章已发布')
    }
    setArticleEditing(null)
  }

  const handleDeleteArticle = async (id) => {
    if (!confirm('确定要删除这篇文章吗？')) return
    await deleteArticle(id)
    setArticles(current => current.filter(a => a.id !== id))
    setNotice('文章已删除')
  }

  const tabs = ['图片库审核', '游客评论中心', '内容发布管理', '网站功能推荐', '前端页面编排']
  const imageQueue = data?.imageReviewQueue || []
  const commentQueue = data?.commentReviewQueue || []

  const imageColumns = [
    { key: 'preview', label: '预览', render: row => <img src={row.url || imageFallback} onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = imageFallback }} style={{ width: 60, height: 60, objectFit: 'cover', borderRadius: 6 }} alt="" /> },
    { key: 'scenic', label: '景区', render: row => <strong>{row.scenic || `图片 #${row.id}`}</strong> },
    { key: 'source', label: '来源', render: row => row.source || '用户上传' },
    { key: 'quality', label: '质检', render: row => row.quality_check ? <span className={`status-badge ${row.quality_check === 'pass' ? 'success' : 'warning'}`}>{row.quality_check}</span> : <span style={{ color: 'var(--color-muted)', fontSize: 12 }}>待检测</span> },
    { key: 'actions', label: '操作', render: row => (
      <div style={{ display: 'flex', gap: 6 }}>
        <button className="primary-btn" style={{ padding: '4px 12px', fontSize: 12 }} onClick={() => handleImage(row, 'approve')}>通过</button>
        <button className="ghost-btn" style={{ padding: '4px 12px', fontSize: 12 }} onClick={() => setRejectTarget(row)}>拒绝</button>
      </div>
    )},
  ]

  const commentColumns = [
    { key: 'nickname', label: '用户', render: row => <div><strong>{row.nickname}</strong><br/><small style={{ color: 'var(--color-muted)' }}>{row.ip_address || '127.0.0.1'}</small></div> },
    { key: 'scenic', label: '景区', render: row => row.scenic || `景区 #${row.scenic_id}` },
    { key: 'content', label: '内容', render: row => <span style={{ maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', display: 'block' }}>{row.content}</span> },
    { key: 'rating', label: '评分', render: row => row.rating ? `${row.rating} 分` : '-' },
    { key: 'actions', label: '操作', render: row => (
      <div style={{ display: 'flex', gap: 6 }}>
        <button className="primary-btn" style={{ padding: '4px 12px', fontSize: 12 }} onClick={() => handleComment(row, 'approve')}>通过</button>
        <button className="ghost-btn" style={{ padding: '4px 12px', fontSize: 12 }} onClick={() => handleComment(row, 'hide')}>隐藏</button>
        <button className="ghost-btn" style={{ padding: '4px 12px', fontSize: 12, color: 'var(--color-danger)' }} onClick={() => handleComment(row, 'block_ip')} title="隐藏评论并将 IP 拉黑">拉黑</button>
      </div>
    )},
  ]

  const bannerColumns = [
    { key: 'image', label: '封面', render: row => <img src={row.image_url || imageFallback} style={{ width: 100, height: 40, objectFit: 'cover', borderRadius: 4 }} alt="" /> },
    { key: 'title', label: '标题', render: row => <strong>{row.title}</strong> },
    { key: 'link', label: '链接', render: row => <span style={{ fontSize: 12, color: 'var(--color-muted)' }}>{row.link_url || '-'}</span> },
    { key: 'status', label: '状态', render: row => <span className={`status-badge ${row.is_active ? 'success' : 'warning'}`}>{row.is_active ? '展示中' : '已下架'}</span> },
    { key: 'actions', label: '操作', render: row => (
      <div style={{ display: 'flex', gap: 6 }}>
        <button className="ghost-btn" onClick={() => setBannerEditing(row)}><Edit2 size={14} /></button>
        <button className="ghost-btn" onClick={() => handleDeleteBanner(row.id)}><Trash2 size={14} /></button>
      </div>
    )},
  ]

  const articleColumns = [
    { key: 'title', label: '标题', render: row => <strong>{row.title}</strong> },
    { key: 'category', label: '分类', render: row => <span className="status-badge">{row.category}</span> },
    { key: 'author', label: '作者' },
    { key: 'date', label: '发布时间', render: row => <span style={{ fontSize: 12 }}>{row.created_at?.split('T')[0]}</span> },
    { key: 'status', label: '状态', render: row => <span className={`status-badge ${row.is_published ? 'success' : 'warning'}`}>{row.is_published ? '已发布' : '草稿'}</span> },
    { key: 'actions', label: '操作', render: row => (
      <div style={{ display: 'flex', gap: 6 }}>
        <button className="ghost-btn" onClick={() => setArticleEditing(row)}><Edit2 size={14} /></button>
        <button className="ghost-btn" onClick={() => handleDeleteArticle(row.id)}><Trash2 size={14} /></button>
      </div>
    )},
  ]

  return (
    <div className="dashboard-page">
      {notice && <div className="notice" style={{ marginBottom: 16 }}>{notice}</div>}

      {/* Reject Reason Modal */}
      {rejectTarget && (
        <div className="modal-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
            <h3 style={{ margin: 0 }}>拒绝原因</h3>
            <button className="ghost-btn" onClick={() => setRejectTarget(null)}>取消</button>
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 12 }}>
            {['图片模糊', '内容不当', '非景区相关', '重复上传', '版权问题'].map(reason => (
              <button key={reason} className={`ghost-btn ${rejectReason === reason ? 'active' : ''}`} style={rejectReason === reason ? { background: 'var(--color-primary-soft)', color: 'var(--color-primary)' } : {}} onClick={() => setRejectReason(reason)}>{reason}</button>
            ))}
          </div>
          <input className="form-input" value={rejectReason} onChange={e => setRejectReason(e.target.value)} placeholder="或输入自定义原因" style={{ marginBottom: 12 }} />
          <button className="primary-btn" onClick={handleRejectWithReason}>确认拒绝</button>
        </div>
      )}

      {/* Banner Editing Modal */}
      {bannerEditing && (
        <div className="modal-panel">
          <h3>{bannerEditing.id ? '编辑 Banner' : '新增 Banner'}</h3>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label>标题</label>
            <input className="form-input" value={bannerEditing.title || ''} onChange={e => setBannerEditing({...bannerEditing, title: e.target.value})} />
          </div>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label>图片 URL</label>
            <input className="form-input" value={bannerEditing.image_url || ''} onChange={e => setBannerEditing({...bannerEditing, image_url: e.target.value})} />
          </div>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label>跳转链接</label>
            <input className="form-input" value={bannerEditing.link_url || ''} onChange={e => setBannerEditing({...bannerEditing, link_url: e.target.value})} />
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
            <button className="primary-btn" onClick={handleSaveBanner}>保存</button>
            <button className="ghost-btn" onClick={() => setBannerEditing(null)}>取消</button>
          </div>
        </div>
      )}

      {/* Article Editing Modal */}
      {articleEditing && (
        <div className="modal-panel" style={{ maxWidth: 800 }}>
          <h3>{articleEditing.id ? '编辑文章' : '写新文章'}</h3>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label>标题</label>
            <input className="form-input" value={articleEditing.title || ''} onChange={e => setArticleEditing({...articleEditing, title: e.target.value})} />
          </div>
          <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
            <div className="form-group" style={{ flex: 1 }}>
              <label>分类</label>
              <select className="form-input" value={articleEditing.category || '攻略'} onChange={e => setArticleEditing({...articleEditing, category: e.target.value})}>
                <option>攻略</option>
                <option>公告</option>
                <option>资讯</option>
                <option>专题</option>
              </select>
            </div>
            <div className="form-group" style={{ flex: 1 }}>
              <label>作者</label>
              <input className="form-input" value={articleEditing.author || '管理员'} onChange={e => setArticleEditing({...articleEditing, author: e.target.value})} />
            </div>
          </div>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label>封面图 URL</label>
            <input className="form-input" value={articleEditing.cover_image || ''} onChange={e => setArticleEditing({...articleEditing, cover_image: e.target.value})} />
          </div>
          <div className="form-group" style={{ marginBottom: 12 }}>
            <label>内容</label>
            <textarea className="form-input" style={{ height: 200 }} value={articleEditing.content || ''} onChange={e => setArticleEditing({...articleEditing, content: e.target.value})} />
          </div>
          <div style={{ display: 'flex', gap: 12, marginTop: 20 }}>
            <button className="primary-btn" onClick={handleSaveArticle}>发布文章</button>
            <button className="ghost-btn" onClick={() => setArticleEditing(null)}>取消</button>
          </div>
        </div>
      )}

      <section className="section-header">
        <div><h1 style={{ fontSize: 24, margin: 0 }}>内容与社区</h1><p style={{ color: 'var(--color-muted)', margin: '4px 0 0' }}>处理待审核图片、评论及页面推荐</p></div>
      </section>

      <div className="tab-nav panel" style={{ display: 'flex', gap: 20, padding: '16px 24px', marginBottom: 24 }}>
        {tabs.map(tab => (
          <button key={tab} className={`ghost-btn ${activeTab === tab ? 'active' : ''}`} onClick={() => setActiveTab(tab)} style={activeTab === tab ? { background: 'var(--color-primary-soft)', color: 'var(--color-primary)' } : {}}>
            {tab === '图片库审核' && <Camera size={18} />}
            {tab === '游客评论中心' && <MessageSquare size={18} />}
            {tab === '内容发布管理' && <FileText size={18} />}
            {tab === '网站功能推荐' && <Flag size={18} />}
            {tab === '前端页面编排' && <LayoutTemplate size={18} />}
            <span style={{ marginLeft: 8 }}>{tab}</span>
            {tab === '图片库审核' && imageQueue.length > 0 && <span style={{ marginLeft: 4, background: 'var(--color-danger)', color: '#fff', borderRadius: 10, padding: '1px 7px', fontSize: 11 }}>{imageQueue.length}</span>}
            {tab === '游客评论中心' && commentQueue.length > 0 && <span style={{ marginLeft: 4, background: 'var(--color-danger)', color: '#fff', borderRadius: 10, padding: '1px 7px', fontSize: 11 }}>{commentQueue.length}</span>}
          </button>
        ))}
      </div>

      {activeTab === '图片库审核' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>待审核图片 ({imageQueue.length})</h2></div>
          <DataTable columns={imageColumns} rows={imageQueue} pagination pageSize={10} />
        </section>
      )}

      {activeTab === '游客评论中心' && (
        <section className="admin-panel">
          <div className="card-title-row"><h2>待审核评论 ({commentQueue.length})</h2></div>
          <DataTable columns={commentColumns} rows={commentQueue} pagination pageSize={10} />
        </section>
      )}

      {activeTab === '内容发布管理' && (
        <section className="admin-panel">
          <div className="card-title-row">
            <h2>文章列表</h2>
            <button className="primary-btn" onClick={() => setArticleEditing({title: '', content: '', category: '攻略', author: '管理员'})}><Plus size={16} /> 写新文章</button>
          </div>
          <DataTable columns={articleColumns} rows={articles} pagination pageSize={10} />
        </section>
      )}

      {activeTab === '网站功能推荐' && (
        <section className="admin-panel">
          <div className="card-title-row">
            <h2>首页 Banner 管理</h2>
            <button className="primary-btn" onClick={() => setBannerEditing({title: '', image_url: '', link_url: '', order_index: 0, is_active: 1})}><Plus size={16} /> 新增 Banner</button>
          </div>
          <DataTable columns={bannerColumns} rows={banners} pagination pageSize={5} />
          
          <div className="card-title-row" style={{ marginTop: 40 }}>
            <h2>核心功能开关</h2>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 16 }}>
            {[
              { name: '实况地球 Online', desc: '开启首页实时来源展示' },
              { name: '智能推荐算法', desc: '基于用户偏好自动排序' },
              { name: '用户上传权限', desc: '允许普通用户上传景区图片' },
              { name: '评论深度审核', desc: '使用敏感词库自动过滤不当言论' }
            ].map(item => (
              <div key={item.name} className="panel" style={{ padding: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div><strong>{item.name}</strong><p style={{ margin: 0, fontSize: 11, color: 'var(--color-muted)' }}>{item.desc}</p></div>
                <input type="checkbox" defaultChecked />
              </div>
            ))}
          </div>
        </section>
      )}

      {activeTab === '前端页面编排' && (
        <section className="admin-panel" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <LayoutTemplate size={48} style={{ color: 'var(--color-muted)', margin: '0 auto 16px' }} />
          <h2>首页推荐配置</h2>
          <p style={{ color: 'var(--color-muted)', maxWidth: 400, margin: '0 auto 24px' }}>基于数据库自动推荐算法接管前端排版，如需人工干预请通过 JSON 编辑器配置。</p>
          <button className="ghost-btn">打开高级配置</button>
        </section>
      )}
    </div>
  )
}
