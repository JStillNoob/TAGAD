import test from 'node:test'
import assert from 'node:assert/strict'

import {
  findOwnActiveSession,
  restoreSlideIndex,
  startSessionWithRecovery,
  endSessionWithRecovery,
} from '../src/sessionReliability.js'

const active = {
  id: 10,
  user: 7,
  status: 'ongoing',
  current_slide: 102,
  cameras: [{ id: 4 }],
  presentation: { slides: [{ id: 101 }, { id: 102 }] },
}

test('refresh recovery finds only the signed-in user active session', () => {
  const sessions = [
    { ...active, id: 9, user: 8 },
    { ...active, id: 8, status: 'completed' },
    active,
  ]

  assert.equal(findOwnActiveSession(sessions, 7), active)
  assert.equal(findOwnActiveSession(sessions, 99), null)
})

test('refresh recovery restores the persisted slide safely', () => {
  assert.equal(restoreSlideIndex(active), 1)
  assert.equal(restoreSlideIndex({ ...active, current_slide: 999 }), 0)
  assert.equal(restoreSlideIndex({ ...active, presentation: { slides: [] } }), 0)
})

test('a lost start response recovers the one active session', async () => {
  const recovered = await startSessionWithRecovery({
    start: async () => { throw new Error('response lost') },
    fetchSessions: async () => [active],
    userId: 7,
  })

  assert.equal(recovered, active)
})

test('start recovery preserves the original error when no session started', async () => {
  const original = new Error('start failed')

  await assert.rejects(
    startSessionWithRecovery({
      start: async () => { throw original },
      fetchSessions: async () => [],
      userId: 7,
    }),
    (error) => error === original,
  )
})

test('a lost end response recovers the completed session', async () => {
  const completed = { ...active, status: 'completed', ended_at: '2026-09-14T10:00:00Z' }
  const recovered = await endSessionWithRecovery({
    sessionId: active.id,
    end: async () => { throw new Error('response lost') },
    fetchSessions: async () => [completed],
  })

  assert.equal(recovered, completed)
})

test('end recovery preserves the original error when the session is still active', async () => {
  const original = new Error('end failed')

  await assert.rejects(
    endSessionWithRecovery({
      sessionId: active.id,
      end: async () => { throw original },
      fetchSessions: async () => [active],
    }),
    (error) => error === original,
  )
})
