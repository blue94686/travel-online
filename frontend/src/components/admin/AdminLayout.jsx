import { useEffect, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import AdminSidebar from './AdminSidebar.jsx'
import AdminTopbar from './AdminTopbar.jsx'
import { getPublicLayout } from '../../api/layouts.js'

export default function AdminLayout() {
  const location = useLocation()
  const [layout, setLayout] = useState(null)
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('adminSidebarCollapsed') === '1')
  useEffect(() => {
    if (location.pathname === '/admin') getPublicLayout('admin_dashboard').then(setLayout).catch(() => setLayout(null))
  }, [location.pathname])
  const toggleCollapsed = () => {
    setCollapsed(value => {
      const next = !value
      localStorage.setItem('adminSidebarCollapsed', next ? '1' : '0')
      return next
    })
  }
  return (
    <main className={`admin-layout ${collapsed ? 'sidebar-collapsed' : ''}`}>
      <AdminSidebar collapsed={collapsed} onToggle={toggleCollapsed} />
      <section className="admin-main">
        <AdminTopbar />
        <div className="admin-content" data-layout-page={location.pathname === '/admin' ? 'admin_dashboard' : ''}><Outlet context={{ layout: layout?.layout, pageKey: 'admin_dashboard' }} /></div>
      </section>
    </main>
  )
}
