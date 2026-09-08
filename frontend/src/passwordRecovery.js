import { apiRequest } from './api'

export function requestPasswordReset(email) {
  return apiRequest('/api/auth/password-reset/request/', {
    method: 'POST',
    body: JSON.stringify({ email }),
  })
}

export function validatePasswordReset(uid, token) {
  return apiRequest('/api/auth/password-reset/validate/', {
    method: 'POST',
    body: JSON.stringify({ uid, token }),
  })
}

export function confirmPasswordReset(payload) {
  return apiRequest('/api/auth/password-reset/confirm/', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}
