import assert from 'node:assert/strict'
import { getScenicGalleryImages } from '../src/api/fallback.js'

const missing = getScenicGalleryImages({ name: '北京八达岭国家森林公园', province: '北京市', gallery: [] })
assert.equal(missing.length, 1)
assert.equal(missing[0].startsWith('data:image/svg+xml,'), true)

const real = getScenicGalleryImages({
  cover_image_url: 'https://example.com/cover.jpg',
  gallery: ['https://example.com/cover.jpg', 'https://example.com/side.jpg'],
})
assert.deepEqual(real, ['https://example.com/cover.jpg', 'https://example.com/side.jpg'])

console.log('scenicGalleryFallback tests passed')
