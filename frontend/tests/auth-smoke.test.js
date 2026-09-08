import test from 'node:test'
import assert from 'node:assert/strict'

import { currentUser, login, logout } from '../src/auth.js'

test('login establishes frontend user state and logout clears it', async () => {
  globalThis.document = { cookie: 'csrftoken=smoke-token' }
  const requests = []
  globalThis.fetch = async (url, options = {}) => {
    requests.push({ url, options })
    if (url.endsWith('/login/')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 1, username: 'demo.teacher', role: 'teacher' }),
      }
    }
    return { ok: true, status: 204, json: async () => null }
  }

  await login('demo.teacher', 'DemoPassword!19')
  assert.equal(currentUser.value?.username, 'demo.teacher')
  assert.equal(requests[0].url, '/api/auth/login/')
  assert.equal(requests[0].options.method, 'POST')

  await logout()
  assert.equal(currentUser.value, null)
  assert.equal(requests[1].url, '/api/auth/logout/')
  assert.equal(requests[1].options.method, 'POST')
})
