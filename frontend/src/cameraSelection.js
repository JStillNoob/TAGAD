export function availableCameraIds(subject) {
  return (subject?.cameras || [])
    .filter((camera) => camera.status === 'active')
    .map((camera) => camera.id)
}

export function cameraReadinessLabel(camera) {
  return camera?.status === 'active' ? 'Configured' : 'Inactive'
}
