import { apiRequest } from './api'
import { paginationQuery } from './pagination'

export function fetchClassrooms(parameters = {}) {
  return apiRequest(`/api/auth/classrooms/${paginationQuery(parameters)}`)
}

export function createClassroom(classroom) {
  return apiRequest('/api/auth/classrooms/', {
    method: 'POST',
    body: JSON.stringify(classroom),
  })
}

export function updateClassroom(id, changes) {
  return apiRequest(`/api/auth/classrooms/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deleteClassroom(id) {
  return apiRequest(`/api/auth/classrooms/${id}/`, { method: 'DELETE' })
}

export function fetchSubjects(parameters = {}) {
  return apiRequest(`/api/auth/subjects/${paginationQuery(parameters)}`)
}

export function createSubject(subject) {
  return apiRequest('/api/auth/subjects/', {
    method: 'POST',
    body: JSON.stringify(subject),
  })
}

export function updateSubject(id, changes) {
  return apiRequest(`/api/auth/subjects/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deleteSubject(id) {
  return apiRequest(`/api/auth/subjects/${id}/`, { method: 'DELETE' })
}

export function fetchClassManagementOptions() {
  return apiRequest('/api/auth/class-management/options/')
}

export function createQuickSetup(setup) {
  return apiRequest('/api/auth/class-management/quick-setup/', {
    method: 'POST',
    body: JSON.stringify(setup),
  })
}

export function fetchCameras(parameters = {}) {
  return apiRequest(`/api/auth/cameras/${paginationQuery(parameters)}`)
}

export function createCamera(camera) {
  return apiRequest('/api/auth/cameras/', {
    method: 'POST',
    body: JSON.stringify(camera),
  })
}

export function updateCamera(id, changes) {
  return apiRequest(`/api/auth/cameras/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(changes),
  })
}

export function deleteCamera(id) {
  return apiRequest(`/api/auth/cameras/${id}/`, { method: 'DELETE' })
}
