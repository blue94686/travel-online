import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Bell, Camera, CheckCircle2, Copy, Eye, EyeOff, GripVertical, Heart, Lock, MapPinned, MessageSquare, Route, Settings, ShieldCheck, UserRound } from 'lucide-react'
import { exportTrip, getFavorites, getRoutes, getTrips, getUserProfile, getWorkbenchLayout, publishWorkbenchLayout, resetWorkbenchLayout, saveWorkbenchLayout } from '../api/user.js'
import { getScenicList } from '../api/scenic.js'
import { imageFallback } from '../api/fallback.js'
import UserStatsCard from '../components/common/UserStatsCard.jsx'

const menus = [
  ['用户中心', UserRound],
  ['我的行程', Route],
  ['我的收藏', Heart],
  ['我的评论', MessageSquare],
  ['我的图片', Camera],
  ['我的路线', MapPinned],
  ['账号安全', ShieldCheck],
  ['消息中心', Bell],
  ['账号设置', Settings],
  ['工作台编排', GripVertical]
]

const checklist = [
  ['装备准备', 10, 10],
  ['交通预订', 3, 3],
  ['住宿安排', 5, 6],
  ['景点门票', 2, 4],
  ['行程规划', 1, 1]
]

const defaultWorkbench = ['当前行程', '即将出发', '快捷入口', '最近浏览', '我的收藏', '行程清单', '足迹数据', '账号安全', '行程工具箱']
  .map((title, index) => ({ id: `user-${index + 1}`, title, visible: true, order: index }))

export default function UserCenterPage() {
  const navigate = useNavigate()
  const [active, setActive] = useState('用户中心')
  const [notice, setNotice] = useState('')
  const [profile, setProfile] = useState(null)
  const [trips, setTrips] = useState([])
  const [favorites, setFavorites] = useState([])
  const [routes, setRoutes] = useState([])
  const [scenic, setScenic] = useState([])
  const [workbench, setWorkbench] = useState(defaultWorkbench)
  const [dragIndex, setDragIndex] = useState(null)

  useEffect(() => {
    getUserProfile().then(setProfile)
    getTrips().then(data => setTrips(data || []))
    getFavorites().then(data => setFavorites(data || []))
    getRoutes().then(data => setRoutes(data || []))
    getScenicList().then(data => setScenic(Array.isArray(data) ? data : (data?.items || [])))
    getWorkbenchLayout().then(data => {
      const layout = data?.layout || data?.layout_json
      setWorkbench(layout?.modules?.length ? layout.modules : (Array.isArray(layout) && layout.length ? layout : defaultWorkbench))
    })
  }, [])

  const exportCurrentTrip = async (id) => {
    await exportTrip(id)
    setNotice('行程导出任务已生成')
  }

  const trip = trips[0] || { id: 1, title: '四川 · 四姑娘山徒步穿越', status: '进行中' }
  const scenicItems = Array.isArray(scenic) ? scenic : []
  const recent = scenicItems.slice(0, 4)
  const favoriteScenic = favorites.length ? favorites : scenicItems.slice(0, 4)
  const visible = (title) => workbench.find(item => item.title === title)?.visible !== false
  const moveWorkbench = (from, to) => {
    if (from === null || from === to) return
    setWorkbench(current => {
      const next = [...current]
      const [picked] = next.splice(from, 1)
      next.splice(to, 0, picked)
      return next.map((item, index) => ({ ...item, order: index }))
    })
  }
  const toggleWorkbench = (title) => setWorkbench(current => current.map(item => item.title === title ? { ...item, visible: !item.visible } : item))
  const copyWorkbenchModule = (item) => {
    const id = `${item.id}-copy-${Date.now()}`
    setWorkbench(current => [...current, { ...item, id, title: `${item.title} 副本`, order: current.length }])
    setNotice(`${item.title} 已复制`)
  }
  const updateWorkbenchWidth = (id, width) => setWorkbench(current => current.map(item => item.id === id ? { ...item, width } : item))
  const renderWorkbenchModule = (item, index) => {
    const width = item.width || (['当前行程', '即将出发', '快捷入口'].includes(item.title) ? 'third' : 'half')
    return (
      <article
        key={item.id}
        draggable
        onDragStart={() => setDragIndex(index)}
        onDragOver={event => event.preventDefault()}
        onDrop={() => moveWorkbench(dragIndex, index)}
        className={`user-compose-module width-${width} ${item.visible ? '' : 'muted'}`}
      >
        <div className="user-compose-toolbar">
          <span><GripVertical size={15} /> {item.title}</span>
          <div>
            <button type="button" onClick={() => toggleWorkbench(item.title)}>{item.visible ? <Eye size={15} /> : <EyeOff size={15} />}</button>
            <button type="button" onClick={() => copyWorkbenchModule(item)}><Copy size={15} /></button>
          </div>
        </div>
        <div className="user-compose-preview">
          {['顶部个人横幅', '等级进度'].includes(item.title) && <div className="compose-hero-slice"><strong>景小游</strong><span>Lv.6 探索家 · 旅行数据</span></div>}
          {['当前行程', '即将出发'].includes(item.title) && <><img src={imageFallback} alt="" /><div><strong>{item.title}</strong><span>路线、日期、同行人与进度</span></div></>}
          {['最近浏览', '我的收藏', '我的路线', '我的图片', '最近评论', '地球 Online 收藏'].includes(item.title) && <div className="compose-mini-cards"><span /><span /><span /></div>}
          {['足迹数据', '快捷入口', '账号安全', '行程清单', '行程工具箱'].includes(item.title) && <div className="compose-lines"><span /><span /><span /></div>}
        </div>
        <label>宽度
          <select value={width} onChange={e => updateWorkbenchWidth(item.id, e.target.value)}>
            {['full', 'half', 'third', 'quarter'].map(value => <option value={value} key={value}>{value}</option>)}
          </select>
        </label>
      </article>
    )
  }
  const savePersonalWorkbench = async () => {
    const saved = await saveWorkbenchLayout({ pageKey: 'user_center', theme: '清爽风景', modules: workbench })
    const layout = saved?.layout || saved?.layout_json
    setWorkbench(layout?.modules || workbench)
    setNotice('个人工作台编排已保存')
  }
  const resetPersonalWorkbench = async () => {
    const saved = await resetWorkbenchLayout()
    const layout = saved?.layout || saved?.layout_json
    setWorkbench(layout?.modules || defaultWorkbench)
    setNotice('已恢复默认工作台')
  }
  const publishPersonalWorkbench = async () => {
    await savePersonalWorkbench()
    await publishWorkbenchLayout()
    setNotice('已发布到我的工作台')
  }

  return (
    <section className="member-layout">
      <aside className="member-sidebar">
        {menus.map(([item, Icon]) => <button className={active === item ? 'active' : ''} type="button" onClick={() => setActive(item)} key={item}><Icon size={18} /> {item}</button>)}
        <article className="member-promo">
          <strong>探索世界之美</strong>
          <p>分享你的旅行故事</p>
          <button onClick={() => navigate('/community')}>去发布</button>
        </article>
      </aside>
      <main className="member-main">
        {notice && <div className="notice">{notice}</div>}
        
        <UserStatsCard 
          variant="dashboard"
          profile={{
            name: profile?.nickname || '景小游',
            level: 'Lv.6 探索家',
            desc: profile?.bio || '用脚步丈量世界，用镜头记录美好',
            avatar: profile?.avatar_url || imageFallback
          }}
          stats={{
            visited: 36,
            favorites: favorites.length || 12,
            comments: 28,
            routes: routes.length || 3,
            likes: '1.2w'
          }}
        />

        {active === '用户中心' && (
          <>
            <section className="content-grid three user-dashboard-grid">
              {visible('当前行程') && <article className="panel trip-card">
                <img src={imageFallback} alt="" />
                <div><h2>当前行程</h2><strong>{trip.title}</strong><p>2025.06.01 - 2025.06.08 · 第 3 天</p><div className="progress-line"><span style={{ width: '38%' }} /></div></div>
                <button onClick={() => setNotice(`${trip.title} 已打开`)}>查看行程</button>
                <button onClick={() => exportCurrentTrip(trip.id)}>导出行程</button>
              </article>}
              {visible('即将出发') && <article className="panel trip-card">
                <img src={imageFallback} onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = imageFallback }} alt="" />
                <div><h2>即将出发</h2><strong>新疆 · 伊犁河谷深度游</strong><p>出发倒计时 17 天 · 乌鲁木齐 - 赛里木湖</p></div>
                <button onClick={() => setNotice('即将出发行程已打开')}>查看行程</button>
              </article>}
              {visible('快捷入口') && <article className="panel quick-card">
                <h2>快捷入口</h2>
                <div className="quick-grid">
                  {[
                    ['路线规划', '/trip-planning?tab=map'],
                    ['景区实况', '/trip-planning?tab=weather#live'],
                    ['实时天气', '/trip-planning?tab=weather'],
                    ['客流查询', '/trip-planning?tab=weather'],
                    ['景区导览', '/scenic'],
                    ['停车场', '/trip-planning?tab=map'],
                    ['充电地图', '/trip-planning?tab=map'],
                    ['应急电话', '/user']
                  ].map(([label, to]) => <button key={label} onClick={() => navigate(to)}>{label}</button>)}
                </div>
              </article>}
            </section>

            <section className="content-grid two">
              {visible('最近浏览') && <article className="panel">
                <div className="card-title-row"><h2>最近浏览</h2><Link to="/scenic">查看全部</Link></div>
                <div className="mini-card-row">{recent.length ? recent.map(item => <Link to={`/scenic/${item.id}`} key={item.id}><img src={item.cover_image_url || imageFallback} onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = imageFallback }} alt="" /><strong>{item.name}</strong><span>{item.city}</span></Link>) : <span>暂无后端景区浏览记录</span>}</div>
              </article>}
              {visible('我的收藏') && <article className="panel">
                <div className="card-title-row"><h2>我的收藏</h2><button onClick={() => setActive('我的收藏')}>查看全部</button></div>
                <div className="mini-card-row">{favoriteScenic.length ? favoriteScenic.slice(0, 4).map(item => <Link to={`/scenic/${item.scenic_id || item.id}`} key={item.id}><img src={item.cover_image_url || imageFallback} onError={e => { e.currentTarget.onerror = null; e.currentTarget.src = imageFallback }} alt="" /><Heart size={16} fill="currentColor" /><strong>{item.name || item.scenic_name || `景区 #${item.scenic_id}`}</strong></Link>) : <span>暂无后端收藏数据</span>}</div>
              </article>}
            </section>

            <section className="content-grid two">
              {visible('行程清单') && <article className="panel">
                <h2>行程清单</h2>
                {checklist.map(([label, done, total]) => <p className="check-row" key={label}><CheckCircle2 size={16} /> {label}<span>{done}/{total}</span></p>)}
                <div className="health-ring small"><strong>78%</strong><span>总进度</span></div>
              </article>}
              {visible('足迹数据') && <article className="panel footprints">
                <h2>足迹数据</h2>
                <div className="china-map-placeholder">中国足迹</div>
                <div className="compact-grid"><span>已去省份 28 个</span><span>打卡城市 128 个</span><span>打卡景点 3562 个</span><span>行程里程 12680 km</span></div>
              </article>}
            </section>

            <section className="content-grid two">
              {visible('账号安全') && <article className="panel account-security">
                <h2>账号安全</h2>
                <p><ShieldCheck size={18} /> 安全等级：高</p>
                {['手机绑定', '邮箱绑定', '登录密码', '实名认证'].map(item => <span key={item}>{item} 已设置</span>)}
                <button onClick={() => setActive('账号安全')}>安全设置</button>
              </article>}
              {visible('行程工具箱') && <article className="panel">
                <h2>行程工具箱</h2>
                <p>整理行程清单、路线偏好、天气提醒与出行资料。</p>
                <button className="primary-btn" onClick={() => setNotice('行程清单已整理')}>整理行程</button>
              </article>}
            </section>
          </>
        )}

        {active === '工作台编排' && <section className="panel personal-layout-panel">
          <div className="card-title-row"><h2>我的工作台编排</h2><div className="admin-actions"><button onClick={resetPersonalWorkbench}>恢复默认</button><button onClick={savePersonalWorkbench}>保存</button><button className="primary-btn" onClick={publishPersonalWorkbench}>发布</button></div></div>
          <p>调整模块顺序、可见性和宽度后，刷新页面仍会保留。当前演示使用用户 id=1，后续可接入登录会话。</p>
          <div className="user-compose-canvas">{workbench.map(renderWorkbenchModule)}</div>
        </section>}

        {active !== '用户中心' && active !== '工作台编排' && (
          <section className="content-grid two">
            {active === '我的行程' && trips.concat([{ id: 9, title: '杭州周末湖山线', status: 'draft' }]).map(item => <article className="panel" key={item.id}><h2>{item.title}</h2><p>状态：{item.status}</p><button onClick={() => setNotice(`${item.title} 已打开`)}>查看行程</button><button onClick={() => exportCurrentTrip(item.id)}>导出行程</button></article>)}
            {active === '我的收藏' && (favoriteScenic.length ? favoriteScenic.slice(0, 4).map(item => <article className="panel" key={item.id}><h2>{item.name || item.scenic_name || `景区 #${item.scenic_id}`}</h2><p>{item.summary || '收藏数据来自后端接口。'}</p><Link className="primary-btn" to={`/scenic/${item.scenic_id || item.id}`}>查看详情</Link></article>) : <article className="panel"><h2>暂无收藏</h2><p>后端暂未返回收藏数据。</p></article>)}
            {active === '我的评论' && <article className="panel"><h2>我的评论</h2><p>西湖傍晚很美，建议从曲院风荷一路走到苏堤。</p><span className="status-badge orange">审核通过</span></article>}
            {active === '我的图片' && <article className="panel"><h2>我的图片</h2><p>最近上传 2 张图片，其中 1 张审核中。</p><span className="status-badge">审核中</span></article>}
            {active === '我的路线' && routes.concat([{ id: 8, title: '西湖环线', distance_km: 12.4 }]).map(route => <article className="panel" key={route.id}><h2>{route.title}</h2><p>总里程：{route.distance_km} km</p><button onClick={() => setNotice(`${route.title} 已保存为常用路线`)}>保存路线</button></article>)}
            {['账号安全', '消息中心', '账号设置'].includes(active) && <article className="panel"><h2>{active}</h2><p>手机、邮箱、密码、实名认证和消息偏好均可在这里维护。</p><button onClick={() => setNotice(`${active} 设置已保存`)}><Lock size={16} /> 修改 / 设置</button></article>}
          </section>
        )}
      </main>
    </section>
  )
}
