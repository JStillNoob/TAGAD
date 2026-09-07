import { apiRequest } from './api'

export function fetchClassrooms() {
  return apiRequest('/api/auth/classrooms/')
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

export function fetchSubjects() {
  return apiRequest('/api/auth/subjects/')
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

export function fetchCameras() {
  return apiRequest('/api/auth/cameras/')
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
