import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider } from 'react-router-dom'
import { router } from './router.jsx'
import './styles/tokens.css'
import './styles/global.css'
import './styles/layout.css'
import './styles/pages.css'

const chunkReloadKey = 'scenic-online-chunk-reload'
const reloadForFreshChunks = () => {
  const lastReload = Number(sessionStorage.getItem(chunkReloadKey) || 0)
  const now = Date.now()
  if (lastReload && now - lastReload < 10000) return
  sessionStorage.setItem(chunkReloadKey, String(now))
  window.location.reload()
}

window.addEventListener('vite:preloadError', reloadForFreshChunks)
window.addEventListener('unhandledrejection', event => {
  if (/Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module/i.test(String(event.reason?.message || event.reason || ''))) {
    reloadForFreshChunks()
  }
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
)
