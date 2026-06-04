import { request } from './client.js'

const withDefaultLimit = (params = '') => {
  const query = new URLSearchParams(params.startsWith('?') ? params.slice(1) : params)
  if (!query.has('limit')) query.set('limit', '80')
  return `?${query.toString()}`
}

export const getScenicList = (params = '') => request(`/api/scenic${withDefaultLimit(params)}`, {}, 'scenicList')
export const getSyncedScenicList = (params = '') => request(`/api/scenic${withDefaultLimit(params)}`, {}, null)
export const getScenicDetail = (id) => request(`/api/scenic/${id}`, {}, 'scenicDetail')
export const getScenicProfile = (id) => request(`/api/scenic/${id}/profile`, {}, 'scenicDetail')
export const getScenicNearby = (id) => request(`/api/scenic/${id}/nearby`, {}, null)
export const searchScenic = (q) => request(`/api/scenic/search?q=${encodeURIComponent(q)}`, {}, 'scenicList')
export const getScenicThemes = () => request('/api/scenic/themes', {}, null)
export const getProvinces = () => request('/api/provinces', {}, 'provinces')
export const getScenicRegions = (params = '') => request(`/api/scenic/regions${params}`, {}, null)
export const getRegionProvinces = () => request('/api/regions/provinces', {}, null)
export const getRegionCities = (province) => request(`/api/regions/cities?province=${encodeURIComponent(province || '')}`, {}, null)
export const getRegionDistricts = (province, city) => request(`/api/regions/districts?province=${encodeURIComponent(province || '')}&city=${encodeURIComponent(city || '')}`, {}, null)
export const planRoute = (params = '') => request(`/api/routes/plan${params}`, {}, null)
