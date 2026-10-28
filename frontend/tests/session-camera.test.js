import test from 'node:test'
import assert from 'node:assert/strict'

import {
  availableCameraIds,
  cameraReadinessClass,
  cameraReadinessLabel,
} from '../src/cameraSelection.js'

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

test('camera selection labels live connection checks without showing video', () => {
  assert.equal(cameraReadinessLabel('checking'), 'Checking')
  assert.equal(cameraReadinessLabel('available'), 'Available')
  assert.equal(cameraReadinessLabel('offline'), 'Offline')
  assert.equal(cameraReadinessLabel('uninitialized'), 'Not initialized')
  assert.match(cameraReadinessClass('available'), /emerald/)
  assert.match(cameraReadinessClass('offline'), /red/)
})
