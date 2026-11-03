import test from 'node:test'
import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'

const routerSource = await readFile(new URL('../src/router/index.js', import.meta.url), 'utf8')
const layoutSource = await readFile(new URL('../src/layouts/AppLayout.vue', import.meta.url), 'utf8')
const dashboardSource = await readFile(new URL('../src/views/DashboardView.vue', import.meta.url), 'utf8')
const sessionSource = await readFile(new URL('../src/views/SessionView.vue', import.meta.url), 'utf8')
const analyticsSource = await readFile(new URL('../src/views/AnalyticsView.vue', import.meta.url), 'utf8')
const stylesSource = await readFile(new URL('../src/assets/main.css', import.meta.url), 'utf8')
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

test('organization administrators and teachers share the new organization UI', () => {
  assert.match(layoutSource, /\["system_admin", "org_admin", "teacher"\]\.includes/)
  assert.match(dashboardSource, /\['org_admin', 'teacher'\]\.includes/)
  assert.match(sessionSource, /\['org_admin', 'teacher'\]\.includes/)
  assert.match(layoutSource, /\["system_admin", "org_admin"\]\.includes/)
  assert.match(routerSource, /path: '\/users'[\s\S]*roles: \['system_admin', 'org_admin'\]/)
})

test('page heroes share the compact Live Session dimensions', () => {
  assert.match(dashboardSource, /app-page-hero teacher-dashboard-hero/)
  assert.match(sessionSource, /app-page-hero teacher-session-hero/)
  assert.match(classesSource, /app-page-hero classes-hero/)
  assert.match(stylesSource, /\.app-page-hero \{ height: 190px; min-height: 190px; padding: 24px 32px; \}/)
  assert.match(stylesSource, /\.app-page-hero > img \{ max-height: 225px; \}/)
})

test('record tables keep rows visually distinct from their card background', () => {
  assert.match(dashboardSource, /class="app-data-table/)
  assert.match(analyticsSource, /class="app-data-table/)
  assert.match(classesSource, /class="app-data-table classes-data-table/)
  assert.match(stylesSource, /\.app-data-table thead \{ background:/)
  assert.match(stylesSource, /\.app-data-table tbody tr:nth-child\(even\)/)
  assert.match(stylesSource, /\.app-data-table tbody td \{ border-bottom:/)
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
  assert.match(sessionSource, /This classroom has no active cameras\. You can still start the session/)
  assert.match(sessionSource, /Prepare and start without cameras for now/)
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
  assert.match(analyticsSource, /class="analytics-stat-value(?: analytics-stat-value-alert)?"/)
  assert.match(stylesSource, /\.analytics-stat-value \{[^}]*text-align: right;/)

  for (const source of [reportsSource]) {
    const cardLines = source.split('\n').filter(line => line.includes('class="stat-card"'))
    assert.ok(cardLines.length > 0)
    for (const line of cardLines) {
      const valueClasses = [...line.matchAll(/class="([^"]*font-bold[^"]*)"/g)]
      assert.ok(valueClasses.length > 0)
      for (const [, classes] of valueClasses) assert.match(classes, /\btext-right\b/)
    }
  }
  assert.match(classesSource, /class="stat-card classes-stat-card"[\s\S]*?<strong class="text-right">/)
  assert.match(stylesSource, /\.classes-stat-card strong \{[^}]*text-align: right;/)
})

test('ending a session opens analytics and the stacked bar chart uses its data', () => {
  assert.match(sessionSource, /window\.confirm/)
  assert.match(sessionSource, /endSessionWithRecovery/)
  assert.match(sessionSource, /router\.push\(\{ path: '\/analytics', query: \{ session: String\(ended\.id\) \} \}\)/)

  assert.match(analyticsSource, /analytics\.value = await fetchSessionAnalytics\(selectedSessionId\.value\)/)
  assert.match(analyticsSource, /analytics\.value\.slides\.map\(slide => `Slide \$\{slide\.slide_number\}`\)/)
  assert.match(analyticsSource, /type: 'bar'/)
  assert.match(analyticsSource, /tooltip: \{ callbacks: \{ label: context => `\$\{context\.dataset\.label\}: \$\{context\.parsed\.y\}%` \} \}/)
  assert.match(analyticsSource, /<canvas ref="chartCanvas"/)
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
  assert.match(classesSource, /src="\/illustrations\/classes-hero\.png"/)
  assert.match(classesSource, /class="app-page-hero classes-hero page-card"/)
  assert.match(stylesSource, /\.classes-hero/)
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
