import { ExternalLink, Database, Image, Cloud, Globe, Shield } from 'lucide-react'
import HeroSection from '../components/common/HeroSection.jsx'
import '../styles/sources.css'

const SOURCES = [
  {
    icon: Database,
    title: '景区数据',
    items: [
      { name: '全国景点种子数据', status: 'active', note: '基于 SQL 自建库，含 36 张表' },
      { name: '公开景区信息聚合', status: 'active', note: '携程/马蜂窝公开数据整理' },
      { name: '天气数据接口', status: 'active', note: '高德天气 / 和风天气 API（无 Key 时 fallback 静态数据）' },
    ]
  },
  {
    icon: Image,
    title: '图片资源',
    items: [
      { name: 'Unsplash 公开图库', status: 'active', note: 'unsplash.com — 免费高清图片', link: 'https://unsplash.com' },
      { name: 'Lucide 图标库', status: 'active', note: 'lucide.dev — MIT 开源图标', link: 'https://lucide.dev' },
    ]
  },
  {
    icon: Globe,
    title: '地图与地球',
    items: [
      { name: '高德地图 JS API', status: 'active', note: '用于路线规划与地图展示' },
      { name: 'EarthCam 公开直播', status: 'external', note: 'earthcam.com — 全球景点实时摄像头', link: 'https://www.earthcam.com' },
      { name: 'SkylineWebcams', status: 'external', note: 'skylinewebcams.com — 世界地标直播', link: 'https://www.skylinewebcams.com' },
    ]
  },
  {
    icon: Cloud,
    title: '天气与环境',
    items: [
      { name: '高德天气 API', status: 'active', note: '实况天气 + 7日预报' },
      { name: '和风天气 API', status: 'pending', note: '作为备选天气源（需配置 API Key）' },
      { name: 'Open-Meteo', status: 'external', note: 'open-meteo.com — 免费天气预报 API', link: 'https://open-meteo.com' },
    ]
  }
]

const STATUS_LABEL = {
  active: { text: '可使用', className: 'status-active' },
  pending: { text: '待配置', className: 'status-pending' },
  external: { text: '仅外链', className: 'status-external' },
}

export default function SourcesPage() {
  return (
    <div className="sources-page">
      <HeroSection
        variant="display"
        images={[
          'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1920&q=80',
        ]}
        title="数据来源"
        subtitle="公开透明，展示本项目使用的所有外部数据与资源"
      />

      <div className="sources-content">
        <div className="sources-grid">
          {SOURCES.map(group => {
            const Icon = group.icon
            return (
              <div className="source-card panel" key={group.title}>
                <div className="source-card-header">
                  <Icon size={22} />
                  <h3>{group.title}</h3>
                </div>
                <div className="source-list">
                  {group.items.map(item => {
                    const status = STATUS_LABEL[item.status] || STATUS_LABEL.active
                    return (
                      <div className="source-item" key={item.name}>
                        <div className="source-item-main">
                          <span className="source-name">{item.name}</span>
                          <span className={`source-status ${status.className}`}>{status.text}</span>
                        </div>
                        <div className="source-note">
                          {item.note}
                          {item.link && (
                            <a href={item.link} target="_blank" rel="noopener noreferrer" className="source-link">
                              <ExternalLink size={13} />
                            </a>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
        </div>

        <div className="disclaimer panel">
          <div className="disclaimer-header">
            <Shield size={20} />
            <h3>免责声明</h3>
          </div>
          <p>
            本项目仅供学习与演示使用。景区信息、天气数据等来源于公开接口，可能存在时效性差异。
            使用外部链接时请遵守相关网站的服务条款。
          </p>
        </div>
      </div>
    </div>
  )
}
