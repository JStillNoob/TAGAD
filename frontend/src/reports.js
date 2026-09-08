import { apiRequest } from './api'

export function fetchReports() {
  return apiRequest('/api/auth/reports/')
}

export function fetchReportOptions() {
  return apiRequest('/api/auth/reports/options/')
}

export function generateReport(session, reportType) {
  return apiRequest('/api/auth/reports/', {
    method: 'POST',
    body: JSON.stringify({ session, report_type: reportType }),
  })
}
