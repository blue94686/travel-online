import { request } from './client.js'

export const getPublicLayout = (pageKey) => request(`/api/layouts/${pageKey}`, {}, 'layout')
export const getBanners = () => request('/api/content/banners', {}, 'banners')
export const getArticles = (category = '') => request(`/api/content/articles?category=${encodeURIComponent(category)}`, {}, 'articles')
export const getArticle = (id) => request(`/api/content/articles/${encodeURIComponent(id)}`, {}, null)
