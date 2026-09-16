import { apiErrorMessage, apiRequest } from './api.js'
import { ensureCsrfCookie, getCookie } from './auth.js'
import { paginationQuery } from './pagination.js'

export function fetchSessionOptions() {
  return apiRequest('/api/auth/session-options/')
}

export function fetchSessionSubjectPage(parameters = {}) {
  return apiRequest(`/api/auth/session-subjects/${paginationQuery(parameters)}`)
}

export function fetchPresentationPage(parameters = {}) {
  return apiRequest(`/api/auth/presentations/${paginationQuery(parameters)}`)
}

export async function fetchSessions(parameters = {}) {
  const page = await apiRequest(`/api/auth/sessions/${paginationQuery(parameters)}`)
  return page.results
}

export function fetchSessionPage(parameters = {}) {
  return apiRequest(`/api/auth/sessions/${paginationQuery(parameters)}`)
}

export async function uploadPresentation({ title, file, requestId, onProgress }) {
  await ensureCsrfCookie()
  const body = new FormData()
  body.append('title', title)
  body.append('file', file)
  if (requestId) body.append('request_id', requestId)

  return new Promise((resolve, reject) => {
    const upload = new XMLHttpRequest()
    upload.open('POST', '/api/auth/presentations/')
    upload.withCredentials = true
    upload.setRequestHeader('X-CSRFToken', getCookie('csrftoken'))
    upload.upload.onprogress = (event) => {
      if (!event.lengthComputable) return
      onProgress?.({
        phase: 'uploading',
        percent: Math.round((event.loaded / event.total) * 100),
      })
    }
    upload.upload.onload = () => onProgress?.({ phase: 'processing', percent: 100 })
    upload.onerror = () => reject(new Error(
      'The backend server is unavailable. Check your connection and try again.',
    ))
    upload.onload = () => {
      let data = null
      try {
        data = upload.responseText ? JSON.parse(upload.responseText) : null
      } catch {
        data = null
      }
      if (upload.status >= 200 && upload.status < 300) {
        resolve(data)
        return
      }
      const response = {
        status: upload.status,
        headers: { get: name => upload.getResponseHeader?.(name) },
      }
      const error = new Error(apiErrorMessage(response, data))
      error.fields = upload.status < 500 && data && typeof data === 'object' ? data : {}
      error.status = upload.status
      reject(error)
    }
    upload.send(body)
  })
}

export function retryPresentation(id) {
  return apiRequest(`/api/auth/presentations/${id}/retry/`, { method: 'POST' })
}

export function deletePresentation(id) {
  return apiRequest(`/api/auth/presentations/${id}/`, { method: 'DELETE' })
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

export function simulateEngagement(sessionId) {
  return apiRequest(`/api/auth/sessions/${sessionId}/simulate-engagement/`, { method: 'POST' })
}
