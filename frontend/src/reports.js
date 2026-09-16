import { apiRequest } from './api'
import { paginationQuery } from './pagination'

export function fetchReports(parameters = {}) {
  return apiRequest(`/api/auth/reports/${paginationQuery(parameters)}`)
}

export function fetchReportOptions(parameters = {}) {
  return apiRequest(`/api/auth/reports/options/${paginationQuery(parameters)}`)
}

export function generateReport(session, reportType) {
  return apiRequest('/api/auth/reports/', {
    method: 'POST',
    body: JSON.stringify({ session, report_type: reportType }),
  })
}
