import { request } from './client.js'

export const getWeather = (city = '杭州') => request(`/api/weather?city=${encodeURIComponent(city)}`, {}, 'weather')
export const getLive = () => request('/api/live', {}, 'live')
export const getWeatherForecast = (city = '杭州') => request(`/api/weather/forecast?city=${encodeURIComponent(city)}`, {}, null)
export const getWeatherLive = (city = '杭州') => request(`/api/weather/live?city=${encodeURIComponent(city)}`, {}, 'live')
export const getRouteWeather = (cities = []) => request(`/api/weather/route?cities=${encodeURIComponent(cities.join(','))}`, {}, null)
