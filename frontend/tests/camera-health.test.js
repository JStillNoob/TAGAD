import assert from 'node:assert/strict'
import test from 'node:test'

import {
  cameraStateClass,
  cameraStateMessage,
  mergeCameraHealth,
} from '../src/cameraHealth.js'


test('camera health is merged by camera ID without combining source counts', () => {
  const result = mergeCameraHealth([
    { id: 1, name: 'Center', position: 'front' },
    { id: 2, name: 'Left', position: 'left' },
  ], [
    {
      camera_id: 2,
      state: 'online',
      state_label: 'Online',
      confirmed_students: 7,
      counts: { engaged: 4, attentive: 3 },
    },
  ])

  assert.equal(result[0].state, 'stopped')
  assert.equal(result[0].official_analytics, true)
  assert.equal(result[0].confirmed_students, 0)
  assert.equal(result[1].state, 'online')
  assert.equal(result[1].official_analytics, false)
  assert.deepEqual(result[1].counts, { engaged: 4, attentive: 3 })
})

test('camera state helpers distinguish recovery, stale, and online states', () => {
  assert.match(cameraStateClass('online'), /emerald/)
  assert.match(cameraStateClass('offline'), /red/)
  assert.match(cameraStateMessage({ state: 'reconnecting' }), /reconnecting/i)
  assert.match(cameraStateMessage({ state: 'offline', reason: 'heartbeat_stale' }), /stale/i)
  assert.match(cameraStateMessage({ state: 'online' }), /processing/i)
})
