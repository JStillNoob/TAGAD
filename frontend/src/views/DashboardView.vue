<script setup>
import { computed, onMounted, ref } from 'vue'
import { currentUser } from '../auth'
import { fetchDashboardSummary } from '../dashboard'
import AppLayout from '../layouts/AppLayout.vue'

const dashboard = ref({
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

const greeting = computed(() => {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
})

const statCards = computed(() => [
  { label: 'Classrooms', value: dashboard.value.counts.classrooms, hint: 'Available to your account' },
  { label: 'Subjects', value: dashboard.value.counts.subjects, hint: 'Available to your account' },
  { label: 'Cameras', value: dashboard.value.counts.cameras, hint: 'Configured classroom cameras' },
  { label: 'Sessions Today', value: dashboard.value.counts.sessions_today, hint: 'Recorded today' },
])

const engagementBars = computed(() => {
  const distribution = dashboard.value.engagement.distribution
  return [
    { key: 'engaged', label: 'Engaged', color: '#2D3CC8' },
    { key: 'attentive', label: 'Attentive', color: '#10B981' },
    { key: 'confused', label: 'Confused', color: '#F59E0B' },
    { key: 'bored', label: 'Bored', color: '#F97316' },
    { key: 'disengaged', label: 'Disengaged', color: '#EF476F' },
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
    <div class="flex items-center justify-between gap-4 mb-6">
      <div>
        <h2 class="text-xl font-bold text-navy">{{ greeting }}, {{ displayName }} 👋</h2>
        <p class="text-sm text-gray-400 mt-0.5">Here is the latest data available to your account.</p>
      </div>
      <RouterLink to="/session" class="btn-primary">Start New Session</RouterLink>
    </div>

    <div v-if="error" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <button type="button" class="ml-2 font-semibold underline" @click="loadDashboard">Try again</button>
    </div>

    <div v-if="loading" class="page-card p-10 text-center text-sm text-gray-500">
      Loading dashboard…
    </div>

    <template v-else>
      <div class="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
        <div v-for="card in statCards" :key="card.label" class="stat-card">
          <p class="text-sm font-medium text-gray-500 mb-5">{{ card.label }}</p>
          <h3 class="text-3xl font-bold text-navy mb-1">{{ card.value }}</h3>
          <p class="text-xs text-gray-400">{{ card.hint }}</p>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div class="xl:col-span-2 page-card overflow-x-auto">
          <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <div>
              <h3 class="text-sm font-semibold text-navy">Recent Sessions</h3>
              <p class="text-xs text-gray-400 mt-0.5">Your five most recent accessible sessions</p>
            </div>
            <RouterLink to="/analytics" class="text-xs font-semibold text-brand">View all →</RouterLink>
          </div>
          <div v-if="!dashboard.recent_sessions.length" class="px-6 py-12 text-center text-sm text-gray-500">
            No classroom sessions have been recorded yet.
          </div>
          <table v-else class="w-full min-w-[760px] text-sm">
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

        <div class="flex flex-col gap-5">
          <div class="page-card p-5">
            <div class="flex items-start justify-between mb-4">
              <div>
                <h3 class="text-sm font-semibold text-navy">Today's Engagement</h3>
                <p v-if="dashboard.engagement.has_data" class="text-xs text-gray-400 mt-1">
                  {{ dashboard.engagement.total_detected }} detections · {{ dashboard.engagement.average_score }}% positive
                </p>
              </div>
              <span class="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-danger">
                {{ dashboard.alerts_today }} alerts
              </span>
            </div>
            <div v-if="dashboard.engagement.has_data" class="space-y-3.5">
              <div v-for="item in engagementBars" :key="item.key">
                <div class="flex justify-between text-xs mb-1.5">
                  <span class="font-medium text-gray-600">{{ item.label }}</span>
                  <span class="font-semibold" :style="{ color: item.color }">{{ item.percentage }}%</span>
                </div>
                <div class="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                  <div class="h-full rounded-full" :style="{ width: `${item.percentage}%`, background: item.color }"></div>
                </div>
              </div>
            </div>
            <p v-else class="py-8 text-center text-sm text-gray-500">
              No engagement data has been recorded today.
            </p>
          </div>

          <div class="page-card p-5">
            <h3 class="text-sm font-semibold text-navy mb-4">Quick Actions</h3>
            <div class="space-y-1 text-sm">
              <RouterLink to="/session" class="block rounded-lg px-3 py-2.5 text-gray-600 hover:bg-gray-50">Start Monitoring</RouterLink>
              <RouterLink to="/reports" class="block rounded-lg px-3 py-2.5 text-gray-600 hover:bg-gray-50">View Reports</RouterLink>
              <RouterLink to="/classes" class="block rounded-lg px-3 py-2.5 text-gray-600 hover:bg-gray-50">View Classes</RouterLink>
            </div>
          </div>
        </div>
      </div>
    </template>
  </AppLayout>
</template>
