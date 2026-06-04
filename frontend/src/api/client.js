const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''

export async function request(path, options = {}, fallbackKey) {
  try {
    const token = localStorage.getItem('scenic-token') || ''
    const isFormData = options.body instanceof FormData
    const headers = isFormData
      ? { ...(options.headers || {}) }
      : { 'Content-Type': 'application/json', ...(options.headers || {}) }
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }
    const normalizedPath = path.startsWith('/') ? path : `/${path}`
    const response = await fetch(`${baseURL}${normalizedPath}`, {
      headers,
      ...options
    })
    const raw = await response.text()
    let payload = null
    if (raw) {
      try {
        payload = JSON.parse(raw)
      } catch {
        payload = {
          success: false,
          message: raw.slice(0, 180) || `接口返回非 JSON 内容，HTTP ${response.status}`,
        }
      }
    } else {
      payload = {
        success: false,
        message: `接口无响应内容，HTTP ${response.status}`,
      }
    }
    if (!response.ok || payload.success === false) throw new Error(payload.message || '请求失败')
    return payload.data
  } catch (error) {
    console.info(`[api unavailable] ${path}${fallbackKey ? ` (${fallbackKey})` : ''}: ${error.message}`)
    return null
  }
}
