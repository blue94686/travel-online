import { useEffect, useMemo, useState } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import Navbar from './Navbar.jsx'
import { getPublicLayout } from '../../api/layouts.js'

const pageKeys = [
  ['earth-online', 'earth_online'],
  ['scenic', 'scenic'],
  ['themes', 'themes'],
  ['search', 'search'],
  ['destinations', 'destinations'],
  ['trip-planning', 'trip_planning'],
  ['map', 'map'],
  ['weather', 'weather'],
  ['community', 'community'],
  ['provinces', 'provinces'],
  ['auth', 'auth'],
  ['user', 'user_center'],
  ['sources', 'sources']
]

export default function PageShell() {
  const location = useLocation()
  const pageKey = useMemo(() => pageKeys.find(([path]) => location.pathname.includes(path))?.[1] || 'home', [location.pathname])
  const [layout, setLayout] = useState(null)
  useEffect(() => {
    getPublicLayout(pageKey).then(setLayout).catch(() => setLayout(null))
  }, [pageKey])
  return (
    <>
      <a className="skip-link" href="#main-content">跳到主内容</a>
      <Navbar />
      <main id="main-content" className="page" data-layout-page={pageKey} tabIndex={-1}><Outlet context={{ layout: layout?.layout, pageKey }} /></main>
    </>
  )
}
