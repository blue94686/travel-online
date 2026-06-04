import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'

export default function NotFoundPage() {
  return (
    <div className="not-found-page">
      <div className="not-found-content">
        <Compass size={64} className="not-found-icon" />
        <h1>404</h1>
        <h2>迷路了吗？</h2>
        <p>你访问的页面似乎不存在，或者正在建设中。</p>
        <Link to="/" className="primary-btn">返回推荐首页</Link>
      </div>
    </div>
  )
}
