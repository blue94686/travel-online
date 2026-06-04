import assert from 'node:assert/strict'
import {
  locationTitle,
  nearbyDistricts,
  normalizeFilterChange,
  popularProvinces,
  readScenicState,
  scenicParams,
  scopedOptions
} from '../src/utils/scenicSync.js'

const state = readScenicState('?province=四川省&city=阿坝藏族羌族自治州&district=九寨沟县&keyword=瀑布')
assert.equal(state.keyword, '瀑布')
assert.deepEqual(state.filters, {
  province: '四川省',
  city: '阿坝藏族羌族自治州',
  district: '九寨沟县',
  theme: ''
})

const params = scenicParams('瀑布', state.filters)
assert.equal(params.get('province'), '四川省')
assert.equal(params.get('city'), '阿坝藏族羌族自治州')
assert.equal(params.get('district'), '九寨沟县')
assert.equal(params.get('amap'), '1')

assert.deepEqual(normalizeFilterChange(state.filters, 'province', '云南省'), {
  province: '云南省',
  city: '',
  district: '',
  theme: ''
})
assert.ok(scopedOptions('四川省').cities.includes('阿坝藏族羌族自治州'))
assert.equal(locationTitle(state.filters), '四川省 · 阿坝藏族羌族自治州 · 九寨沟县')
assert.deepEqual(nearbyDistricts([{ district: '九寨沟县' }, { district: '汶川县' }, { district: '都江堰市' }], '九寨沟县'), ['汶川县', '都江堰市'])
assert.deepEqual(popularProvinces([{ province: '四川省' }, { province: '云南省' }, { province: '四川省' }]), ['四川省', '云南省'])
