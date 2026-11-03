<script setup>
import { computed, onMounted, ref } from 'vue'
import { currentUser } from '../auth'
import { fetchDashboardSummary } from '../dashboard'
import AppLayout from '../layouts/AppLayout.vue'

const dashboard = ref({
  platform: {
    organizations: 0,
    active_organizations: 0,
    organization_admins: 0,
    organizations_without_admin: 0,
  },
  counts: { classrooms: 0, subjects: 0, cameras: 0, sessions_today: 0 },
  recent_sessions: [],
  engagement: {
    has_data: false,
    total_detected: 0,
    average_score: null,
    distribution: { engaged: 0, attentive: 0, confused: 0, bored: 0, disengaged: 0 },
  },
  alerts_today: 0,
})
const loading = ref(true)
const error = ref('')

const displayName = computed(() => {
  const fullName = [currentUser.value?.first_name, currentUser.value?.last_name]
    .filter(Boolean)
    .join(' ')
  return fullName || currentUser.value?.username || 'User'
})
const isSystemAdmin = computed(() => currentUser.value?.role === 'system_admin')
const isTeacher = computed(() => ['org_admin', 'teacher'].includes(currentUser.value?.role))

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
})

const statCards = computed(() => [
  { icon: 'classroom', label: 'Classrooms', value: dashboard.value.counts.classrooms, hint: 'Available to your account' },
  { icon: 'book', label: 'Subjects', value: dashboard.value.counts.subjects, hint: 'Available to your account' },
  { icon: 'camera', label: 'Cameras', value: dashboard.value.counts.cameras, hint: 'Configured classroom cameras' },
  { icon: 'calendar', label: 'Sessions Today', value: dashboard.value.counts.sessions_today, hint: 'Recorded today' },
])

const platformCards = computed(() => [
  { icon: 'building', label: 'Organizations', value: dashboard.value.platform.organizations, hint: 'Organizations not archived', to: '/organizations' },
  { icon: 'layers', label: 'Active Organizations', value: dashboard.value.platform.active_organizations, hint: 'Currently enabled', to: '/organizations' },
  { icon: 'users', label: 'Organization Admins', value: dashboard.value.platform.organization_admins, hint: 'Active organization administrators', to: '/users' },
  { icon: 'user-plus', label: 'Need an Administrator', value: dashboard.value.platform.organizations_without_admin, hint: 'Active organizations without an administrator', to: '/users' },
])

const engagementBars = computed(() => {
  const distribution = dashboard.value.engagement.distribution
  return [
    { key: 'engaged', label: 'Engaged', color: 'linear-gradient(180deg, var(--primary), var(--primary-dark))', textColor: 'var(--primary-dark)' },
    { key: 'attentive', label: 'Attentive', color: 'var(--state-attentive)', textColor: 'var(--primary-dark)' },
    { key: 'confused', label: 'Confused', color: 'var(--state-confused)', textColor: 'var(--text-muted)' },
    { key: 'bored', label: 'Bored', color: 'var(--state-bored)', textColor: 'var(--text-muted)' },
    { key: 'disengaged', label: 'Disengaged', color: 'var(--state-disengaged)', textColor: 'var(--text)' },
  ].map((item) => ({ ...item, percentage: distribution[item.key] }))
})

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  }).format(new Date(`${value}T00:00:00`))
}

function formatDuration(minutes) {
  if (minutes === null) return '—'
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return hours ? `${hours}h ${String(remainder).padStart(2, '0')}m` : `${remainder}m`
}

async function loadDashboard() {
  loading.value = true
  error.value = ''
  try {
    dashboard.value = await fetchDashboardSummary()
  } catch (requestError) {
    error.value = requestError.message
  } finally {
    loading.value = false
  }
}

onMounted(loadDashboard)
</script>

<template>
  <AppLayout page-title="Dashboard">
    <div v-if="isTeacher" class="app-page-hero teacher-dashboard-hero page-card mb-6">
      <div class="teacher-dashboard-hero-copy">
        <h2>{{ greeting }}, {{ displayName }}!</h2>
        <p>Here is the latest data available to your account.</p>
        <RouterLink to="/session" class="btn-primary"><span class="text-xl leading-none" aria-hidden="true">+</span> Start New Session</RouterLink>
      </div>
      <img class="teacher-dashboard-hero-art" src="/illustrations/teacher-hero.png" alt="" aria-hidden="true">
    </div>
    <div v-else class="app-page-hero flex items-center justify-between gap-4 mb-6" :class="isSystemAdmin ? 'platform-hero' : 'dashboard-hero'">
      <div>
        <h2 class="text-xl font-bold text-navy">{{ isSystemAdmin ? 'Platform overview' : `${greeting}, ${displayName}` }}</h2>
        <p class="text-sm text-gray-400 mt-0.5">{{ isSystemAdmin ? 'Create organizations and assign their administrators.' : 'Here is the latest data available to your account.' }}</p>
      </div>
      <img v-if="isSystemAdmin" class="platform-hero-art" src="/illustrations/platform-hero.png" alt="" aria-hidden="true">
      <RouterLink :to="isSystemAdmin ? '/organizations' : '/session'" class="btn-primary">{{ isSystemAdmin ? 'Manage Organizations' : 'Start New Session' }}</RouterLink>
    </div>

    <div v-if="error" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <button type="button" class="ml-2 font-semibold underline" @click="loadDashboard">Try again</button>
    </div>

    <div v-if="loading" class="page-card p-10 text-center text-sm text-gray-500">
      Loading dashboard…
    </div>

    <template v-else-if="isSystemAdmin">
      <div class="platform-stats grid grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
        <RouterLink v-for="card in platformCards" :key="card.label" :to="card.to" :aria-label="`View ${card.label}`" class="platform-stat-card stat-card">
          <div class="platform-stat-heading">
            <span class="platform-stat-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <template v-if="card.icon === 'building'">
                  <path d="M4 21V4.5A1.5 1.5 0 0 1 5.5 3h13A1.5 1.5 0 0 1 20 4.5V21M2.5 21h19M8 7h2m4 0h2M8 11h2m4 0h2M8 15h2m4 0h2M10 21v-3h4v3" />
                </template>
                <template v-else-if="card.icon === 'layers'">
                  <path d="m12 2.5 9 5.2-9 5.2-9-5.2 9-5.2ZM3 12l9 5.2 9-5.2M3 16.5l9 5.2 9-5.2" />
                </template>
                <template v-else-if="card.icon === 'users'">
                  <circle cx="9" cy="8" r="3" /><path d="M2.5 20v-1a5.5 5.5 0 0 1 11 0v1h-11Z" /><circle cx="17.5" cy="8" r="2.5" /><path d="M15.5 15a5 5 0 0 1 6 4.9V20h-6" />
                </template>
                <template v-else>
                  <circle cx="9" cy="8" r="3" /><path d="M2.5 20v-1a5.5 5.5 0 0 1 11 0v1h-11ZM18 5v7m-3.5-3.5h7" />
                </template>
              </svg>
            </span>
            <p class="text-sm font-medium text-gray-500">{{ card.label }}</p>
          </div>
          <h3 class="text-3xl font-bold text-navy mb-1 text-right">{{ card.value }}</h3>
          <p class="text-xs text-gray-400">{{ card.hint }}</p>
        </RouterLink>
      </div>

      <div class="platform-links grid gap-5 md:grid-cols-2">
        <RouterLink to="/organizations" class="platform-link-card page-card p-6 hover:border-brand transition-colors">
          <h3 class="text-base font-semibold text-navy">Organizations</h3>
          <p class="mt-2 text-sm text-gray-500">Add, update, archive, or restore organizations.</p>
          <div class="platform-link-body">
            <img src="/illustrations/organizations.png" alt="" aria-hidden="true">
            <ul>
              <li v-for="item in ['Create new organizations', 'Update organization details', 'Archive or restore organizations']" :key="item">
                <span class="platform-check-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 4.5 4.5L19 7" /></svg></span>
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>
          <span class="platform-link-indicator">Open organizations <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" /></svg></span>
        </RouterLink>
        <RouterLink to="/users" class="platform-link-card page-card p-6 hover:border-brand transition-colors">
          <h3 class="text-base font-semibold text-navy">Organization Administrators</h3>
          <p class="mt-2 text-sm text-gray-500">Create the administrator account responsible for each organization’s setup.</p>
          <div class="platform-link-body">
            <img src="/illustrations/administrators.png" alt="" aria-hidden="true">
            <ul>
              <li v-for="item in ['Assign organization admins', 'Manage administrator access', 'Maintain setup and permissions']" :key="item">
                <span class="platform-check-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 4.5 4.5L19 7" /></svg></span>
                <span>{{ item }}</span>
              </li>
            </ul>
          </div>
          <span class="platform-link-indicator">Open administrators <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14m-6-6 6 6-6 6" /></svg></span>
        </RouterLink>
      </div>
    </template>

    <template v-else>
      <div :class="isTeacher ? 'teacher-dashboard' : ''">
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-6" :class="isTeacher ? 'teacher-stats' : ''">
        <div v-for="card in statCards" :key="card.label" class="stat-card" :class="isTeacher ? `teacher-stat-card teacher-stat-${card.icon}` : ''">
          <span v-if="isTeacher" class="teacher-stat-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
              <template v-if="card.icon === 'classroom'"><path d="M3 4h18v13H3zM8 21l4-4 4 4M8 9h8M8 12h5" /></template>
              <template v-else-if="card.icon === 'book'"><path d="M12 6C9.5 4.5 6.5 4 3 4v14c3.5 0 6.5.5 9 2 2.5-1.5 5.5-2 9-2V4c-3.5 0-6.5.5-9 2Zm0 0v14" /></template>
              <template v-else-if="card.icon === 'camera'"><rect x="3" y="6" width="13" height="12" rx="2" /><path d="m16 10 5-3v10l-5-3" /></template>
              <template v-else><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M7 3v4m10-4v4M3 10h18m-13 4h4" /></template>
            </svg>
          </span>
          <div :class="isTeacher ? 'teacher-stat-copy' : ''">
            <p class="text-sm font-medium text-gray-500 mb-5">{{ card.label }}</p>
            <h3 class="text-3xl font-bold text-navy mb-1 text-right">{{ card.value }}</h3>
            <p class="text-xs text-gray-400">{{ card.hint }}</p>
          </div>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-3 gap-6" :class="isTeacher ? 'teacher-dashboard-grid' : ''">
        <div class="xl:col-span-2 page-card overflow-x-auto" :class="isTeacher ? 'teacher-recent-sessions' : ''">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div class="teacher-panel-heading">
              <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg></span>
              <div>
              <h3 class="text-sm font-semibold text-navy">Recent Sessions</h3>
              <p class="text-xs text-gray-400 mt-0.5">Your five most recent accessible sessions</p>
              </div>
            </div>
            <RouterLink to="/analytics" class="text-xs font-semibold text-brand">View all →</RouterLink>
          </div>
          <div v-if="!dashboard.recent_sessions.length" class="px-6 py-12 text-center text-sm text-gray-500">
            <img v-if="isTeacher" class="teacher-sessions-empty-art" src="/illustrations/teacher-sessions-empty.png" alt="" aria-hidden="true">
            <p>No classroom sessions have been recorded yet.</p>
          </div>
          <table v-else class="app-data-table w-full min-w-[760px] text-sm" :class="isTeacher ? 'teacher-sessions-table' : ''">
            <thead>
              <tr class="border-b border-gray-100">
                <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase">Subject</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase">Class</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase">Date</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase">Duration</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase">Avg. Eng.</th>
                <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase">Status</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="session in dashboard.recent_sessions" :key="session.id" class="hover:bg-gray-50">
                <td class="px-6 py-3.5 font-medium text-navy">
                  {{ session.subject_name }}
                  <span class="block text-xs font-normal text-gray-400">{{ session.subject_code }}</span>
                </td>
                <td class="px-6 py-3.5 text-gray-500">{{ session.classroom }}</td>
                <td class="px-6 py-3.5 text-gray-500">{{ formatDate(session.date) }}</td>
                <td class="px-6 py-3.5 text-gray-500">{{ formatDuration(session.duration_minutes) }}</td>
                <td class="px-6 py-3.5 font-semibold text-brand">
                  {{ session.average_engagement === null ? '—' : `${session.average_engagement}%` }}
                </td>
                <td class="px-6 py-3.5">
                  <span :class="session.status === 'completed' ? 'badge-engaged' : 'badge-attentive'">
                    {{ session.status === 'completed' ? 'Completed' : 'Ongoing' }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex flex-col gap-5" :class="isTeacher ? 'teacher-side-panels' : ''">
          <div class="page-card p-5" :class="isTeacher ? 'teacher-engagement-panel' : ''">
            <div class="flex items-start justify-between mb-4">
              <div class="teacher-panel-heading">
                <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m13 2-8 11h6l-1 9 9-12h-6V2Z" /></svg></span>
                <div>
                <h3 class="text-sm font-semibold text-navy">Today's Engagement</h3>
                <p v-if="dashboard.engagement.has_data" class="text-xs text-gray-400 mt-1">
                  {{ dashboard.engagement.total_detected }} detections · {{ dashboard.engagement.average_score }}% positive
                </p>
                </div>
              </div>
              <span class="teacher-alert-badge rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-danger">
                {{ dashboard.alerts_today }} alerts
              </span>
            </div>
            <div v-if="dashboard.engagement.has_data" class="space-y-3.5">
              <div v-for="item in engagementBars" :key="item.key">
                <div class="flex justify-between text-xs mb-1.5">
                  <span class="font-medium text-gray-600">{{ item.label }}</span>
                  <span class="font-semibold" :style="{ color: item.textColor }">{{ item.percentage }}%</span>
                </div>
                <div class="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div class="h-full rounded-full" :style="{ width: `${item.percentage}%`, background: item.color }"></div>
                </div>
              </div>
            </div>
            <div v-else class="teacher-engagement-empty py-8 text-center text-sm text-gray-500">
              <img v-if="isTeacher" src="/illustrations/teacher-engagement-empty.png" alt="" aria-hidden="true">
              <p>No engagement data has been recorded today.</p>
            </div>
          </div>

          <div class="page-card p-5" :class="isTeacher ? 'teacher-actions-panel' : ''">
            <div class="teacher-panel-heading mb-4">
              <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5m-18 5 9 5 9-5" /></svg></span>
              <h3 class="text-sm font-semibold text-navy">Quick Actions</h3>
            </div>
            <div class="space-y-1 text-sm teacher-action-list">
              <RouterLink to="/session" class="block rounded-lg px-3 py-2.5 text-gray-600 hover:bg-gray-50">Start Monitoring<span v-if="isTeacher" class="teacher-action-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"><path d="m7 4 13 8-13 8V4Z" /></svg></span><span v-if="isTeacher" class="teacher-action-arrow" aria-hidden="true">→</span></RouterLink>
              <RouterLink to="/reports" class="block rounded-lg px-3 py-2.5 text-gray-600 hover:bg-gray-50">View Reports<span v-if="isTeacher" class="teacher-action-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20h3v-6H4v6Zm6 0h3V9h-3v11Zm6 0h3V4h-3v16Z" /></svg></span><span v-if="isTeacher" class="teacher-action-arrow" aria-hidden="true">→</span></RouterLink>
              <RouterLink to="/classes" class="block rounded-lg px-3 py-2.5 text-gray-600 hover:bg-gray-50">View Classes<span v-if="isTeacher" class="teacher-action-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4h18v13H3zM8 21l4-4 4 4" /></svg></span><span v-if="isTeacher" class="teacher-action-arrow" aria-hidden="true">→</span></RouterLink>
            </div>
          </div>
        </div>
      </div>
      </div>
    </template>
  </AppLayout>
</template>
