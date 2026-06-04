import { useEffect, useMemo, useState } from 'react'
import { TrendingUp, MessageCircle, Image as ImageIcon, HelpCircle, User, Heart, Share2, AlertCircle, Sparkles } from 'lucide-react'
import { getCommunityPosts, likeCommunityPost, postCommunityPost, reportCommunityPost, uploadImage } from '../api/user.js'
import ReviewCard from '../components/common/ReviewCard.jsx'
import EmptyState from '../components/common/EmptyState.jsx'
import HeroSection from '../components/common/HeroSection.jsx'

const tabs = [
  { label: '全部', icon: Sparkles },
  { label: '点评', icon: MessageCircle },
  { label: '图文', icon: ImageIcon },
  { label: '问答', icon: HelpCircle }
]

export default function CommunityPage() {
  const [comments, setComments] = useState([])
  const [activeTab, setActiveTab] = useState('全部')
  const [content, setContent] = useState('')
  const [imageUrl, setImageUrl] = useState('')
  const [notice, setNotice] = useState('')
  const [likes, setLikes] = useState({})
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    getCommunityPosts().then(data => setComments(Array.isArray(data) ? data : (data?.items || [])))
  }, [])

  const visible = useMemo(() => comments.filter(item => activeTab === '全部' || item.category === activeTab), [comments, activeTab])

  const publish = async (event) => {
    event.preventDefault()
    if (!content.trim()) {
      setNotice('说点什么吧...')
      return
    }
    setSubmitting(true)
    try {
      const created = await postCommunityPost({ 
        scenic_id: 1, 
        nickname: '旅行达人', 
        category: imageUrl.trim() ? '图文' : (activeTab === '问答' ? '问答' : '点评'), 
        title: '我的分享', 
        content: content.trim(), 
        images: imageUrl.trim() ? [imageUrl.trim()] : [] 
      })
      
      setComments(current => [{ 
        id: created?.id || Date.now(), 
        nickname: '旅行达人', 
        scenic_id: 1, 
        content: content.trim(), 
        category: imageUrl.trim() ? '图文' : (activeTab === '问答' ? '问答' : '点评'),
        rating: 5, 
        status: 'pending',
        likes: 0,
        images: imageUrl.trim() ? [imageUrl.trim()] : [],
        created_at: new Date().toISOString()
      }, ...current])
      
      setContent('')
      setImageUrl('')
      setNotice('发布成功，正在审核中')
      setTimeout(() => setNotice(''), 3000)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <>
      <HeroSection 
        variant="display"
        images={[
          'https://images.unsplash.com/photo-1527689368864-3a821dbccc34?auto=format&fit=crop&w=1920&q=80',
          'https://images.unsplash.com/photo-1502086223501-7ea244bce1e4?auto=format&fit=crop&w=1920&q=80'
        ]}
        title="游客社区"
        subtitle="分享点评、图片、景区问答与现场经验。"
        capsules={[
          { title: String(comments.length), subtitle: '分享内容' },
          { title: '8.5k', subtitle: '活跃游客' }
        ]}
      />

      <section className="community-layout" style={{ marginTop: '-60px', position: 'relative', zIndex: 5 }}>
        <main className="stack">
          <form className="panel publish-card-v2" onSubmit={publish} style={{ padding: 24, borderRadius: 16 }}>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'var(--color-bg-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--color-primary)' }}>
                <User size={24} />
              </div>
              <textarea 
                value={content} 
                onChange={e => setContent(e.target.value)} 
                placeholder="分享你的旅行见闻..." 
                style={{ flex: 1, border: 'none', background: 'transparent', fontSize: 16, outline: 'none', resize: 'none', height: 80 }}
              />
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', paddingTop: 16, borderTop: '1px solid var(--color-border)' }}>
              <div style={{ display: 'flex', gap: 16 }}>
                <button type="button" className="ghost-btn" style={{ padding: '8px 12px' }} onClick={() => setImageUrl(prompt('请输入图片链接') || '')}>
                  <ImageIcon size={18} /> <span style={{ marginLeft: 4 }}>图片</span>
                </button>
                <button type="button" className="ghost-btn" style={{ padding: '8px 12px' }} onClick={() => { setActiveTab('问答'); setNotice('已切换到问答发布模式') }}>
                  <HelpCircle size={18} /> <span style={{ marginLeft: 4 }}>提问</span>
                </button>
              </div>
              <button className="primary-btn" disabled={submitting} style={{ padding: '8px 24px' }}>
                {submitting ? '发布中...' : '发布'}
              </button>
            </div>
            {imageUrl && <div style={{ marginTop: 12, fontSize: 12, color: 'var(--color-primary)' }}>已添加图片: {imageUrl.substring(0, 30)}...</div>}
          </form>

          <div className="tab-nav-v2" style={{ display: 'flex', gap: 32, margin: '24px 0', padding: '0 8px', borderBottom: '1px solid var(--color-border)' }}>
            {tabs.map(tab => (
              <button 
                key={tab.label} 
                className={`tab-item ${activeTab === tab.label ? 'active' : ''}`} 
                onClick={() => setActiveTab(tab.label)}
                style={{ 
                  padding: '12px 4px', 
                  border: 'none', 
                  background: 'none', 
                  fontSize: 15, 
                  fontWeight: 600,
                  color: activeTab === tab.label ? 'var(--color-primary)' : 'var(--color-muted)',
                  borderBottom: activeTab === tab.label ? '2px solid var(--color-primary)' : '2px solid transparent',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <tab.icon size={18} /> {tab.label}
              </button>
            ))}
          </div>

          {notice && <div className="notice" style={{ marginBottom: 16 }}>{notice}</div>}

          {visible.length ? visible.map(item => (
            <div className="review-shell panel" key={item.id} style={{ padding: 0, marginBottom: 20, overflow: 'hidden' }}>
              <ReviewCard item={item} />
              <div className="card-actions" style={{ padding: '12px 20px', background: 'var(--color-bg-soft)', display: 'flex', gap: 20 }}>
                <button className="ghost-btn" style={{ padding: 0, fontSize: 13 }} onClick={async () => { await likeCommunityPost(item.id); setLikes(current => ({ ...current, [item.id]: (current[item.id] || item.likes || 0) + 1 })) }}>
                  <Heart size={16} fill={likes[item.id] ? 'var(--color-danger)' : 'none'} color={likes[item.id] ? 'var(--color-danger)' : 'currentColor'} /> 
                  <span style={{ marginLeft: 4 }}>{likes[item.id] || item.likes || 0}</span>
                </button>
                <button className="ghost-btn" style={{ padding: 0, fontSize: 13 }} onClick={() => setNotice('回复功能已打开，请在发布框输入你的回复内容。')}>
                  <MessageCircle size={16} /> <span style={{ marginLeft: 4 }}>回复</span>
                </button>
                <button className="ghost-btn" style={{ padding: 0, fontSize: 13 }} onClick={async () => { await reportCommunityPost(item.id); setNotice('已收到您的举报，我们将尽快核实。') }}>
                  <AlertCircle size={16} /> <span style={{ marginLeft: 4 }}>举报</span>
                </button>
              </div>
            </div>
          )) : <EmptyState title="暂无内容" text="切换分类或发布第一条分享。" />}
        </main>

        <aside className="stack" style={{ gap: 20 }}>
          <section className="panel" style={{ padding: 20 }}>
            <h3 style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 16, margin: '0 0 16px 0' }}>
              <TrendingUp size={18} style={{ color: 'var(--color-danger)' }} /> 热门话题
            </h3>
            <div className="stack" style={{ gap: 12 }}>
              {[
                { title: '# 暑期遛娃好去处', count: '2.4w 互动' },
                { title: '# 2025 川藏线自驾攻略', count: '1.8w 互动' },
                { title: '# 苏州园林摄影大赛', count: '9.2k 互动' },
                { title: '# 全国避暑胜地大盘点', count: '1.5w 互动' }
              ].map(topic => (
                <div key={topic.title} style={{ cursor: 'pointer' }}>
                  <strong style={{ display: 'block', fontSize: 14 }}>{topic.title}</strong>
                  <small style={{ color: 'var(--color-muted)', fontSize: 12 }}>{topic.count}</small>
                </div>
              ))}
            </div>
          </section>

          <section className="panel" style={{ padding: 20 }}>
            <h3 style={{ fontSize: 16, margin: '0 0 16px 0' }}>社区公约</h3>
            <p style={{ fontSize: 13, color: 'var(--color-muted)', lineHeight: 1.6 }}>
              欢迎来到景区在线社区！我们鼓励真实、友好的旅行分享。请遵循以下规则：
              <br/>• 发布内容需与景区相关
              <br/>• 保持言论客观公正，不发布虚假信息
              <br/>• 尊重他人版权，引用请注明出处
            </p>
          </section>
        </aside>
      </section>
    </>
  )
}
