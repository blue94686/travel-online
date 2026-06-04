import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Compass, User, Menu, X, LogOut, Settings, ChevronDown } from 'lucide-react'
import { useAuth } from '../../hooks/useAuth.jsx'

const navLinks = [
  { path: '/', label: '首页' },
  { path: '/destinations', label: '探索中国' },
  { path: '/themes', label: '主题旅行' },
  { path: '/trip-planning', label: '地图规划' },
  { path: '/earth-online', label: '地球Online' },
  { path: '/community', label: '游客社区' },
]

export default function Navbar() {
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const { user, isLoggedIn, isAdmin, logout } = useAuth()

  const isActive = (path) => {
    if (path === '/') return location.pathname === '/'
    return location.pathname.startsWith(path)
  }

  return (
    <header className="site-nav">
      <Link to="/" className="brand">
        <div className="brand-mark"><Compass size={24} /></div>
        <div>
          <strong>Scenic Online</strong>
          <small>极客旅行引擎</small>
        </div>
      </Link>

      <nav className={mobileMenuOpen ? 'open' : ''} aria-label="主导航">
        {navLinks.map(link => (
          <Link key={link.path} to={link.path} className={isActive(link.path) ? 'active' : ''} aria-current={isActive(link.path) ? 'page' : undefined} onClick={() => setMobileMenuOpen(false)}>
            {link.label}
          </Link>
        ))}
      </nav>

      <div className="nav-actions">
        {isLoggedIn ? (
          <div className="nav-user-cluster">
            {isAdmin && <Link to="/admin" className="ghost-btn" style={{ fontSize: 13 }}>后台管理</Link>}
            <div className="nav-user-menu">
              <button className="icon-btn user-menu-trigger" type="button" aria-haspopup="menu" aria-expanded={userMenuOpen} aria-label="打开用户菜单" onClick={() => setUserMenuOpen(!userMenuOpen)}>
                <User size={18} />
                <span>{user?.nickname || '用户'}</span>
                <ChevronDown size={14} />
              </button>
              {userMenuOpen && (
                <div className="user-dropdown" role="menu">
                  <Link to="/user" role="menuitem" onClick={() => setUserMenuOpen(false)}><User size={16} /> 用户中心</Link>
                  <button type="button" role="menuitem" onClick={() => { logout(); setUserMenuOpen(false) }}><LogOut size={16} /> 退出登录</button>
                </div>
              )}
            </div>
          </div>
        ) : (
          <Link to="/auth" className="pill-btn primary-btn" style={{ padding: '0 16px' }}>登录 / 注册</Link>
        )}
        <button className="icon-btn mobile-menu-btn" type="button" aria-label={mobileMenuOpen ? '关闭导航菜单' : '打开导航菜单'} aria-expanded={mobileMenuOpen} onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
          {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </div>
    </header>
  )
}
