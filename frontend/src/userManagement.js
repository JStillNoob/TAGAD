import { apiRequest } from './api'
import { paginationQuery } from './pagination'

export function fetchManagedUsers(parameters = {}) {
  return apiRequest(`/api/auth/users/${paginationQuery(parameters)}`)
}

export function fetchUserOptions() {
  return apiRequest('/api/auth/users/options/')
}

export function createManagedUser(user) {
  return apiRequest('/api/auth/users/', {
    method: 'POST',
    body: JSON.stringify(user),
  })
}

export function updateManagedUser(id, changes) {
  return apiRequest(`/api/auth/users/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deactivateManagedUser(id) {
  return apiRequest(`/api/auth/users/${id}/`, { method: 'DELETE' })
}
