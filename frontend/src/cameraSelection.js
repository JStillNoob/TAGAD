export function availableCameraIds(subject) {
  return (subject?.cameras || [])
    .filter((camera) => camera.status === 'active')
    .map((camera) => camera.id)
}

export function cameraReadinessLabel(state) {
  return {
    checking: 'Checking',
    available: 'Available',
    offline: 'Offline',
    uninitialized: 'Not initialized',
  }[state] || 'Checking'
}

export function cameraReadinessClass(state) {
  return {
    available: 'bg-emerald-50 text-emerald-700',
    offline: 'bg-red-50 text-red-600',
    uninitialized: 'bg-amber-50 text-amber-700',
  }[state] || 'bg-gray-100 text-gray-500'
}
