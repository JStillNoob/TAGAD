import { apiRequest } from './api'

export function fetchAnalyticsSessions() {
  return apiRequest('/api/auth/analytics/sessions/')
}

export function fetchSessionAnalytics(sessionId) {
  return apiRequest(`/api/auth/analytics/sessions/${sessionId}/`)
}

export function analyticsCsvUrl(sessionId) {
  return `/api/auth/analytics/sessions/${sessionId}/csv/`
}
