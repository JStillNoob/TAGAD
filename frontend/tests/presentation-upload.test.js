import test from 'node:test'
import assert from 'node:assert/strict'

globalThis.document = {
  cookie: 'csrftoken=test-csrf-token',
  createElement: () => ({}),
}

class SuccessfulUpload {
  constructor() {
    this.upload = {}
    this.headers = {}
    SuccessfulUpload.instance = this
  }

  open(method, url) {
    this.method = method
    this.url = url
  }

  setRequestHeader(name, value) {
    this.headers[name] = value
  }

  send(body) {
    this.body = body
    this.upload.onprogress({ lengthComputable: true, loaded: 5, total: 10 })
    this.upload.onload()
    this.status = 201
    this.responseText = JSON.stringify({ id: 41, processing_status: 'ready' })
    this.onload()
  }
}

globalThis.XMLHttpRequest = SuccessfulUpload

const { uploadPresentation } = await import('../src/sessions.js')

test('presentation upload sends its idempotency key and reports both phases', async () => {
  const progress = []
  const result = await uploadPresentation({
    title: 'Reliable Upload',
    file: new Blob(['%PDF-test'], { type: 'application/pdf' }),
    requestId: 'bf2ec037-370a-4892-9086-918a04d538f3',
    onProgress: (update) => progress.push(update),
  })

  const request = SuccessfulUpload.instance
  assert.equal(request.method, 'POST')
  assert.equal(request.url, '/api/auth/presentations/')
  assert.equal(request.headers['X-CSRFToken'], 'test-csrf-token')
  assert.equal(request.body.get('title'), 'Reliable Upload')
  assert.equal(request.body.get('request_id'), 'bf2ec037-370a-4892-9086-918a04d538f3')
  assert.deepEqual(progress, [
    { phase: 'uploading', percent: 50 },
    { phase: 'processing', percent: 100 },
  ])
  assert.deepEqual(result, { id: 41, processing_status: 'ready' })
})
