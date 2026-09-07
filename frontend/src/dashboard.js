import { apiRequest } from './api'

export function fetchDashboardSummary() {
  return apiRequest('/api/auth/dashboard/')
}
