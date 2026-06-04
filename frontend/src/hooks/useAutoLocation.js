import { useEffect, useState } from 'react'
import { getIpLocation, reverseLocation } from '../api/location.js'

const fallbackLocation = {
  province: '江苏省',
  city: '苏州市',
  district: '',
  label: '苏州 / 默认城市',
  status: 'fallback',
  message: '已使用默认城市苏州'
}

export default function useAutoLocation() {
  const [location, setLocation] = useState({ ...fallbackLocation, label: '自动定位中...', status: 'loading', message: '' })

  useEffect(() => {
    let mounted = true
    const applyFallback = async (message = '已使用默认城市苏州') => {
      const ipLocation = await getIpLocation()
      if (!mounted) return
      const city = ipLocation?.city || fallbackLocation.city
      setLocation({
        province: ipLocation?.province || fallbackLocation.province,
        city,
        district: ipLocation?.district || fallbackLocation.district,
        label: `${city.replace('市', '')} / ${ipLocation?.provider === 'amap' ? 'IP 定位' : '默认城市'}`,
        status: 'fallback',
        message
      })
    }

    if (!navigator.geolocation) {
      applyFallback('浏览器不支持定位，已使用默认城市苏州')
      return () => { mounted = false }
    }

    navigator.geolocation.getCurrentPosition(
      async position => {
        const data = await reverseLocation(position.coords.latitude, position.coords.longitude)
        if (!mounted) return
        const city = data?.city || fallbackLocation.city
        setLocation({
          province: data?.province || fallbackLocation.province,
          city,
          district: data?.district || fallbackLocation.district,
          lat: position.coords.latitude,
          lng: position.coords.longitude,
          label: `${city.replace('市', '')} / 当前定位`,
          status: 'success',
          message: ''
        })
      },
      () => applyFallback('已使用默认城市苏州'),
      { enableHighAccuracy: false, timeout: 3500, maximumAge: 10 * 60 * 1000 }
    )
    return () => { mounted = false }
  }, [])

  return location
}
