import { request } from './client.js'

export const getComments = () => request('/api/comments', {}, 'comments')
export const getScenicComments = (scenicId) => request(`/api/comments?scenic_id=${scenicId}`, {}, 'comments')
export const postComment = (payload) => request('/api/comments', { method: 'POST', body: JSON.stringify(payload) })
export const getCommunityPosts = (params = '') => request(`/api/community/posts${params}`, {}, 'comments')
export const postCommunityPost = (payload) => request('/api/community/posts', { method: 'POST', body: JSON.stringify(payload) })
export const likeCommunityPost = (id) => request(`/api/community/posts/${id}/like`, { method: 'POST' })
export const reportCommunityPost = (id) => request(`/api/community/posts/${id}/report`, { method: 'POST' })
export const getUserProfile = () => request('/api/user/profile', {}, null)
export const uploadImage = (payload) => {
  if (payload instanceof FormData) {
    return request('/api/uploads', { method: 'POST', body: payload, headers: {} })
  }
  return request('/api/uploads', { method: 'POST', body: JSON.stringify(payload) })
}
export const saveFavorite = (payload = {}) => request('/api/user/favorites', { method: 'POST', body: JSON.stringify(payload) })
export const getFavorites = () => request('/api/user/favorites', {}, null)
export const getTrips = () => request('/api/user/trips', {}, null)
export const getRoutes = () => request('/api/user/routes', {}, null)
export const saveUserRoute = (payload) => request('/api/user/routes', { method: 'POST', body: JSON.stringify(payload) })
export const exportTrip = (id) => request(`/api/user/export/trip/${id}`, {}, null)
export const exportRoute = (id, format = 'gpx') => request(`/api/user/export/route/${id}?format=${encodeURIComponent(format)}`, {}, null)
export const getWorkbenchLayout = () => request('/api/user/workbench-layout', {}, null)
export const saveWorkbenchLayout = (layout) => request('/api/user/workbench-layout', { method: 'PUT', body: JSON.stringify({ layout }) })
export const resetWorkbenchLayout = () => request('/api/user/workbench-layout/reset', { method: 'POST' })
export const publishWorkbenchLayout = () => request('/api/user/workbench-layout/publish', { method: 'POST' })
export const getWorkbenchLayoutVersions = () => request('/api/user/workbench-layout/versions', {}, null)
