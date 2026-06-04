import { useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { request } from '../../api/client.js'
import { getStaticMapPreview } from '../../api/map.js'

const CITY_POINTS = {
  杭州: { lng: 120.155, lat: 30.274 },
  杭州市: { lng: 120.155, lat: 30.274 },
  苏州: { lng: 120.585, lat: 31.299 },
  苏州市: { lng: 120.585, lat: 31.299 },
  黄山: { lng: 118.338, lat: 29.715 },
  北京: { lng: 116.407, lat: 39.904 },
  上海: { lng: 121.473, lat: 31.23 },
  成都: { lng: 104.066, lat: 30.572 },
  西安: { lng: 108.94, lat: 34.341 },
  桂林: { lng: 110.29, lat: 25.273 },
  张家界: { lng: 110.479, lat: 29.117 },
}

function fallbackPreview(city) {
  const key = Object.keys(CITY_POINTS).find(name => name.includes(city) || city.includes(name))
  const center = CITY_POINTS[key] || CITY_POINTS.苏州
  return {
    city: city || key || '苏州',
    center,
    provider: 'OpenStreetMap',
    source: '真实地图',
  }
}

function buildPreviewBackground(provider) {
  const grid = encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
      <rect width="640" height="360" fill="#edf7f4"/>
      <path d="M0 88H640M0 176H640M0 264H640M88 0V360M176 0V360M264 0V360M352 0V360M440 0V360M528 0V360" stroke="#c8ded9" stroke-width="2"/>
      <path d="M-20 250C100 210 150 115 275 145C380 170 430 245 660 170" fill="none" stroke="#f4bd55" stroke-width="12" stroke-linecap="round"/>
      <path d="M70 15C135 90 160 175 250 235C335 292 445 305 590 330" fill="none" stroke="#7eb7d8" stroke-width="8" stroke-linecap="round"/>
      <path d="M110 310C150 235 220 205 310 205C415 205 485 115 555 60" fill="none" stroke="#86cfa9" stroke-width="7" stroke-linecap="round"/>
      <circle cx="320" cy="180" r="15" fill="#3e9f92"/>
      <circle cx="320" cy="180" r="42" fill="none" stroke="#3e9f92" stroke-width="5" opacity=".25"/>
      <text x="24" y="334" fill="#2f615b" font-size="18" font-family="Arial, sans-serif">${provider}</text>
    </svg>
  `)
  return `url("data:image/svg+xml,${grid}")`
}

function buildOsmEmbedUrl(center) {
  const lng = Number(center?.lng)
  const lat = Number(center?.lat)
  const safeLng = Number.isFinite(lng) ? lng : 120.585
  const safeLat = Number.isFinite(lat) ? lat : 31.299
  const deltaLng = 0.08
  const deltaLat = 0.05
  const params = new URLSearchParams({
    bbox: `${safeLng - deltaLng},${safeLat - deltaLat},${safeLng + deltaLng},${safeLat + deltaLat}`,
    layer: 'mapnik',
    marker: `${safeLat},${safeLng}`,
  })
  return `https://www.openstreetmap.org/export/embed.html?${params.toString()}`
}

function buildSatellitePreviewUrl(center) {
  const lng = Number(center?.lng)
  const lat = Number(center?.lat)
  const safeLng = Number.isFinite(lng) ? lng : 120.585
  const safeLat = Number.isFinite(lat) ? lat : 31.299
  const deltaLng = 0.08
  const deltaLat = 0.05
  const params = new URLSearchParams({
    bbox: `${safeLng - deltaLng},${safeLat - deltaLat},${safeLng + deltaLng},${safeLat + deltaLat}`,
    bboxSR: '4326',
    imageSR: '4326',
    size: '960,540',
    format: 'jpg',
    f: 'image',
  })
  return `https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/export?${params.toString()}`
}

const TILE_SIZE = 256

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function lngLatToTile(center, zoom) {
  const lng = Number(center?.lng)
  const lat = Number(center?.lat)
  const safeLng = Number.isFinite(lng) ? lng : 120.585
  const safeLat = clamp(Number.isFinite(lat) ? lat : 31.299, -85.0511, 85.0511)
  const latRad = safeLat * Math.PI / 180
  const scale = 2 ** zoom
  return {
    x: (safeLng + 180) / 360 * scale,
    y: (1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2 * scale,
  }
}

function tileUrl(layer, x, y, zoom) {
  if (layer === 'satellite') {
    return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${zoom}/${y}/${x}`
  }
  return `https://tile.openstreetmap.org/${zoom}/${x}/${y}.png`
}

function buildTiles(center, zoom, layer, compact) {
  const point = lngLatToTile(center, zoom)
  const centerX = Math.floor(point.x)
  const centerY = Math.floor(point.y)
  const scale = 2 ** zoom
  const radiusX = compact ? 2 : 3
  const radiusY = compact ? 2 : 3
  const tiles = []

  for (let dx = -radiusX; dx <= radiusX; dx += 1) {
    for (let dy = -radiusY; dy <= radiusY; dy += 1) {
      const rawX = centerX + dx
      const rawY = centerY + dy
      const x = ((rawX % scale) + scale) % scale
      const y = clamp(rawY, 0, scale - 1)
      tiles.push({
        key: `${zoom}-${x}-${y}`,
        src: tileUrl(layer, x, y, zoom),
        left: (rawX - point.x) * TILE_SIZE,
        top: (rawY - point.y) * TILE_SIZE,
      })
    }
  }
  return tiles
}

function InteractiveTileMap({ center, city, compact, layer, zoom }) {
  const tiles = useMemo(() => buildTiles(center, zoom, layer, compact), [center, zoom, layer, compact])
  const isSatellite = layer === 'satellite'
  return (
    <div className={`interactive-tile-map osm-map-frame ${isSatellite ? 'satellite-map-frame' : ''}`}>
      <div className="map-tile-stage" style={{ '--tile-size': `${TILE_SIZE}px` }}>
        {tiles.map(tile => (
          <img
            key={tile.key}
            src={tile.src}
            alt=""
            draggable="false"
            style={{ transform: `translate(calc(-50% + ${tile.left}px), calc(-50% + ${tile.top}px))` }}
          />
        ))}
      </div>
      {isSatellite && (
        <>
          <div className="satellite-contour-overlay" />
          <div className="satellite-raster-labels">
            <span>World Imagery</span>
            <span>Terrain + POI</span>
          </div>
        </>
      )}
      <span className="tile-map-marker">{city || '地图中心'}</span>
    </div>
  )
}

export default function MapPanel({ title = '', compact = false, startPoint, endPoint, layer = 'standard', city = '苏州', actionTo = '' }) {
  const mapContainerRef = useRef(null)
  const mapInstanceRef = useRef(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [preview, setPreview] = useState(() => fallbackPreview(city))
  const [mapReady, setMapReady] = useState(false)
  const [fallbackZoom, setFallbackZoom] = useState(compact ? 11 : 12)
  const previewBackground = useMemo(() => buildPreviewBackground(preview?.source || preview?.provider || '后端地图预览'), [preview])
  const osmEmbedUrl = useMemo(() => buildOsmEmbedUrl(preview?.center), [preview])
  const satellitePreviewUrl = useMemo(() => buildSatellitePreviewUrl(preview?.center), [preview])

  const zoomIn = () => {
    if (mapInstanceRef.current?.zoomIn) {
      mapInstanceRef.current.zoomIn()
      return
    }
    setFallbackZoom(value => clamp(value + 1, 3, 18))
  }

  const zoomOut = () => {
    if (mapInstanceRef.current?.zoomOut) {
      mapInstanceRef.current.zoomOut()
      return
    }
    setFallbackZoom(value => clamp(value - 1, 3, 18))
  }

  useEffect(() => {
    let isMounted = true

    const initMap = async () => {
      if (!mapContainerRef.current) return
      if (isMounted) setPreview(fallbackPreview(city))

      try {
        const [config, previewData] = await Promise.all([
          request('/api/map/config'),
          getStaticMapPreview(city),
        ])
        if (isMounted && previewData) setPreview(previewData)

        if (!config?.amap_js_key) {
          setLoading(false)
          setMapReady(false)
          return
        }

        if (!window.AMap) {
          await new Promise((resolve, reject) => {
            window._AMapSecurityConfig = {
              securityJsCode: config.amap_security_code || ''
            }
            const script = document.createElement('script')
            script.src = `https://webapi.amap.com/maps?v=2.0&key=${config.amap_js_key}&plugin=AMap.Driving`
            script.async = true
            script.onload = resolve
            script.onerror = () => reject(new Error('高德地图 SDK 加载失败'))
            document.body.appendChild(script)
          })
        }

        if (!isMounted) return

        if (!mapInstanceRef.current) {
          const center = previewData?.center
          mapInstanceRef.current = new window.AMap.Map(mapContainerRef.current, {
            zoom: 11,
            center: center?.lng && center?.lat ? [center.lng, center.lat] : [120.585, 31.299],
            viewMode: '3D'
          })
        }
        
        setMapReady(true)
        setLoading(false)

      } catch (err) {
        if (isMounted) {
          let errorMsg = err.message
          if (errorMsg.includes('USERKEY_PLAT_NOMATCH')) {
            errorMsg = '高德地图 Key 类型不匹配。请在后台配置 [高德地图前端 JS API]，而不是 Web 服务 Key。'
          }
          setError(errorMsg)
          setMapReady(false)
          setLoading(false)
        }
      }
    }

    initMap()

    // Handle global AMap errors
    window.onerror = function(message, source, lineno, colno, error) {
      if (message && message.toString().includes('USERKEY_PLAT_NOMATCH')) {
        setError('高德地图 Key 类型不匹配。请在后台配置 [高德地图前端 JS API]，而不是 Web 服务 Key。')
      }
    }

    return () => {
      isMounted = false
      if (mapInstanceRef.current) {
        mapInstanceRef.current.destroy()
        mapInstanceRef.current = null
      }
    }
  }, [city])

  // Handle Layer change
  useEffect(() => {
    if (!mapInstanceRef.current || !window.AMap) return
    const map = mapInstanceRef.current
    if (layer === 'satellite') {
      const satellite = new window.AMap.TileLayer.Satellite()
      map.setLayers([satellite])
    } else {
      map.setLayers([new window.AMap.TileLayer()])
    }
  }, [layer, loading])

  if (error) {
    return (
      <section className={`map-panel ${compact ? 'compact' : ''}`}>
        <div className="map-toolbar">
          <strong>{title || '地图区域'}</strong>
        </div>
        <div className="map-canvas" style={{display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f8f9fa'}}>
          <p style={{color: 'var(--color-muted)'}}>地图加载失败: {error}</p>
        </div>
      </section>
    )
  }

  return (
    <section className={`map-panel ${compact ? 'compact' : ''}`} style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {title && (
        <div className="map-toolbar">
          <strong>{title}</strong>
        </div>
      )}
      <div 
        ref={mapContainerRef} 
        className="map-canvas" 
        style={{
          flex: 1,
          width: '100%',
          minHeight: compact ? '200px' : '400px',
          background: '#e5e3df',
          backgroundImage: previewBackground,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          position: 'relative'
        }}
      >
        {loading && !preview?.center && <div style={{position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', zIndex: 3}}>加载地图中...</div>}
        {!mapReady && preview?.center && (
          <InteractiveTileMap
            center={preview.center}
            city={preview?.city || city}
            compact={compact}
            layer={layer}
            zoom={fallbackZoom}
          />
        )}
        {!mapReady && (
          <div className="map-provider-badge">
            {preview?.city || city} · {layer === 'satellite' ? 'ArcGIS World Imagery 卫星影像' : 'OpenStreetMap 真实地图'}
          </div>
        )}
        <div className="map-zoom-controls" aria-label="地图缩放">
          <button type="button" aria-label="放大地图" onClick={zoomIn}>+</button>
          <button type="button" aria-label="缩小地图" onClick={zoomOut}>−</button>
          {!mapReady && <span>{fallbackZoom}</span>}
        </div>
        {!mapReady && (
          <div className="map-scale-ruler">
            <span />
            <b>{fallbackZoom >= 14 ? '500 m' : fallbackZoom >= 12 ? '2 km' : '10 km'}</b>
          </div>
        )}
        {actionTo && (
          <Link className="map-card-cover" to={actionTo} aria-label={`${title || '地图'}跳转到地图规划`} />
        )}
        {actionTo && (
          <Link className="map-open-link" to={actionTo}>
            打开地图规划
          </Link>
        )}
        {startPoint && endPoint && (
          <>
            <div className="route-line" />
            <span className="map-stop one">起</span>
            <span className="map-stop three">终</span>
          </>
        )}
      </div>
    </section>
  )
}
