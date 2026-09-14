import test from 'node:test'
import assert from 'node:assert/strict'

import { availableCameraIds, cameraReadinessLabel } from '../src/cameraSelection.js'

test('active classroom cameras are selected by default', () => {
  const subject = {
    cameras: [
      { id: 4, status: 'active' },
      { id: 8, status: 'inactive' },
      { id: 15, status: 'active' },
    ],
  }

  assert.deepEqual(availableCameraIds(subject), [4, 15])
})

test('a subject without configured cameras remains valid', () => {
  assert.deepEqual(availableCameraIds({ cameras: [] }), [])
  assert.deepEqual(availableCameraIds(null), [])
})

test('camera readiness never claims that a configured camera is connected', () => {
  assert.equal(cameraReadinessLabel({ status: 'active' }), 'Configured')
  assert.equal(cameraReadinessLabel({ status: 'inactive' }), 'Inactive')
})
