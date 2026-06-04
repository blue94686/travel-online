import { CloudSun } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function WeatherCard({ weather, to = '/trip-planning?tab=weather' }) {
  return (
    <Link className="tool-card weather-card-link" to={to}>
      <div className="card-title-row">
        <h3>景区天气</h3>
        <span className="inline-action">查看 7 日预报</span>
      </div>
      <div className="weather-main">
        <CloudSun size={48} />
        <strong>{weather?.temp || weather?.current?.temp || 24}°C</strong>
        <span>{weather?.condition || weather?.current?.condition || '多云'}</span>
      </div>
      <div className="compact-grid">
        <span>湿度 {weather?.current?.humidity || '68%'}</span>
        <span>空气 {weather?.air || weather?.current?.air || '优 32'}</span>
        <span>风力 {weather?.current?.wind || '东北风 2级'}</span>
      </div>
    </Link>
  )
}
