import test from 'node:test'
import assert from 'node:assert/strict'

import {
  findOwnActiveSession,
  findOwnPreparedSession,
  restoreSlideIndex,
  startSessionWithRecovery,
  endSessionWithRecovery,
  continueLessonWithRecovery,
  finishLessonWithRecovery,
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

test('refresh recovery finds a prepared session separately', () => {
  const prepared = { ...active, id: 11, status: 'preparing', started_at: null }
  assert.equal(findOwnPreparedSession([active, prepared], 7), prepared)
  assert.equal(findOwnPreparedSession([prepared], 99), null)
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

test('prepared start recovery uses the exact meeting and preserves its current closed state', async () => {
  const closed = { ...active, status: 'completed', ended_at: '2026-11-07T01:00:00Z', end_action: 'save' }
  const recovered = await startSessionWithRecovery({
    start: async () => { throw new Error('response lost') },
    sessionId: 10, userId: 7, fetchSession: async id => { assert.equal(id, 10); return closed },
  })
  assert.equal(recovered, closed)
})

test('exact start recovery cannot restore a different class', async () => {
  const original = new Error('start failed')
  await assert.rejects(startSessionWithRecovery({
    start: async () => { throw original }, sessionId: 10, userId: 7,
    fetchSession: async () => ({ ...active, id: 20 }),
  }), error => error === original)
})

test('lost save response recovers only its committed save action', async () => {
  const saved = { ...active, status: 'completed', end_action: 'save', ended_at: '2026-11-07T01:00:00Z' }
  const recovered = await endSessionWithRecovery({
    sessionId: 10, action: 'save', end: async () => { throw new Error('response lost') },
    fetchSession: async () => saved,
  })
  assert.equal(recovered, saved)
  const original = new Error('response lost')
  await assert.rejects(endSessionWithRecovery({
    sessionId: 10, action: 'save', end: async () => { throw original },
    fetchSession: async () => ({ ...saved, end_action: 'finish' }),
  }), error => error === original && error.recoveredSession.end_action === 'finish')
})

test('unavailable recovery read retains an explicit pending state', async () => {
  const original = new Error('response lost')
  await assert.rejects(endSessionWithRecovery({
    sessionId: 10, action: 'save', end: async () => { throw original },
    fetchSession: async () => { throw new Error('still offline') },
  }), error => error.recoveryPending === true)
})

test('continuation recovery matches both the lesson and request key', async () => {
  const prepared = { ...active, id: 11, status: 'preparing', lesson: { id: 3 }, continuation_request_id: 'request-a' }
  const parameters = {
    prepare: async () => { throw new Error('response lost') }, lessonId: 3, requestId: 'request-a',
    fetchLesson: async () => ({ id: 3, prepared_session: 11 }), fetchSession: async () => prepared,
  }
  assert.equal(await continueLessonWithRecovery(parameters), prepared)
  await assert.rejects(continueLessonWithRecovery({ ...parameters, requestId: 'request-b' }),
    error => error.recoveredSession === prepared)
})

test('saved lesson finish recovers completion and retains changed saved revisions', async () => {
  const completed = { id: 3, state: 'completed', revision: 5 }
  const parameters = { lessonId: 3, finish: async () => { throw new Error('response lost') }, fetchLesson: async () => completed }
  assert.equal(await finishLessonWithRecovery(parameters), completed)
  await assert.rejects(finishLessonWithRecovery({ ...parameters, fetchLesson: async () => ({ id: 3, state: 'saved', revision: 6 }) }),
    error => error.recoveredLesson.revision === 6)
})
