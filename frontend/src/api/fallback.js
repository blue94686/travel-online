export const imageFallback = '/images/hero-mountain-lake.jpg'

// Province color mapping for gradient placeholders
const PROVINCE_COLORS = {
  '北京市': ['#E74C3C', '#C0392B'], '天津市': ['#3498DB', '#2980B9'], '上海市': ['#9B59B6', '#8E44AD'],
  '重庆市': ['#E67E22', '#D35400'], '河北省': ['#1ABC9C', '#16A085'], '山西省': ['#F39C12', '#E67E22'],
  '辽宁省': ['#E74C3C', '#C0392B'], '吉林省': ['#3498DB', '#2980B9'], '黑龙江省': ['#2ECC71', '#27AE60'],
  '江苏省': ['#9B59B6', '#8E44AD'], '浙江省': ['#0B9F8A', '#12B7A0'], '安徽省': ['#E67E22', '#D35400'],
  '福建省': ['#1ABC9C', '#16A085'], '江西省': ['#27AE60', '#229954'], '山东省': ['#F39C12', '#E67E22'],
  '河南省': ['#E74C3C', '#C0392B'], '湖北省': ['#3498DB', '#2980B9'], '湖南省': ['#E67E22', '#D35400'],
  '广东省': ['#E74C3C', '#C0392B'], '广西壮族自治区': ['#1ABC9C', '#16A085'], '海南省': ['#3498DB', '#2980B9'],
  '四川省': ['#E67E22', '#D35400'], '贵州省': ['#9B59B6', '#8E44AD'], '云南省': ['#2ECC71', '#27AE60'],
  '西藏自治区': ['#3498DB', '#2980B9'], '陕西省': ['#E74C3C', '#C0392B'], '甘肃省': ['#F39C12', '#E67E22'],
  '青海省': ['#3498DB', '#2980B9'], '内蒙古自治区': ['#2ECC71', '#27AE60'], '宁夏回族自治区': ['#F39C12', '#E67E22'],
  '新疆维吾尔自治区': ['#E67E22', '#D35400'], '香港特别行政区': ['#9B59B6', '#8E44AD'],
  '澳门特别行政区': ['#E74C3C', '#C0392B'], '台湾省': ['#3498DB', '#2980B9'],
}

// Simple hash for consistent color
function hashStr(str) {
  let h = 0
  for (let i = 0; i < str.length; i++) h = ((h << 5) - h + str.charCodeAt(i)) | 0
  return Math.abs(h)
}

const FALLBACK_PALETTES = [
  ['#667eea', '#764ba2'], ['#f093fb', '#f5576c'], ['#4facfe', '#00f2fe'],
  ['#43e97b', '#38f9d7'], ['#fa709a', '#fee140'], ['#a18cd1', '#fbc2eb'],
  ['#fccb90', '#d57eeb'], ['#e0c3fc', '#8ec5fc'], ['#f5576c', '#ff6b6b'],
  ['#0B9F8A', '#38BDF8'],
]

export function getScenicImage(scenic) {
  if (!scenic) return imageFallback
  if (scenic.cover_image_url && scenic.cover_image_url.startsWith('http')) return scenic.cover_image_url
  if (scenic.gallery && scenic.gallery.length > 0 && scenic.gallery[0]) return scenic.gallery[0]
  return null // caller should use getScenicPlaceholder
}

export function getScenicPlaceholder(scenic) {
  const name = scenic?.name || '景区'
  const province = scenic?.province || ''
  const colors = PROVINCE_COLORS[province] || ['#2F7D73', '#8BC7B5']
  const initial = name.charAt(0)
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="520" height="320" viewBox="0 0 520 320">
    <defs>
      <linearGradient id="sky" x1="0%" y1="0%" x2="0%" y2="100%"><stop offset="0%" stop-color="#E9F8F5"/><stop offset="100%" stop-color="#CDEDE6"/></linearGradient>
      <linearGradient id="mountain" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" stop-color="${colors[0]}"/><stop offset="100%" stop-color="${colors[1]}"/></linearGradient>
    </defs>
    <rect width="520" height="320" fill="url(#sky)"/>
    <circle cx="410" cy="72" r="34" fill="#F4C95D" opacity=".76"/>
    <path d="M0 232L90 130L164 214L245 96L354 232Z" fill="url(#mountain)" opacity=".92"/>
    <path d="M160 232L270 128L338 205L404 148L520 244V320H0V250Z" fill="#0F766E" opacity=".82"/>
    <path d="M0 260C94 232 145 264 230 242C319 219 404 235 520 207V320H0Z" fill="#FFFFFF" opacity=".28"/>
    <circle cx="72" cy="66" r="28" fill="rgba(255,255,255,.86)"/>
    <text x="72" y="77" text-anchor="middle" fill="#0F766E" font-family="PingFang SC,sans-serif" font-size="30" font-weight="800">${initial}</text>
    <rect x="30" y="238" width="460" height="48" rx="16" fill="rgba(255,255,255,.78)"/>
    <text x="52" y="267" fill="#12312D" font-family="PingFang SC,sans-serif" font-size="18" font-weight="700">${name.length > 18 ? name.substring(0, 18) + '…' : name}</text>
    <text x="408" y="267" text-anchor="end" fill="#5F7470" font-family="PingFang SC,sans-serif" font-size="13">${province || '景区图片待补全'}</text>
  </svg>`
  return `data:image/svg+xml,${encodeURIComponent(svg)}`
}

export function getScenicImageOrPlaceholder(scenic) {
  return getScenicImage(scenic) || getScenicPlaceholder(scenic)
}

export function getScenicGalleryImages(scenic, { includePlaceholder = true } = {}) {
  const images = [
    scenic?.cover_image_url,
    ...((Array.isArray(scenic?.gallery) ? scenic.gallery : []) || []),
  ].filter(image => typeof image === 'string' && image.startsWith('http'))
  const unique = Array.from(new Set(images)).slice(0, 8)
  if (unique.length > 0) return unique
  return includePlaceholder ? [getScenicPlaceholder(scenic)] : []
}
