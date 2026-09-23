const stateClasses = {
  starting: 'bg-blue-50 text-blue-700',
  online: 'bg-emerald-50 text-emerald-700',
  reconnecting: 'bg-amber-50 text-amber-700',
  offline: 'bg-red-50 text-red-700',
  stopped: 'bg-gray-100 text-gray-600',
}

export function cameraStateClass(state) {
  return stateClasses[state] || stateClasses.stopped
}

export function cameraStateMessage(camera) {
  if (camera.state === 'online') return 'Worker is processing frames.'
  if (camera.state === 'starting') return 'Worker is starting.'
  if (camera.state === 'reconnecting') return 'Source interrupted; reconnecting.'
  if (camera.reason === 'heartbeat_stale') return 'Worker heartbeat is stale.'
  if (camera.state === 'offline') return 'Worker is offline; the session continues.'
  return 'Waiting for the camera controller.'
}

export function mergeCameraHealth(cameras, health) {
  const healthById = new Map(health.map(item => [Number(item.camera_id), item]))
  return cameras.map((camera) => ({
    ...camera,
    state: 'stopped',
    state_label: 'Stopped',
    source_type: null,
    source_label: null,
    official_analytics: camera.position === 'front',
    reason: '',
    last_heartbeat: null,
    confirmed_students: 0,
    unclassified_students: 0,
    counts: {},
    ...healthById.get(Number(camera.id)),
  }))
}
