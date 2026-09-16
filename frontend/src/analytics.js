import { apiRequest } from './api'
import { paginationQuery } from './pagination'

export function fetchAnalyticsSessions(parameters = {}) {
  return apiRequest(`/api/auth/analytics/sessions/${paginationQuery(parameters)}`)
}

export function fetchSessionAnalytics(sessionId) {
  return apiRequest(`/api/auth/analytics/sessions/${sessionId}/`)
}

export function analyticsCsvUrl(sessionId) {
  return `/api/auth/analytics/sessions/${sessionId}/csv/`
}
