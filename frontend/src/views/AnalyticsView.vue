<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Chart, registerables } from 'chart.js'
import AppLayout from '../layouts/AppLayout.vue'
import { analyticsCsvUrl, fetchAnalyticsSessions, fetchSessionAnalytics } from '../analytics'
import { currentTheme } from '../theme'

Chart.register(...registerables)

const route = useRoute()

const categories = [
  { key: 'engaged', label: 'Engaged', color: '#2D3CC8' },
  { key: 'attentive', label: 'Attentive', color: '#10B981' },
  { key: 'confused', label: 'Confused', color: '#F59E0B' },
  { key: 'bored', label: 'Bored', color: '#F97316' },
  { key: 'disengaged', label: 'Disengaged', color: '#EF476F' },
]
const sessions = ref([])
const selectedSessionId = ref('')
const analytics = ref(null)
const loading = ref(true)
const error = ref('')
const chartCanvas = ref(null)
let chart = null

function formatDate(value) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${value}T00:00:00`)) : '—'
}

function formatTime(value) {
  return value ? new Intl.DateTimeFormat(undefined, { timeStyle: 'short' }).format(new Date(value)) : '—'
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined) return '—'
  const total = Math.max(0, Math.round(seconds))
  const hours = Math.floor(total / 3600)
  const minutes = Math.floor((total % 3600) / 60)
  const remainingSeconds = total % 60
  if (hours) return `${hours}h ${minutes}m`
  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`
}

function percentage(value) {
  return value === null || value === undefined ? '—' : `${value}%`
}

function sessionLabel(session) {
  const status = session.status === 'ongoing' ? ' · Ongoing' : ''
  return `${session.subject_code} — ${session.subject_name} · ${formatDate(session.session_date)}${status}`
}

function engagementColor(value) {
  if (value === null || value === undefined) return '#94a3b8'
  if (value >= 80) return '#2D3CC8'
  if (value >= 65) return '#465FF1'
  return '#6B7280'
}

function destroyChart() {
  if (chart) chart.destroy()
  chart = null
}

async function renderChart() {
  destroyChart()
  if (!analytics.value?.has_data || !analytics.value.slides.length) return
  await nextTick()
  if (!chartCanvas.value) return
  const dark = currentTheme.value === 'dark'
  const labelColor = dark ? '#CBD5E1' : '#94A3B8'
  const gridColor = dark ? '#293548' : '#F1F5F9'
  chart = new Chart(chartCanvas.value, {
    type: 'bar',
    data: {
      labels: analytics.value.slides.map(slide => `Slide ${slide.slide_number}`),
      datasets: categories.map(category => ({
        label: category.label,
        data: analytics.value.slides.map(slide => slide[category.key] ?? 0),
        backgroundColor: category.color,
        categoryPercentage: 0.6,
        barPercentage: 1,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { stacked: true, grid: { display: false }, ticks: { color: labelColor } },
        y: { stacked: true, max: 100, grid: { color: gridColor }, ticks: { color: labelColor, callback: value => `${value}%` } },
      },
    },
  })
}

async function loadAnalytics() {
  if (!selectedSessionId.value) return
  loading.value = true
  error.value = ''
  let shouldRender = false
  try {
    analytics.value = await fetchSessionAnalytics(selectedSessionId.value)
    shouldRender = true
  } catch (requestError) {
    analytics.value = null
    destroyChart()
    error.value = requestError.message || 'Unable to load session analytics.'
  } finally {
    loading.value = false
  }
  if (shouldRender) await renderChart()
}

async function loadSessions() {
  loading.value = true
  error.value = ''
  try {
    sessions.value = await fetchAnalyticsSessions()
    if (sessions.value.length) {
      const requested = sessions.value.find(session => session.id === Number(route.query.session))
      selectedSessionId.value = String(requested?.id || sessions.value[0].id)
      await loadAnalytics()
    } else {
      analytics.value = null
      loading.value = false
    }
  } catch (requestError) {
    error.value = requestError.message || 'Unable to load analytics sessions.'
    loading.value = false
  }
}

watch(() => route.query.session, async (value) => {
  const requested = sessions.value.find(session => session.id === Number(value))
  if (requested && String(requested.id) !== selectedSessionId.value) {
    selectedSessionId.value = String(requested.id)
    await loadAnalytics()
  }
})
watch(currentTheme, renderChart)

onMounted(loadSessions)
onBeforeUnmount(destroyChart)
</script>

<template>
  <AppLayout page-title="Post-Lesson Analytics">
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
      <div class="min-w-0">
        <div class="flex flex-col sm:flex-row sm:items-center gap-3">
          <label for="session-select" class="text-sm font-semibold text-gray-600">Session:</label>
          <select
            id="session-select"
            v-model="selectedSessionId"
            class="min-w-0 sm:min-w-[420px] border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none bg-white text-navy focus:border-brand"
            :disabled="loading || !sessions.length"
            @change="loadAnalytics"
          >
            <option v-for="session in sessions" :key="session.id" :value="String(session.id)">{{ sessionLabel(session) }}</option>
          </select>
        </div>
        <p v-if="analytics" class="text-xs text-gray-400 mt-2 sm:ml-20">
          {{ analytics.session.classroom }} · {{ analytics.session.teacher_name }} ·
          {{ formatTime(analytics.session.started_at) }}–{{ formatTime(analytics.session.ended_at) }}
        </p>
      </div>
      <a
        v-if="selectedSessionId"
        :href="analyticsCsvUrl(selectedSessionId)"
        class="btn-primary self-start lg:self-auto"
        download
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        Download CSV
      </a>
    </div>

    <div v-if="loading" class="page-card p-12 text-center text-sm text-gray-400">Loading session analytics…</div>
    <div v-else-if="error" class="page-card p-12 text-center">
      <p class="text-sm text-red-600" role="alert">{{ error }}</p>
      <button class="mt-4 px-4 py-2 rounded-lg bg-brand text-white text-sm" @click="loadSessions">Try again</button>
    </div>
    <div v-else-if="!sessions.length" class="page-card p-12 text-center">
      <h3 class="font-semibold text-navy">No classroom sessions yet</h3>
      <p class="text-sm text-gray-400 mt-2">Start and complete a classroom session to view analytics here.</p>
    </div>

    <template v-else-if="analytics">
      <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-5 mb-6">
        <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Students Detected</div><div class="text-3xl font-bold text-navy">{{ analytics.summary.students_detected }}</div><div class="text-xs text-gray-400 mt-1">Highest simultaneous count</div></div>
        <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Session Duration</div><div class="text-3xl font-bold text-navy">{{ formatDuration(analytics.session.duration_seconds) }}</div><div class="text-xs text-gray-400 mt-1">{{ analytics.session.slides_covered }} slides covered</div></div>
        <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Avg. Engagement</div><div class="text-3xl font-bold" style="color:#2D3CC8">{{ percentage(analytics.summary.average_engagement) }}</div><div class="text-xs text-gray-400 mt-1"><template v-if="analytics.summary.engagement_change !== null">{{ analytics.summary.engagement_change >= 0 ? '▲' : '▼' }} {{ Math.abs(analytics.summary.engagement_change) }}% vs previous session</template><template v-else>No previous comparison</template></div></div>
        <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Most Confused Slide</div><div class="text-2xl font-bold" style="color:#D97706">{{ analytics.insights ? `Slide ${analytics.insights.most_confusion.slide_number}` : '—' }}</div><div class="text-xs text-gray-400 mt-1">{{ analytics.insights ? `${analytics.insights.most_confusion.percentage}% confused` : 'No engagement data' }}</div></div>
        <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Total Detections</div><div class="text-3xl font-bold text-navy">{{ analytics.summary.total_detections }}</div><div class="text-xs text-gray-400 mt-1">Across all samples</div></div>
        <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Avg. Confidence</div><div class="text-3xl font-bold text-navy">{{ percentage(analytics.summary.average_confidence) }}</div><div class="text-xs text-gray-400 mt-1">Detection-weighted score</div></div>
      </div>

      <div v-if="!analytics.has_data" class="page-card p-10 mb-6 text-center">
        <h3 class="font-semibold text-navy">No engagement data for this session</h3>
        <p class="text-sm text-gray-400 mt-2">Session and slide timing are available, but engagement results will appear after the detection model submits summaries.</p>
      </div>

      <div v-else class="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <div class="xl:col-span-2 page-card p-6">
          <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3 mb-5">
            <div><h3 class="font-semibold text-navy">Engagement per Slide</h3><p class="text-xs text-gray-400 mt-0.5">Stacked breakdown by engagement state</p></div>
            <div class="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
              <span v-for="category in categories" :key="category.key" class="flex items-center gap-1.5"><span class="w-3 h-3 rounded-sm" :style="{ background: category.color }"></span>{{ category.label }}</span>
            </div>
          </div>
          <div class="relative h-[300px]"><canvas ref="chartCanvas"></canvas></div>
        </div>

        <div class="page-card p-5">
          <h3 class="font-semibold text-sm mb-4 text-navy">Key Insights</h3>
          <div class="space-y-3">
            <div class="insight-card-engaged p-3 rounded-xl border-l-4" style="border-color:#2D3CC8"><p class="text-xs font-semibold" style="color:#7083FF">Highest Engagement</p><p class="text-sm font-bold mt-0.5 text-navy">Slide {{ analytics.insights.highest_engagement.slide_number }} — {{ analytics.insights.highest_engagement.percentage }}%</p><p class="text-xs text-gray-400 mt-0.5">{{ analytics.insights.highest_engagement.title }}</p></div>
            <div class="insight-card-confused p-3 rounded-xl border-l-4" style="border-color:#F59E0B"><p class="text-xs font-semibold text-amber-600">Most Confusion</p><p class="text-sm font-bold mt-0.5 text-navy">Slide {{ analytics.insights.most_confusion.slide_number }} — {{ analytics.insights.most_confusion.percentage }}%</p><p class="text-xs text-gray-400 mt-0.5">{{ analytics.insights.most_confusion.title }}</p></div>
            <div class="insight-card-disengaged p-3 rounded-xl border-l-4" style="border-color:#EF476F"><p class="text-xs font-semibold text-rose-600">Most Disengaged</p><p class="text-sm font-bold mt-0.5 text-navy">Slide {{ analytics.insights.most_disengaged.slide_number }} — {{ analytics.insights.most_disengaged.percentage }}%</p><p class="text-xs text-gray-400 mt-0.5">{{ analytics.insights.most_disengaged.title }}</p></div>
            <div class="p-3 rounded-xl border-l-4 border-gray-200 bg-gray-50"><p class="text-xs font-semibold text-gray-400">Recommendation</p><p class="text-xs text-gray-600 mt-1">{{ analytics.insights.recommendation }}</p></div>
          </div>
        </div>
      </div>

      <div class="page-card">
        <div class="px-6 py-5 border-b border-gray-50"><h3 class="font-semibold text-sm text-navy">Slide-by-Slide Breakdown</h3></div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-gray-50"><th v-for="heading in ['Slide', 'Topic', 'Timestamp', 'Duration', 'Detected', 'Engaged', 'Attentive', 'Confused', 'Bored', 'Disengaged']" :key="heading" class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">{{ heading }}</th></tr></thead>
            <tbody class="divide-y divide-gray-50">
              <tr v-if="!analytics.slides.length"><td colspan="10" class="px-6 py-10 text-center text-gray-400">No slide activity was recorded.</td></tr>
              <tr v-for="row in analytics.slides" :key="row.slide_id" class="hover:bg-gray-50/50 transition-colors">
                <td class="px-6 py-3 text-gray-400 font-mono text-xs">{{ String(row.slide_number).padStart(2, '0') }}</td>
                <td class="px-6 py-3 font-medium text-navy">{{ row.title }}</td>
                <td class="px-6 py-3 text-gray-400 whitespace-nowrap">{{ formatTime(row.entered_at) }}</td>
                <td class="px-6 py-3 text-gray-500">{{ formatDuration(row.duration_seconds) }}</td>
                <td class="px-6 py-3 text-gray-500">{{ row.has_data ? row.detected : '—' }}</td>
                <td class="px-6 py-3 font-semibold" :style="{ color: engagementColor(row.engaged) }">{{ percentage(row.engaged) }}</td>
                <td class="px-6 py-3 text-gray-500">{{ percentage(row.attentive) }}</td>
                <td class="px-6 py-3" :class="row.confused >= 30 ? 'font-semibold text-amber-600' : 'text-gray-500'">{{ percentage(row.confused) }}</td>
                <td class="px-6 py-3 text-gray-500">{{ percentage(row.bored) }}</td>
                <td class="px-6 py-3" :class="row.disengaged >= 15 ? 'font-semibold text-rose-600' : 'text-gray-500'">{{ percentage(row.disengaged) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </AppLayout>
</template>
