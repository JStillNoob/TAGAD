import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const routerSource = await readFile(new URL('../src/router/index.js', import.meta.url), 'utf8')
const layoutSource = await readFile(new URL('../src/layouts/AppLayout.vue', import.meta.url), 'utf8')
const dashboardSource = await readFile(new URL('../src/views/DashboardView.vue', import.meta.url), 'utf8')
const sessionSource = await readFile(new URL('../src/views/SessionView.vue', import.meta.url), 'utf8')
const analyticsSource = await readFile(new URL('../src/views/AnalyticsView.vue', import.meta.url), 'utf8')
const reportsSource = await readFile(new URL('../src/views/ReportsView.vue', import.meta.url), 'utf8')
const classesSource = await readFile(new URL('../src/views/StudentsView.vue', import.meta.url), 'utf8')
const classManagementSource = await readFile(new URL('../src/classManagement.js', import.meta.url), 'utf8')
const userManagementSource = await readFile(new URL('../src/views/UserManagementView.vue', import.meta.url), 'utf8')
const organizationsSource = await readFile(new URL('../src/views/OrganizationsView.vue', import.meta.url), 'utf8')

test('authenticated shell keeps its core navigation and logout actions', () => {
  assert.match(routerSource, /path: '\/dashboard'/)
  assert.match(layoutSource, /to="\/settings"/)
  assert.match(layoutSource, /@click="handleLogout"/)
})

test('system administrators have a dedicated platform management UI', () => {
  assert.match(routerSource, /path: '\/organizations'/)
  assert.match(routerSource, /roles: \['system_admin'\]/)
  assert.match(layoutSource, /v-if="isSystemAdmin"[\s\S]*to="\/organizations"/)
  assert.match(layoutSource, /v-if="!isSystemAdmin"[\s\S]*to="\/session"/)
  assert.doesNotMatch(layoutSource, /Advanced Django admin/)
  assert.match(dashboardSource, /Platform overview/)
  assert.match(dashboardSource, /Organization Administrators/)
  assert.match(dashboardSource, /Create organizations and assign their administrators/)
  assert.match(routerSource, /path: '\/analytics'[\s\S]*roles: \['org_admin', 'teacher'\]/)
  assert.match(routerSource, /path: '\/classes'[\s\S]*roles: \['org_admin', 'teacher'\]/)
  assert.match(routerSource, /path: '\/reports'[\s\S]*roles: \['org_admin', 'teacher'\]/)
  assert.match(organizationsSource, /Add Organization/)
  assert.match(organizationsSource, /saveOrganization/)
  assert.match(userManagementSource, /Assign an administrator to each organization/)
})

test('live session connects to engagement WebSocket and exposes the development simulator', () => {
  assert.match(sessionSource, /new WebSocket/)
  assert.match(sessionSource, /simulateEngagement/)
  assert.match(sessionSource, /options\.simulator_enabled/)
  assert.match(sessionSource, /setInterval\(emitSimulation, 2000\)/)
})

test('live session automatically selects classroom cameras and provides bulk controls', () => {
  assert.match(sessionSource, /selectAllCameras\(\)\s+startCameraAvailability\(\)/)
  assert.match(sessionSource, /checkSessionCameraAvailability/)
  assert.match(sessionSource, /selectedCamerasAvailable/)
  assert.match(sessionSource, /@click="selectAllCameras">Select all/)
  assert.match(sessionSource, /@click="clearCameraSelection">Clear/)
  assert.match(sessionSource, /You can still start the session and use the development simulator/)
})

test('prepared session reuses the presentation screen before countdown starts', () => {
  assert.match(sessionSource, /Review mode · session timing and analytics have not started/)
  assert.match(sessionSource, /preparedSession.*Start Session/s)
  assert.match(sessionSource, /if \(preparedSession\.value && !activeSession\.value\)/)
})

test('active session shows independent official camera worker health', () => {
  assert.match(sessionSource, /Camera & Worker Health/)
  assert.match(sessionSource, /Simulator only/)
  assert.match(sessionSource, /Official analytics/)
  assert.doesNotMatch(sessionSource, /Diagnostics only/)
  assert.match(sessionSource, /fetchSessionCameraHealth/)
  assert.match(sessionSource, /simulatorAvailable/)
  assert.match(sessionSource, /Simulation is unavailable because this session has assigned camera sources/)
})

test('analytics labels pipeline, simulation, and historical mixed data', () => {
  assert.match(analyticsSource, /analytics\.data_source\.label/)
  assert.match(analyticsSource, /analytics\.data_source\.notice/)
  assert.match(analyticsSource, /analytics\.data_quality\.label/)
  assert.match(analyticsSource, /analytics\.summary\.classification_coverage/)
  assert.match(analyticsSource, /analytics\.summary\.unclassified_detections/)
  assert.match(analyticsSource, /Insights withheld/)
})

test('summary card values are right-aligned', () => {
  assert.match(dashboardSource, /<h3 class="[^"]*font-bold[^"]*text-right[^"]*"/)

  for (const source of [analyticsSource, reportsSource, classesSource]) {
    const cardLines = source.split('\n').filter(line => line.includes('class="stat-card"'))
    assert.ok(cardLines.length > 0)
    for (const line of cardLines) {
      const valueClasses = [...line.matchAll(/class="([^"]*font-bold[^"]*)"/g)]
      assert.ok(valueClasses.length > 0)
      for (const [, classes] of valueClasses) assert.match(classes, /\btext-right\b/)
    }
  }
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

test('administrative records use archive, restore, deactivation, and intentional deletion', () => {
  assert.match(classesSource, /lifecycleFilter/)
  assert.match(classesSource, /Archive classroom/)
  assert.match(classesSource, /restoreArchivedSubject/)
  assert.match(classesSource, /restoreArchivedCamera/)
  assert.match(sessionSource, /presentationLifecycle/)
  assert.match(sessionSource, /Delete permanently/)
  assert.match(sessionSource, /restoreArchivedPresentation/)
  assert.match(sessionSource, /restoreArchivedSession/)
  assert.match(organizationsSource, /archiveRecord/)
  assert.match(organizationsSource, /restoreRecord/)
  assert.match(userManagementSource, /Deactivate/)
})
