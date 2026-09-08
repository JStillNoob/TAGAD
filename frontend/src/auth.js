import { readonly, ref } from 'vue'
import { request } from './http.js'

const userState = ref(null)
let sessionChecked = false

export const currentUser = readonly(userState)

export function getCookie(name) {
  const prefix = `${name}=`
  const cookie = document.cookie
    .split(';')
    .map((item) => item.trim())
    .find((item) => item.startsWith(prefix))
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null
}

async function parseResponse(response) {
  if (response.status === 204) return null
  return response.json().catch(() => null)
}

export async function ensureCsrfCookie() {
  if (getCookie('csrftoken')) return
  const response = await request('/api/auth/csrf/', { credentials: 'same-origin' })
  if (!response.ok) throw new Error('Unable to initialize a secure session.')
}

export async function fetchCurrentUser({ force = false } = {}) {
  if (sessionChecked && !force) return userState.value

  const response = await request('/api/auth/me/', { credentials: 'same-origin' })
  if (response.ok) {
    userState.value = await response.json()
  } else if (response.status === 401 || response.status === 403) {
    userState.value = null
  } else {
    throw new Error('Unable to verify the current session.')
  }
  sessionChecked = true
  return userState.value
}

export async function login(identity, password) {
  await ensureCsrfCookie()
  const response = await request('/api/auth/login/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify({ identity, password }),
  })
  const data = await parseResponse(response)
  if (!response.ok) {
    throw new Error(data?.detail || 'Unable to sign in with those credentials.')
  }
  userState.value = data
  sessionChecked = true
  return data
}

export async function register(account) {
  await ensureCsrfCookie()
  const response = await request('/api/auth/register/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': getCookie('csrftoken'),
    },
    body: JSON.stringify(account),
  })
  const data = await parseResponse(response)
  if (!response.ok) {
    const error = new Error(data?.detail || 'Please correct the highlighted fields.')
    error.fields = data && typeof data === 'object' ? data : {}
    throw error
  }
  return data
}

export async function logout() {
  await ensureCsrfCookie()
  const response = await request('/api/auth/logout/', {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'X-CSRFToken': getCookie('csrftoken') },
  })
  if (response.status === 401 || response.status === 403) {
    const user = await fetchCurrentUser({ force: true })
    if (!user) return
  }
  if (!response.ok) {
    const data = await parseResponse(response)
    throw new Error(data?.detail || 'Unable to sign out.')
  }
  userState.value = null
  sessionChecked = true
}
