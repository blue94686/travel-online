const reloadKey = 'scenic-online-chunk-reload'
const lastReload = Number(sessionStorage.getItem(reloadKey) || 0)
const now = Date.now()

if (!lastReload || now - lastReload > 10000) {
  sessionStorage.setItem(reloadKey, String(now))
  window.location.reload()
}

export default function ChunkReloadFallback() {
  return null
}
