import test from 'node:test'
import assert from 'node:assert/strict'

import {
  createUploadRequestId,
  presentationDirectionForKey,
} from '../src/presentationControls.js'

test('left and right arrows navigate an active presentation', () => {
  const target = { tagName: 'DIV', isContentEditable: false }

  assert.equal(presentationDirectionForKey({ key: 'ArrowLeft', target }, true), -1)
  assert.equal(presentationDirectionForKey({ key: 'ArrowRight', target }, true), 1)
  assert.equal(presentationDirectionForKey({ key: 'Space', target }, true), 0)
})

test('presentation shortcuts do not interfere with typing or inactive sessions', () => {
  for (const tagName of ['INPUT', 'TEXTAREA', 'SELECT']) {
    assert.equal(
      presentationDirectionForKey({ key: 'ArrowRight', target: { tagName } }, true),
      0,
    )
  }
  assert.equal(
    presentationDirectionForKey({
      key: 'ArrowRight',
      target: { tagName: 'DIV', isContentEditable: true },
    }, true),
    0,
  )
  assert.equal(
    presentationDirectionForKey({ key: 'ArrowRight', target: { tagName: 'DIV' } }, false),
    0,
  )
  assert.equal(
    presentationDirectionForKey({
      key: 'ArrowLeft',
      target: { tagName: 'DIV' },
      altKey: true,
    }, true),
    0,
  )
})

test('upload request identifiers are non-empty and unique', () => {
  const first = createUploadRequestId()
  const second = createUploadRequestId()

  assert.ok(first)
  assert.notEqual(first, second)
})
