import { Link } from 'react-router-dom'
import { Compass } from 'lucide-react'
import './Footer.css'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-grid">
        <div className="footer-brand">
          <div className="brand-mark"><Compass size={22} /></div>
          <strong>Scenic Online</strong>
          <p>极客旅行引擎，覆盖全国省市县三级景区数据，提供智能行程规划、实时天气与地图路线服务。</p>
        </div>
        <div className="footer-col">
          <h4>探索</h4>
          <Link to="/destinations">景区推荐</Link>
          <Link to="/themes">主题旅行</Link>
          <Link to="/provinces">省份浏览</Link>
          <Link to="/earth-online">地球 Online</Link>
        </div>
        <div className="footer-col">
          <h4>功能</h4>
          <Link to="/trip-planning">行程规划</Link>
          <Link to="/community">游客社区</Link>
          <Link to="/user">用户中心</Link>
        </div>
        <div className="footer-col">
          <h4>关于</h4>
          <a href="#api">API 接口</a>
          <a href="#privacy">隐私政策</a>
          <a href="#terms">服务条款</a>
          <a href="#contact">联系我们</a>
        </div>
      </div>
      <div className="footer-bottom">
        <span>&copy; {new Date().getFullYear()} Scenic Online · 极客旅行引擎</span>
        <span>
          <a href="#icp">备案号占位</a>
          <a href="#github">GitHub</a>
        </span>
      </div>
    </footer>
  )
}
