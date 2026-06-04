import { request } from './client.js'

export const geocodeAddress = (address) => request(`/api/map/geocode?address=${encodeURIComponent(address || '')}`, {}, null)
export const reverseGeocode = (lat, lng) => request(`/api/map/reverse-geocode?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`, {}, null)
export const getMapRoute = ({ origin, destination, mode = 'driving' }) => request(`/api/map/route?origin=${encodeURIComponent(origin)}&destination=${encodeURIComponent(destination)}&mode=${encodeURIComponent(mode)}`, {}, null)
export const getMapPoi = (keyword, city = '') => request(`/api/map/poi?keyword=${encodeURIComponent(keyword || '')}&city=${encodeURIComponent(city || '')}`, {}, null)
export const getStaticMapPreview = (city = '') => request(`/api/map/static-preview?city=${encodeURIComponent(city)}`, {}, null)
