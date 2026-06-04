export const regionOptions = {
  '': {
    cities: [''],
    districts: ['']
  },
  '四川省': {
    cities: ['成都市', '阿坝藏族羌族自治州', '乐山市', '甘孜藏族自治州'],
    districts: ['九寨沟县', '汶川县', '都江堰市', '峨眉山市']
  },
  '浙江省': {
    cities: ['杭州市', '宁波市', '温州市', '湖州市', '舟山市'],
    districts: ['西湖区', '普陀区', '安吉县', '雁荡山']
  },
  '江苏省': {
    cities: ['南京市', '苏州市', '无锡市', '扬州市'],
    districts: ['玄武区', '姑苏区', '滨湖区', '广陵区']
  },
  '云南省': {
    cities: ['昆明市', '丽江市', '大理白族自治州', '迪庆藏族自治州'],
    districts: ['石林彝族自治县', '古城区', '大理市', '香格里拉市']
  }
}

export const themes = ['全部', '自然风光', '人文古迹', '亲子乐园', '徒步登山', '红色旅游', '摄影打卡', '夜游景观']

export function readScenicState(search) {
  const params = new URLSearchParams(search)
  return {
    keyword: params.get('keyword') || params.get('q') || '',
    filters: {
      province: params.get('province') || '',
      city: params.get('city') || '',
      district: params.get('district') || '',
      theme: params.get('theme') || ''
    }
  }
}

export function scenicParams(keyword, filters) {
  const params = new URLSearchParams()
  const value = (keyword || '').trim()
  if (value) {
    params.set('keyword', value)
    params.set('amap', '1')
  }
  Object.entries(filters || {}).forEach(([key, item]) => {
    if (item) params.set(key, item)
  })
  return params
}

export function scopedOptions(province) {
  const config = regionOptions[province] || regionOptions['']
  return {
    provinces: Object.keys(regionOptions).filter(Boolean),
    cities: config.cities.filter(Boolean),
    districts: config.districts.filter(Boolean)
  }
}

export function normalizeFilterChange(current, key, value) {
  const nextValue = value === '全部' || current[key] === value ? '' : value
  const next = { ...current, [key]: nextValue }
  if (key === 'province') {
    next.city = ''
    next.district = ''
  }
  if (key === 'city') next.district = ''
  return next
}

export function locationTitle(filters) {
  const parts = [filters.province, filters.city, filters.district].filter(Boolean)
  return parts.length ? parts.join(' · ') : '全国景点'
}

export function nearbyDistricts(items, currentDistrict = '') {
  const values = Array.from(new Set((items || []).map(item => item.district).filter(Boolean)))
  return values.filter(item => item !== currentDistrict).slice(0, 3)
}

export function popularProvinces(items) {
  return Array.from(new Set((items || []).map(item => item.province).filter(Boolean))).slice(0, 4)
}
