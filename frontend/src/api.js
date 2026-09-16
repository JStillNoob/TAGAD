import { ensureCsrfCookie, getCookie } from './auth.js'
import { request } from './http.js'

const safeRequestId = /^[A-Za-z0-9._-]{1,64}$/

export function apiErrorMessage(response, data = null) {
  if (response.status < 500) return data?.detail || 'Unable to complete the request.'
  const candidate = response.headers?.get?.('X-Request-ID') || data?.request_id || ''
  const reference = safeRequestId.test(candidate) ? ` Reference: ${candidate}` : ''
  return `The server could not complete the request. Please try again.${reference}`
}

export async function apiRequest(url, options = {}) {
  const method = options.method || 'GET'
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method)
  const formData = options.body instanceof FormData
  if (unsafe) await ensureCsrfCookie()

  const response = await request(url, {
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
    const error = new Error(apiErrorMessage(response, data))
    error.fields = response.status < 500 && data && typeof data === 'object' ? data : {}
    error.status = response.status
    throw error
  }
  return data
}
