import { ensureCsrfCookie, getCookie } from './auth'

async function request(url, options = {}) {
  const method = options.method || 'GET'
  const unsafe = !['GET', 'HEAD', 'OPTIONS'].includes(method)
  if (unsafe) await ensureCsrfCookie()

  const response = await fetch(url, {
    ...options,
    credentials: 'same-origin',
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
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

export function fetchManagedUsers() {
  return request('/api/auth/users/')
}

export function fetchUserOptions() {
  return request('/api/auth/users/options/')
}

export function createManagedUser(user) {
  return request('/api/auth/users/', {
    method: 'POST',
    body: JSON.stringify(user),
  })
}

export function updateManagedUser(id, changes) {
  return request(`/api/auth/users/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deactivateManagedUser(id) {
  return request(`/api/auth/users/${id}/`, { method: 'DELETE' })
}
