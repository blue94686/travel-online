import { lazy, Suspense } from 'react'
import { Navigate, useLocation, useParams } from 'react-router-dom'
import { createBrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import PageShell from './components/common/PageShell.jsx'
import AdminLayout from './components/admin/AdminLayout.jsx'
import { useAuth } from './hooks/useAuth.jsx'
import { SkeletonList } from './components/common/Skeleton.jsx'

// Public Pages (Lazy)
const HomePage = lazy(() => import('./pages/HomePage.jsx'))
const DestinationsPage = lazy(() => import('./pages/DestinationsPage.jsx'))
const ThemesPage = lazy(() => import('./pages/ThemesPage.jsx'))
const ProvinceDetailPage = lazy(() => import('./pages/ProvinceDetailPage.jsx'))
const ScenicDetailPage = lazy(() => import('./pages/ScenicDetailPage.jsx'))
const TripPlanningPage = lazy(() => import('./pages/TripPlanningPage.jsx'))
const CommunityPage = lazy(() => import('./pages/CommunityPage.jsx'))
const UserCenterPage = lazy(() => import('./pages/UserCenterPage.jsx'))
const AuthPage = lazy(() => import('./pages/AuthPage.jsx'))
const EarthOnlinePage = lazy(() => import('./pages/EarthOnlinePage.jsx'))
const SearchPage = lazy(() => import('./pages/SearchPage.jsx'))
const SourcesPage = lazy(() => import('./pages/SourcesPage.jsx'))
const RankingsPage = lazy(() => import('./pages/RankingsPage.jsx'))
const GuideDetailPage = lazy(() => import('./pages/GuideDetailPage.jsx'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage.jsx'))

// Admin Pages (Lazy)
const AdminOperationsPage = lazy(() => import('./pages/admin/AdminOperationsPage.jsx'))
const AdminContentPage = lazy(() => import('./pages/admin/AdminContentPage.jsx'))
const AdminAutomationPage = lazy(() => import('./pages/admin/AdminAutomationPage.jsx'))
const AdminIntegrationPage = lazy(() => import('./pages/admin/AdminIntegrationPage.jsx'))
const AdminApiPage = lazy(() => import('./pages/admin/AdminApiPage.jsx'))
const AdminDataPage = lazy(() => import('./pages/admin/AdminDataPage.jsx'))
const AdminWebEnrichmentPage = lazy(() => import('./pages/admin/AdminWebEnrichmentPage.jsx'))
const AdminEarthOnlinePage = lazy(() => import('./pages/admin/AdminEarthOnlinePage.jsx'))
const AdminSystemPage = lazy(() => import('./pages/admin/AdminSystemPage.jsx'))
const AdminLayoutPage = lazy(() => import('./pages/admin/AdminLayoutPage.jsx'))
const AdminDatabasePage = lazy(() => import('./pages/admin/AdminDatabasePage.jsx'))

// Route Guards
function ProtectedRoute({ children, requireAdmin = false }) {
  const { isLoggedIn, isAdmin } = useAuth()
  if (!isLoggedIn) return <Navigate to="/auth" replace />
  if (requireAdmin && !isAdmin) return <Navigate to="/" replace />
  return children
}

function LegacyRedirect({ to }) {
  const location = useLocation()
  const joiner = to.includes('?') ? '&' : '?'
  return <Navigate to={`${to}${location.search ? `${joiner}${location.search.slice(1)}` : ''}${location.hash || ''}`} replace />
}

function LegacyProvinceRedirect() {
  const location = useLocation()
  const { province = '' } = useParams()
  return <Navigate to={`/provinces/${encodeURIComponent(province)}${location.search || ''}${location.hash || ''}`} replace />
}

// Suspense Wrapper
const withSuspense = (Component) => (
  <Suspense fallback={<div style={{ padding: 40 }}><SkeletonList count={3} /></div>}>
    <Component />
  </Suspense>
)

export const router = createBrowserRouter([
  {
    path: '/',
    element: <App />,
    children: [
      {
        element: <PageShell />,
        children: [
          { index: true, element: withSuspense(HomePage) },
          { path: 'search', element: withSuspense(SearchPage) },
          { path: 'destinations', element: withSuspense(DestinationsPage) },
          { path: 'themes', element: withSuspense(ThemesPage) },
          { path: 'themes/:slug', element: withSuspense(ThemesPage) },
          { path: 'provinces', element: withSuspense(ProvinceDetailPage) },
          { path: 'provinces/:province', element: withSuspense(ProvinceDetailPage) },
          { path: 'province', element: <LegacyRedirect to="/provinces" /> },
          { path: 'province/:province', element: <LegacyProvinceRedirect /> },
          { path: 'scenic/:id', element: withSuspense(ScenicDetailPage) },
          { path: 'map', element: <LegacyRedirect to="/trip-planning?tab=map" /> },
          { path: 'weather', element: <LegacyRedirect to="/trip-planning?tab=weather" /> },
          { path: 'trip-planning', element: withSuspense(TripPlanningPage) },
          { path: 'community', element: withSuspense(CommunityPage) },
          { path: 'earth-online', element: withSuspense(EarthOnlinePage) },
          { path: 'sources', element: withSuspense(SourcesPage) },
          { path: 'rankings', element: withSuspense(RankingsPage) },
          { path: 'guides/:id', element: withSuspense(GuideDetailPage) },
          { path: 'user', element: <ProtectedRoute>{withSuspense(UserCenterPage)}</ProtectedRoute> },
          { path: 'auth', element: withSuspense(AuthPage) },
          { path: '*', element: withSuspense(NotFoundPage) }
        ]
      },
      {
        path: 'admin',
        element: <ProtectedRoute requireAdmin><AdminLayout /></ProtectedRoute>,
        children: [
          { index: true, element: withSuspense(AdminOperationsPage) },
          { path: 'scenic', element: withSuspense(AdminDatabasePage) },
          { path: 'images', element: withSuspense(AdminContentPage) },
          { path: 'comments', element: withSuspense(AdminContentPage) },
          { path: 'users', element: withSuspense(AdminSystemPage) },
          { path: 'data', element: withSuspense(AdminDataPage) },
          { path: 'data/source', element: withSuspense(AdminDataPage) },
          { path: 'data/quality', element: withSuspense(AdminDataPage) },
          { path: 'api', element: withSuspense(AdminApiPage) },
          { path: 'services', element: withSuspense(AdminSystemPage) },
          { path: 'earth-online', element: withSuspense(AdminEarthOnlinePage) },
          { path: 'enrichment', element: withSuspense(AdminDataPage) },
          { path: 'web-enrichment', element: withSuspense(AdminWebEnrichmentPage) },
          { path: 'workbench', element: withSuspense(AdminLayoutPage) },
          { path: 'roles', element: withSuspense(AdminSystemPage) },
          { path: 'security', element: withSuspense(AdminSystemPage) },
          { path: 'settings', element: withSuspense(AdminSystemPage) },
          { path: 'logs', element: withSuspense(AdminSystemPage) },
          { path: 'content', element: withSuspense(AdminContentPage) },
          { path: 'automation', element: withSuspense(AdminAutomationPage) },
          { path: 'integration', element: withSuspense(AdminIntegrationPage) },
          { path: 'system', element: withSuspense(AdminSystemPage) },
          { path: 'layout', element: withSuspense(AdminLayoutPage) },
          { path: 'database', element: withSuspense(AdminDatabasePage) },
          { path: '*', element: withSuspense(NotFoundPage) }
        ]
      }
    ]
  }
])
