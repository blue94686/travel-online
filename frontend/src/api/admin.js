import { request } from './client.js'

export const getDashboard = () => request('/api/admin/dashboard', {}, 'dashboard')
export const getAdminScenic = (params = '') => request(`/api/admin/scenic${params}`, {}, 'scenicList')
export const createAdminScenic = (payload) => request('/api/admin/scenic', { method: 'POST', body: JSON.stringify(payload) })
export const updateAdminScenic = (id, payload) => request(`/api/admin/scenic/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteAdminScenic = (id) => request(`/api/admin/scenic/${id}`, { method: 'DELETE' })

export const getBanners = () => request('/api/admin/content/banners', {}, 'banners')
export const createBanner = (payload) => request('/api/admin/content/banners', { method: 'POST', body: JSON.stringify(payload) })
export const updateBanner = (id, payload) => request(`/api/admin/content/banners/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteBanner = (id) => request(`/api/admin/content/banners/${id}`, { method: 'DELETE' })

export const getArticles = () => request('/api/admin/content/articles', {}, 'articles')
export const createArticle = (payload) => request('/api/admin/content/articles', { method: 'POST', body: JSON.stringify(payload) })
export const updateArticle = (id, payload) => request(`/api/admin/content/articles/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteArticle = (id) => request(`/api/admin/content/articles/${id}`, { method: 'DELETE' })

export const getReviewImages = () => request('/api/admin/images/review', {}, 'reviewImages')
export const approveImage = (id) => request(`/api/admin/images/${id}/approve`, { method: 'POST' })
export const rejectImage = (id) => request(`/api/admin/images/${id}/reject`, { method: 'POST' })
export const coverImage = (id) => request(`/api/admin/images/${id}/cover`, { method: 'POST' })
export const deleteImage = (id) => request(`/api/admin/images/${id}`, { method: 'DELETE' })
export const getReviewComments = () => request('/api/admin/comments/review', {}, 'comments')
export const approveComment = (id) => request(`/api/admin/comments/${id}/approve`, { method: 'POST' })
export const hideComment = (id) => request(`/api/admin/comments/${id}/hide`, { method: 'POST' })
export const deleteComment = (id) => request(`/api/admin/comments/${id}`, { method: 'DELETE' })
export const addIpBlacklist = (payload) => request('/api/admin/security/ip-blacklist', { method: 'POST', body: JSON.stringify(payload) })
export const getAdminUsers = () => request('/api/admin/users', {}, 'adminUsers')
export const updateUserStatus = (id, status) => request(`/api/admin/users/${id}/status`, { method: 'PUT', body: JSON.stringify({ status }) })
export const updateUserRole = (id, role) => request(`/api/admin/users/${id}/role`, { method: 'PUT', body: JSON.stringify({ role }) })
export const resetDemoPassword = (id) => request(`/api/admin/users/${id}/reset-demo-password`, { method: 'POST' })
export const getApiConfig = () => request('/api/admin/api/config', {}, 'apiConfig')
export const saveApiConfig = (payload) => request('/api/admin/api/config', { method: 'PUT', body: JSON.stringify(payload) })
export const checkApiHealth = (provider = 'health-check') => request(`/api/admin/api/health-check/${encodeURIComponent(provider)}`, { method: 'POST' })
export const getApiLogs = () => request('/api/admin/api/logs', {}, 'apiLogs')
export const getRoles = () => request('/api/admin/roles', {}, 'roles')
export const saveRoles = (roles) => request('/api/admin/roles', { method: 'PUT', body: JSON.stringify({ roles }) })
export const getSecurityLogs = () => request('/api/admin/security/logs', {}, 'logs')
export const getIpBlacklist = () => request('/api/admin/security/ip-blacklist', {}, 'ipBlacklist')
export const removeIpBlacklist = (ip) => request(`/api/admin/security/ip-blacklist/${encodeURIComponent(ip)}`, { method: 'DELETE' })
export const getSettings = () => request('/api/admin/system/settings', {}, 'settings')
export const saveSettings = (payload) => request('/api/admin/system/settings', { method: 'PUT', body: JSON.stringify(payload) })
export const getAuditLogs = (params = '') => request(`/api/admin/logs${params}`, {}, 'logs')
export const triggerDataSync = () => request('/api/admin/data/sync', { method: 'POST' })
export const createDataBackup = () => request('/api/admin/data/backup', { method: 'POST' })
export const runQualityCheck = () => request('/api/admin/data/quality-check', { method: 'POST' })
export const getDatabaseStatus = () => request('/api/admin/database/status', {}, 'dbStatus')
export const getDatabaseOverview = () => request('/api/admin/database/overview', {}, null)
export const getDatabaseTable = (name, params = '') => request(`/api/admin/database/tables/${encodeURIComponent(name)}${params}`, {}, null)
export const getDatabaseFiles = () => request('/api/admin/database/files', {}, null)
export const executeSql = (sql) => request('/api/admin/database/query', { method: 'POST', body: JSON.stringify({ sql }) })
export const getServicesStatus = () => request('/api/admin/services/status', {}, 'servicesStatus')
export const checkService = (name) => request(`/api/admin/services/${encodeURIComponent(name)}/check`, { method: 'POST' })
export const getPageLayout = (scope) => request(`/api/admin/page-layouts/${encodeURIComponent(scope)}`, {}, null)
export const savePageLayout = (scope, layout, meta = {}) => request(`/api/admin/page-layouts/${encodeURIComponent(scope)}`, { method: 'PUT', body: JSON.stringify({ layout, ...meta }) })
export const publishPageLayout = (scope) => request(`/api/admin/page-layouts/${encodeURIComponent(scope)}/publish`, { method: 'POST' })
export const resetPageLayout = (scope) => request(`/api/admin/page-layouts/${encodeURIComponent(scope)}/reset`, { method: 'POST' })
export const getPageLayoutVersions = (scope) => request(`/api/admin/page-layouts/${encodeURIComponent(scope)}/versions`, {}, null)
export const previewPageLayout = (scope, layout) => request(`/api/admin/layouts/${encodeURIComponent(scope)}/preview`, { method: 'POST', body: JSON.stringify({ layout }) })
export const getComponentTemplates = (params = '') => request(`/api/admin/component-templates${params}`, {}, null)
export const saveComponentTemplate = (payload) => request('/api/admin/component-templates', { method: 'POST', body: JSON.stringify(payload) })
export const deleteComponentTemplate = (id) => request(`/api/admin/component-templates/${id}`, { method: 'DELETE' })
export const getScenicSqlStatus = () => request('/api/admin/data/scenic-sql/status', {}, null)
export const getJingdianSourceStatus = () => request('/api/admin/scenic-source/jingdian/status', {}, null)
export const importJingdianSource = (limit) => request(`/api/admin/scenic-source/jingdian/import${limit ? `?limit=${encodeURIComponent(limit)}` : ''}`, { method: 'POST' }, null)
export const previewScenicSqlImport = (limit = 5000, extra = {}) => {
  const query = new URLSearchParams({ limit: String(limit) })
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  return request(`/api/admin/data/scenic-sql/preview?${query.toString()}`, {}, null)
}
export const importScenicSql = (limit, extra = {}) => {
  const query = new URLSearchParams()
  if (limit) query.set('limit', String(limit))
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, value)
  })
  return request(`/api/admin/data/scenic-sql/import${query.toString() ? `?${query.toString()}` : ''}`, { method: 'POST' })
}
export const getEnrichmentOverview = () => request('/api/admin/enrichment/overview', {}, null)
export const getEnrichmentTasks = () => request('/api/admin/enrichment/tasks', {}, null)
export const getExternalEnrichmentReadiness = () => request('/api/admin/enrichment/profile/external-readiness', {}, null)
const toQuery = (extra = {}) => {
  const query = new URLSearchParams()
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  return query.toString()
}
export const runExternalEnrichmentBatch = (extra = {}) => {
  const query = new URLSearchParams()
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  return request(`/api/admin/enrichment/profile/external-batch${query.toString() ? `?${query.toString()}` : ''}`, { method: 'POST' }, null)
}
export const runTptMediaBatch = (extra = {}) => {
  const query = new URLSearchParams()
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  return request(`/api/admin/enrichment/tpt/media-batch${query.toString() ? `?${query.toString()}` : ''}`, { method: 'POST' }, null)
}
export const startTptMediaJob = (extra = {}) => {
  const query = new URLSearchParams()
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  return request(`/api/admin/enrichment/tpt/media-job/start${query.toString() ? `?${query.toString()}` : ''}`, { method: 'POST' }, null)
}
export const getTptMediaJobStatus = () => request('/api/admin/enrichment/tpt/media-job/status', {}, null)
export const getTptEnrichmentStats = () => request('/api/admin/enrichment/tpt/stats', {}, null)
export const stopTptMediaJob = () => request('/api/admin/enrichment/tpt/media-job/stop', { method: 'POST' }, null)
export const exportTptSourceSql = () => request('/api/admin/enrichment/tpt/export-sql', { method: 'POST' }, null)
export const runLocalProfileBatch = (extra = {}) => {
  const query = new URLSearchParams()
  Object.entries(extra).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') query.set(key, String(value))
  })
  return request(`/api/admin/enrichment/profile/local-batch${query.toString() ? `?${query.toString()}` : ''}`, { method: 'POST' }, null)
}
export const runCrawlerEnrichmentBatch = (extra = {}) => {
  const query = toQuery(extra)
  return request(`/api/admin/enrichment/crawler/batch${query ? `?${query}` : ''}`, { method: 'POST' }, null)
}
export const startCrawlerEnrichmentJob = (extra = {}) => {
  const query = toQuery(extra)
  return request(`/api/admin/enrichment/crawler/start${query ? `?${query}` : ''}`, { method: 'POST' }, null)
}
export const getCrawlerEnrichmentStatus = () => request('/api/admin/enrichment/crawler/status', {}, null)
export const stopCrawlerEnrichmentJob = () => request('/api/admin/enrichment/crawler/stop', { method: 'POST' }, null)
export const approveLowRiskCrawlerCandidates = (extra = {}) => {
  const query = toQuery(extra)
  return request(`/api/admin/enrichment/crawler/approve-low-risk${query ? `?${query}` : ''}`, { method: 'POST' }, null)
}
export const getWebEnrichmentOverview = () => request('/api/admin/web-enrichment/overview', {}, null)
export const getWebEnrichmentCandidates = (extra = {}) => {
  const query = toQuery(extra)
  return request(`/api/admin/web-enrichment/candidates${query ? `?${query}` : ''}`, {}, null)
}
export const getServiceLogs = (name) => request(`/api/admin/services/${encodeURIComponent(name)}/logs`, {}, null)
export const toggleService = (name) => request(`/api/admin/services/${encodeURIComponent(name)}/toggle`, { method: 'POST' })
export const getAdminEarthSources = (params = '') => request(`/api/admin/earth-online/sources${params}`, {}, null)
export const createAdminEarthSource = (payload) => request('/api/admin/earth-online/sources', { method: 'POST', body: JSON.stringify(payload) })
export const updateAdminEarthSource = (id, payload) => request(`/api/admin/earth-online/sources/${id}`, { method: 'PUT', body: JSON.stringify(payload) })
export const deleteAdminEarthSource = (id) => request(`/api/admin/earth-online/sources/${id}`, { method: 'DELETE' })
export const approveAdminEarthSource = (id) => request(`/api/admin/earth-online/sources/${id}/approve`, { method: 'POST' })
export const rejectAdminEarthSource = (id) => request(`/api/admin/earth-online/sources/${id}/reject`, { method: 'POST' })
export const disableAdminEarthSource = (id) => request(`/api/admin/earth-online/sources/${id}/disable`, { method: 'POST' })
export const checkAdminEarthSource = (id) => request(`/api/admin/earth-online/sources/${id}/check`, { method: 'POST' })
export const bulkCheckAdminEarthSources = () => request('/api/admin/earth-online/sources/bulk-check', { method: 'POST' })
