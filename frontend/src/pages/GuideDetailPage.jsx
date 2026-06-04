import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft, BookOpen, CalendarDays, CheckCircle2, Clock3, Compass, MapPinned, UserRound } from 'lucide-react'
import EmptyState from '../components/common/EmptyState.jsx'
import HeroSection from '../components/common/HeroSection.jsx'
import { getArticle } from '../api/layouts.js'

const GUIDE_CHECKLIST = [
  '出发前确认景区开放时间、预约规则和天气预警。',
  '优先保存目的地、停车场和返程路线，避免现场临时查找。',
  '热门景区建议错峰入园，摄影点位提前规划日出日落时间。',
  '涉及山地、水域或长距离步行时，预留体力和补给时间。',
]

const GUIDE_SECTIONS = [
  ['适合人群', '第一次到访的游客、周末短途旅行者、希望快速建立行程框架的家庭和自驾用户。'],
  ['推荐节奏', '建议先确定核心景区，再围绕交通、天气、餐饮和住宿补充半日或一日支线。'],
  ['避坑提醒', '不要只看单个景区评分，需同时确认交通耗时、排队情况、天气变化和临时闭园公告。'],
]

export default function GuideDetailPage() {
  const { id } = useParams()
  const [article, setArticle] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    getArticle(id).then(setArticle).finally(() => setLoading(false))
  }, [id])

  if (loading) return <EmptyState title="正在加载官方指南..." />

  if (!article) {
    return (
      <EmptyState
        title="未找到这篇指南"
        text="文章可能已下线或尚未发布。"
        action={<Link className="primary-btn" to="/">返回首页</Link>}
      />
    )
  }

  return (
    <>
      <HeroSection
        variant="display"
        images={[
          '/images/hero-mountain-lake.jpg',
        ]}
        title={article.title}
        subtitle={article.category || '官方指南'}
        capsules={[
          { title: article.author || '管理员', subtitle: '发布者' },
          { title: article.created_at?.split('T')[0] || article.created_at?.split(' ')[0] || '最新', subtitle: '发布时间' },
        ]}
      />

      <article className="guide-detail-page">
        <Link className="ghost-btn guide-back-link" to="/"><ArrowLeft size={16} /> 返回首页</Link>
        <div className="guide-meta-row">
          <span><UserRound size={16} /> {article.author || '管理员'}</span>
          <span><CalendarDays size={16} /> {article.created_at?.split('T')[0] || article.created_at?.split(' ')[0] || '最新发布'}</span>
          <span><Clock3 size={16} /> 预计阅读 3 分钟</span>
        </div>

        <section className="guide-summary-panel">
          <div>
            <BookOpen size={20} />
            <strong>指南摘要</strong>
          </div>
          <p>{String(article.content || '').slice(0, 110)}{String(article.content || '').length > 110 ? '...' : ''}</p>
        </section>

        <div className="guide-content">
          {String(article.content || '').split(/\n+/).filter(Boolean).map((paragraph, index) => (
            <p key={index}>{paragraph}</p>
          ))}
        </div>

        <section className="guide-section-grid">
          {GUIDE_SECTIONS.map(([title, desc]) => (
            <div key={title}>
              <Compass size={18} />
              <strong>{title}</strong>
              <p>{desc}</p>
            </div>
          ))}
        </section>

        <section className="guide-checklist-panel">
          <h2>出发前清单</h2>
          <div>
            {GUIDE_CHECKLIST.map(item => (
              <p key={item}><CheckCircle2 size={17} /> {item}</p>
            ))}
          </div>
        </section>

        <section className="guide-related-panel">
          <Link to="/rankings"><MapPinned size={18} /><span><strong>热门榜单</strong><small>查看高评分目的地和路线灵感</small></span></Link>
          <Link to="/trip-planning?tab=map"><MapPinned size={18} /><span><strong>路线规划</strong><small>把攻略中的地点转成可执行路线</small></span></Link>
          <Link to="/themes"><MapPinned size={18} /><span><strong>主题旅行</strong><small>按兴趣继续筛选景区</small></span></Link>
        </section>

        <div className="guide-actions">
          <Link className="primary-btn" to="/destinations">查看目的地</Link>
          <Link className="ghost-btn" to="/rankings">探索热门榜单</Link>
        </div>
      </article>
    </>
  )
}
