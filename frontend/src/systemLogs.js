import { apiRequest } from './api'

export function fetchSystemLogs(filters = {}) {
  const parameters = new URLSearchParams()
  for (const [key, value] of Object.entries(filters)) {
    if (value !== '' && value !== null && value !== undefined) {
      parameters.set(key, value)
    }
  }
  const query = parameters.toString()
  return apiRequest(`/api/auth/logs/${query ? `?${query}` : ''}`)
}
