import { request } from './client.js'

export const reverseLocation = (lat, lng) => request(`/api/location/reverse?lat=${encodeURIComponent(lat)}&lng=${encodeURIComponent(lng)}`, {}, null)
export const getIpLocation = () => request('/api/location/ip', {}, null)
