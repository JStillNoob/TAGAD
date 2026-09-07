import { ensureCsrfCookie, getCookie } from './auth'

export async function apiRequest(url, options = {}) {
  const method = options.method || 'GET'
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method)
  const formData = options.body instanceof FormData
  if (unsafe) await ensureCsrfCookie()

  const response = await fetch(url, {
    ...options,
    credentials: 'same-origin',
    headers: {
      ...(options.body && !formData ? { 'Content-Type': 'application/json' } : {}),
      ...(unsafe ? { 'X-CSRFToken': getCookie('csrftoken') } : {}),
      ...options.headers,
    },
  })
  const data = response.status === 204
    ? null
    : await response.json().catch(() => null)

  if (!response.ok) {
    const error = new Error(data?.detail || 'Unable to complete the request.')
    error.fields = data && typeof data === 'object' ? data : {}
    error.status = response.status
    throw error
  }
  return data
}
