import test from 'node:test'
import assert from 'node:assert/strict'

import { createSessionCountdown } from '../src/sessionCountdown.js'

function fakeTimers() {
  const pending = []
  return {
    schedule(callback) {
      pending.push(callback)
      return callback
    },
    cancel(timer) {
      const index = pending.indexOf(timer)
      if (index >= 0) pending.splice(index, 1)
    },
    advance() {
      pending.shift()?.()
    },
    get pendingCount() {
      return pending.length
    },
  }
}

test('session starts only after the five-second countdown reaches zero', () => {
  const timers = fakeTimers()
  const ticks = []
  let completed = 0
  const countdown = createSessionCountdown({
    seconds: 5,
    onTick: value => ticks.push(value),
    onComplete: () => { completed += 1 },
    schedule: callback => timers.schedule(callback),
    cancelScheduled: timer => timers.cancel(timer),
  })

  assert.equal(countdown.start(), true)
  assert.deepEqual(ticks, [5])
  assert.equal(completed, 0)

  for (let second = 0; second < 4; second += 1) timers.advance()
  assert.equal(completed, 0)
  timers.advance()

  assert.deepEqual(ticks, [5, 4, 3, 2, 1, 0])
  assert.equal(completed, 1)
  assert.equal(countdown.active, false)
})

test('cancelling prevents the session from starting', () => {
  const timers = fakeTimers()
  let completed = 0
  const countdown = createSessionCountdown({
    onTick: () => {},
    onComplete: () => { completed += 1 },
    schedule: callback => timers.schedule(callback),
    cancelScheduled: timer => timers.cancel(timer),
  })

  countdown.start()
  timers.advance()
  assert.equal(countdown.cancel(), true)

  while (timers.pendingCount) timers.advance()
  assert.equal(completed, 0)
  assert.equal(countdown.active, false)
})

test('repeated start clicks cannot create duplicate countdowns', () => {
  const timers = fakeTimers()
  let completed = 0
  const countdown = createSessionCountdown({
    onTick: () => {},
    onComplete: () => { completed += 1 },
    schedule: callback => timers.schedule(callback),
    cancelScheduled: timer => timers.cancel(timer),
  })

  assert.equal(countdown.start(), true)
  assert.equal(countdown.start(), false)
  assert.equal(timers.pendingCount, 1)

  for (let second = 0; second < 5; second += 1) timers.advance()
  assert.equal(completed, 1)
})
