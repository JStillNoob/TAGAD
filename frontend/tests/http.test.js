import test from 'node:test'
import assert from 'node:assert/strict'

import { request } from '../src/http.js'
import { apiRequest } from '../src/api.js'

test('network failures become a useful backend availability message', async () => {
  globalThis.fetch = async () => { throw new TypeError('fetch failed') }

  await assert.rejects(
    request('/api/auth/me/'),
    /backend server is unavailable/i,
  )
})

test('server failures hide sensitive details and include the request reference', async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    headers: { get: name => name === 'X-Request-ID' ? 'failure-reference-123' : null },
    json: async () => ({ detail: 'DB_PASSWORD=top-secret', student: 'private-name' }),
  })

  await assert.rejects(
    apiRequest('/api/auth/example/'),
    (error) => {
      assert.match(error.message, /failure-reference-123/)
      assert.doesNotMatch(error.message, /top-secret|private-name/)
      assert.deepEqual(error.fields, {})
      return true
    },
  )
})

test('validation failures expose the first useful field message', async () => {
  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    headers: { get: () => null },
    json: async () => ({
      classroom: { room_code: ['Use a valid classroom code.'] },
    }),
  })

  await assert.rejects(
    apiRequest('/api/auth/classrooms/'),
    (error) => {
      assert.equal(error.message, 'Use a valid classroom code.')
      assert.deepEqual(error.fields, {
        classroom: { room_code: ['Use a valid classroom code.'] },
      })
      return true
    },
  )
})
