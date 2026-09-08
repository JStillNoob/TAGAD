import test from 'node:test'
import assert from 'node:assert/strict'

import { request } from '../src/http.js'

test('network failures become a useful backend availability message', async () => {
  globalThis.fetch = async () => { throw new TypeError('fetch failed') }

  await assert.rejects(
    request('/api/auth/me/'),
    /backend server is unavailable/i,
  )
})
