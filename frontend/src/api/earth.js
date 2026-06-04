import { request } from './client.js'

export const getEarthSources = (params = '') => request(`/api/earth-online/sources${params}`, {}, 'earthSources')
export const getEarthCategories = () => request('/api/earth-online/categories', {}, 'earthCategories')
export const getEarthStats = () => request('/api/earth-online/stats', {}, 'earthStats')
export const getEarthFeatured = () => request('/api/earth-online/featured', {}, 'earthSources')
export const getEarthFavorites = () => request('/api/user/earth-online/favorites', {}, null)
export const saveEarthFavorite = (sourceId) => request('/api/user/earth-online/favorites', { method: 'POST', body: JSON.stringify({ source_id: sourceId }) })
export const removeEarthFavorite = (sourceId) => request(`/api/user/earth-online/favorites/${sourceId}`, { method: 'DELETE' })
