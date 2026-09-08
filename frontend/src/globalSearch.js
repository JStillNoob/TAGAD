import { apiRequest } from './api'

export function fetchGlobalSearch(query) {
  const parameters = new URLSearchParams({ q: query })
  return apiRequest(`/api/auth/search/?${parameters}`)
}
