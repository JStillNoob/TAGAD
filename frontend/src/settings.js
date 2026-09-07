import { apiRequest } from './api'

export function fetchSettings() {
  return apiRequest('/api/auth/settings/')
}

export function updateProfile(changes) {
  return apiRequest('/api/auth/settings/profile/', {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function updateOrganization(changes) {
  return apiRequest('/api/auth/settings/organization/', {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function changePassword(passwords) {
  return apiRequest('/api/auth/settings/password/', {
    method: 'POST',
    body: JSON.stringify(passwords),
  })
}
