import { apiRequest } from './api'

export function fetchSessionOptions() {
  return apiRequest('/api/auth/session-options/')
}

export function fetchSessions() {
  return apiRequest('/api/auth/sessions/')
}

export function uploadPresentation({ title, file }) {
  const body = new FormData()
  body.append('title', title)
  body.append('file', file)
  return apiRequest('/api/auth/presentations/', { method: 'POST', body })
}

export function startClassroomSession({ subject, presentation, cameras }) {
  return apiRequest('/api/auth/sessions/', {
    method: 'POST',
    body: JSON.stringify({ subject, presentation, cameras }),
  })
}

export function enterSessionSlide(sessionId, slideId) {
  return apiRequest(`/api/auth/sessions/${sessionId}/enter-slide/`, {
    method: 'POST',
    body: JSON.stringify({ slide: slideId }),
  })
}

export function endClassroomSession(sessionId) {
  return apiRequest(`/api/auth/sessions/${sessionId}/end/`, { method: 'POST' })
}
