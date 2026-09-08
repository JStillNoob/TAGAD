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

test('ending a session opens its analytics and the chart renders after loading', () => {
  assert.match(sessionSource, /router\.push\(\{ path: '\/analytics', query: \{ session: String\(ended\.id\) \} \}\)/)

  const loadingFinished = analyticsSource.indexOf('loading.value = false', analyticsSource.indexOf('async function loadAnalytics'))
  const chartRendered = analyticsSource.indexOf('if (shouldRender) await renderChart()', loadingFinished)
  assert.ok(loadingFinished >= 0 && chartRendered > loadingFinished)
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
