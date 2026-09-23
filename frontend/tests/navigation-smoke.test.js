import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const routerSource = await readFile(new URL('../src/router/index.js', import.meta.url), 'utf8')
const layoutSource = await readFile(new URL('../src/layouts/AppLayout.vue', import.meta.url), 'utf8')
const dashboardSource = await readFile(new URL('../src/views/DashboardView.vue', import.meta.url), 'utf8')
const sessionSource = await readFile(new URL('../src/views/SessionView.vue', import.meta.url), 'utf8')
const analyticsSource = await readFile(new URL('../src/views/AnalyticsView.vue', import.meta.url), 'utf8')
const classesSource = await readFile(new URL('../src/views/StudentsView.vue', import.meta.url), 'utf8')
const classManagementSource = await readFile(new URL('../src/classManagement.js', import.meta.url), 'utf8')

test('authenticated shell keeps its core navigation and logout actions', () => {
  assert.match(routerSource, /path: '\/dashboard'/)
  assert.match(layoutSource, /to="\/settings"/)
  assert.match(layoutSource, /@click="handleLogout"/)
})

test('live session connects to engagement WebSocket and exposes the development simulator', () => {
  assert.match(sessionSource, /new WebSocket/)
  assert.match(sessionSource, /simulateEngagement/)
  assert.match(sessionSource, /options\.simulator_enabled/)
  assert.match(sessionSource, /setInterval\(emitSimulation, 2000\)/)
})

test('live session automatically selects classroom cameras and provides bulk controls', () => {
  assert.match(sessionSource, /watch\(selectedSubjectId, selectAllCameras\)/)
  assert.match(sessionSource, /@click="selectAllCameras">Select all/)
  assert.match(sessionSource, /@click="clearCameraSelection">Clear/)
  assert.match(sessionSource, /You can still start the session and use the development simulator/)
})

test('active session shows independent camera worker health without combining analytics', () => {
  assert.match(sessionSource, /Camera & Worker Health/)
  assert.match(sessionSource, /Simulator only/)
  assert.match(sessionSource, /Official analytics/)
  assert.match(sessionSource, /Diagnostics only/)
  assert.match(sessionSource, /fetchSessionCameraHealth/)
})

test('ending a session opens its analytics and the chart renders after loading', () => {
  assert.match(sessionSource, /window\.confirm/)
  assert.match(sessionSource, /endSessionWithRecovery/)
  assert.match(sessionSource, /router\.push\(\{ path: '\/analytics', query: \{ session: String\(ended\.id\) \} \}\)/)

  const loadingFinished = analyticsSource.indexOf('loading.value = false', analyticsSource.indexOf('async function loadAnalytics'))
  const chartRendered = analyticsSource.indexOf('if (shouldRender) await renderChart()', loadingFinished)
  assert.ok(loadingFinished >= 0 && chartRendered > loadingFinished)
})

test('live monitoring reports reconnecting and unavailable states', () => {
  assert.match(sessionSource, /socketStatus\.value = 'reconnecting'/)
  assert.match(sessionSource, /socketStatus\.value = 'unavailable'/)
  assert.match(sessionSource, /retryEngagementConnection/)
})

test('live presentation supports arrow keys and fullscreen projector mode', () => {
  assert.match(sessionSource, /presentationDirectionForKey/)
  assert.match(sessionSource, /document\.addEventListener\('keydown'/)
  assert.match(sessionSource, /requestFullscreen/)
  assert.match(sessionSource, /document\.exitFullscreen/)
  assert.match(sessionSource, /'Present fullscreen'/)
})

test('presentation library exposes retry and safe deletion actions', () => {
  assert.match(sessionSource, /retryPresentation/)
  assert.match(sessionSource, /deletePresentation/)
  assert.match(sessionSource, /presentation\.in_use/)
  assert.match(sessionSource, /uploadProgress/)
})

test('dashboard report action opens reports and unknown routes have a 404 page', () => {
  assert.match(dashboardSource, /to="\/reports"[^>]*>View Reports/)
  assert.match(routerSource, /path: '\/:pathMatch\(\.\*\)\*'/)
  assert.match(routerSource, /NotFoundView/)
})

test('class management exposes one-step room, camera, and subject setup', () => {
  assert.match(classManagementSource, /class-management\/quick-setup\//)
  assert.match(classesSource, />Quick Setup</)
  assert.match(classesSource, /v-for="camera in quickForm\.cameras"/)
  assert.match(classesSource, /Complete Setup/)
  assert.match(classesSource, /await createQuickSetup\(payload\)/)
})
