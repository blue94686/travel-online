import { request } from './client.js'

export const searchAll = (params = '') => request(`/api/search${params}`, {}, 'search')
export const getSearchSuggestions = (q) => request(`/api/search/suggestions?q=${encodeURIComponent(q)}`, {}, 'suggestions')
export const getHotSearches = (category = '', limit = 10) => request(`/api/search/hot?category=${category}&limit=${limit}`, {}, 'hotSearches')
export const getSearchHistory = () => request('/api/user/search-history', {}, 'searchHistory')
export const clearSearchHistory = () => request('/api/user/search-history', { method: 'DELETE' }, 'searchHistory')
