import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'


function view(name) {
  return readFileSync(new URL(`../src/views/${name}`, import.meta.url), 'utf8')
}


test('mutating forms guard against duplicate submissions', () => {
  const classes = view('StudentsView.vue')
  const users = view('UserManagementView.vue')
  const settings = view('SettingsView.vue')
  const registration = view('RegisterView.vue')
  const login = view('LoginView.vue')
  const recovery = view('ForgotPasswordView.vue')
  const reset = view('ResetPasswordView.vue')
  const session = view('SessionView.vue')

  assert.equal((classes.match(/if \(saving\.value\) return/g) || []).length, 4)
  assert.match(users, /async function saveUser\(\) \{\s+if \(saving\.value\) return/)
  assert.match(settings, /if \(profilePending\.value\) return/)
  assert.match(settings, /if \(organizationPending\.value\) return/)
  assert.match(settings, /if \(passwordPending\.value \|\| !passwordReady\.value\) return/)
  assert.match(registration, /if \(submitting\.value\) return/)
  assert.match(login, /if \(submitting\.value\) return/)
  assert.match(recovery, /if \(submitting\.value\) return/)
  assert.match(reset, /if \(submitting\.value \|\| !passwordReady\.value\) return/)
  assert.match(session, /if \(actionBusy\.value \|\| !uploadFile\.value/)
})


test('administration forms expose validation limits and field errors', () => {
  const classes = view('StudentsView.vue')
  const users = view('UserManagementView.vue')

  assert.match(classes, /max="10000"/)
  assert.match(classes, /firstError\('building'\)/)
  assert.match(classes, /firstError\('subject_name'\)/)
  assert.match(users, /fieldErrors\.contact_no/)
  assert.match(users, /inputmode="tel"/)
})
