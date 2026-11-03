<script setup>
import { onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import PaginationControls from '../components/PaginationControls.vue'
import { analyticsCsvUrl, fetchAnalyticsSessions, fetchSessionAnalytics } from '../analytics'

const route = useRoute()

const categories = [
  { key: 'engaged', label: 'Engaged', color: '#2D8FE8' },
  { key: 'attentive', label: 'Attentive', color: '#20C7A4' },
  { key: 'confused', label: 'Confused', color: '#F3B337' },
  { key: 'bored', label: 'Bored', color: '#E85591' },
  { key: 'disengaged', label: 'Disengaged', color: '#785BE5' },
]
const sessions = ref([])
const sessionCount = ref(0)
const sessionPage = ref(1)
const pageSize = 20
const selectedSessionId = ref('')
const analytics = ref(null)
const loading = ref(true)
const error = ref('')

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

function dataSourceClass(type) {
  return {
    pipeline: 'bg-emerald-50 text-emerald-700',
    simulator: 'bg-violet-50 text-violet-700',
    mixed: 'bg-red-50 text-red-700',
    none: 'bg-gray-100 text-gray-600',
  }[type] || 'bg-gray-100 text-gray-600'
}

function dataQualityClass(level) {
  return {
    good: 'border-emerald-200 bg-emerald-50 text-emerald-800',
    limited: 'border-amber-200 bg-amber-50 text-amber-800',
    insufficient: 'border-red-200 bg-red-50 text-red-800',
  }[level] || 'border-gray-200 bg-gray-50 text-gray-700'
}

function sessionLabel(session) {
  const status = session.status === 'ongoing' ? ' · Ongoing' : ''
  return `${session.subject_code} — ${session.subject_name} · ${formatDate(session.session_date)}${status}`
}

function engagementColor(value) {
  if (value === null || value === undefined) return 'var(--text-muted)'
  if (value >= 80) return 'var(--primary-dark)'
  if (value >= 65) return 'var(--primary-dark)'
  return 'var(--text-muted)'
}

function donutStyle(slide) {
  if (!slide.has_data) return { background: 'var(--border)' }
  const values = categories.map(category => Math.max(0, Number(slide[category.key]) || 0))
  const total = values.reduce((sum, value) => sum + value, 0)
  if (!total) return { background: 'var(--border)' }
  let position = 0
  const segments = categories.flatMap((category, index) => {
    if (!values[index]) return []
    const start = position
    position += values[index] / total * 100
    return `${category.color} ${start}% ${position}%`
  })
  return { background: `conic-gradient(from -90deg, ${segments.join(', ')})` }
}

function donutLabel(slide) {
  if (!slide.has_data) return `Slide ${slide.slide_number}: no classified engagement data`
  return `Slide ${slide.slide_number}: ${categories.map(category => `${category.label} ${percentage(slide[category.key])}`).join(', ')}`
}

async function loadAnalytics() {
  if (!selectedSessionId.value) return
  loading.value = true
  error.value = ''
  try {
    analytics.value = await fetchSessionAnalytics(selectedSessionId.value)
  } catch (requestError) {
    analytics.value = null
    error.value = requestError.message || 'Unable to load session analytics.'
  } finally {
    loading.value = false
  }
}

async function loadSessions(page = sessionPage.value) {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchAnalyticsSessions({ page })
    sessions.value = response.results
    sessionCount.value = response.count
    sessionPage.value = page
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
onMounted(loadSessions)
</script>

<template>
  <AppLayout page-title="Analytics">
    <div class="analytics-page">
    <div class="analytics-toolbar flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6">
      <div class="min-w-0">
        <div class="flex flex-col sm:flex-row sm:items-center gap-3">
          <label for="session-select" class="text-sm font-semibold text-gray-600">Session:</label>
          <select
            id="session-select"
            v-model="selectedSessionId"
            class="analytics-session-select min-w-0 sm:min-w-[420px] border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none bg-white text-navy focus:border-brand"
            :disabled="loading || !sessions.length"
            @change="loadAnalytics"
          >
            <option v-for="session in sessions" :key="session.id" :value="String(session.id)">{{ sessionLabel(session) }}</option>
          </select>
        </div>
        <div v-if="analytics" class="analytics-session-meta mt-2 flex flex-wrap items-center gap-2 text-xs text-gray-400 sm:ml-20">
          <span>
            {{ analytics.session.classroom }} · {{ analytics.session.teacher_name }} ·
            {{ formatTime(analytics.session.started_at) }}–{{ formatTime(analytics.session.ended_at) }}
          </span>
          <span class="rounded-full px-2 py-1 font-semibold" :class="dataSourceClass(analytics.data_source.type)">
            {{ analytics.data_source.label }}
          </span>
        </div>
      </div>
      <a
        v-if="selectedSessionId"
        :href="analyticsCsvUrl(selectedSessionId)"
        class="btn-primary analytics-download self-start lg:self-auto"
        download
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        Download CSV
      </a>
    </div>
    <PaginationControls class="analytics-pagination mb-6 page-card" :page="sessionPage" :count="sessionCount" :page-size="pageSize" :disabled="loading" @change="loadSessions" />

    <div v-if="loading" class="page-card p-12 text-center text-sm text-gray-400">Loading session analytics…</div>
    <div v-else-if="error" class="page-card p-12 text-center">
      <p class="text-sm text-red-600" role="alert">{{ error }}</p>
      <button class="btn-secondary mt-4" @click="loadSessions">Try again</button>
    </div>
    <div v-else-if="!sessions.length" class="page-card p-12 text-center">
      <h3 class="font-semibold text-navy">No classroom sessions yet</h3>
      <p class="text-sm text-gray-400 mt-2">Start and complete a classroom session to view analytics here.</p>
    </div>

    <template v-else-if="analytics">
      <div v-if="!analytics.data_source.official && analytics.data_source.type !== 'none'" class="analytics-source-notice mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
        {{ analytics.data_source.notice }}
      </div>
      <div class="analytics-quality mb-6 rounded-xl border px-4 py-3" :class="dataQualityClass(analytics.data_quality.level)" role="status">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M10.3 3.6 2.2 18a2 2 0 0 0 1.7 3h16.2a2 2 0 0 0 1.7-3L13.7 3.6a2 2 0 0 0-3.4 0Z" /><path d="M12 9v5m0 3h.01" /></svg>
        <div><p class="text-sm font-semibold">Data quality: {{ analytics.data_quality.label }}</p><p class="mt-1 text-xs">{{ analytics.data_quality.explanation }}</p></div>
      </div>
      <div class="analytics-stats grid grid-cols-2 md:grid-cols-4 gap-5 mb-6">
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="9" cy="8" r="3" /><circle cx="17" cy="9" r="2" /><path d="M3 19a6 6 0 0 1 12 0m-1.5-4.3A5 5 0 0 1 21 19" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Students Detected</div><div class="analytics-stat-value">{{ analytics.summary.students_detected }}</div><div class="analytics-stat-note">Highest simultaneous count</div></div></div>
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Session Duration</div><div class="analytics-stat-value">{{ formatDuration(analytics.session.duration_seconds) }}</div><div class="analytics-stat-note">{{ analytics.session.slides_covered }} slides covered</div></div></div>
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M2 12h4l2-6 4 12 2-6h8" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Avg. Engagement</div><div class="analytics-stat-value">{{ percentage(analytics.summary.average_engagement) }}</div><div class="analytics-stat-note"><template v-if="analytics.summary.engagement_change !== null">{{ analytics.summary.engagement_change >= 0 ? '▲' : '▼' }} {{ Math.abs(analytics.summary.engagement_change) }}% vs previous session</template><template v-else>No previous comparison</template></div></div></div>
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m3 10 9-6 9 6-9 6-9-6Z" /><path d="M6 12v6c3 2 9 2 12 0v-6M21 10v7" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Most Confused Slide</div><div class="analytics-stat-value analytics-stat-value-alert">{{ analytics.insights ? `Slide ${analytics.insights.most_confusion.slide_number}` : '—' }}</div><div class="analytics-stat-note">{{ analytics.insights ? `${analytics.insights.most_confusion.percentage}% confused` : 'No supported insight' }}</div></div></div>
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Total Detections</div><div class="analytics-stat-value">{{ analytics.summary.total_detections }}</div><div class="analytics-stat-note">Across all samples</div></div></div>
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5m-18 5 9 5 9-5" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Unclassified</div><div class="analytics-stat-value">{{ analytics.summary.unclassified_detections }}</div><div class="analytics-stat-note">Preserved as unknown, not disengaged</div></div></div>
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="13" width="4" height="8" rx="1" /><rect x="10" y="8" width="4" height="13" rx="1" /><rect x="17" y="3" width="4" height="18" rx="1" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Classification Coverage</div><div class="analytics-stat-value">{{ percentage(analytics.summary.classification_coverage) }}</div><div class="analytics-stat-note">{{ analytics.summary.monitoring_windows }} monitoring windows</div></div></div>
        <div class="stat-card analytics-stat-card"><span class="analytics-stat-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 8 4v6c0 5-3.2 8.2-8 10-4.8-1.8-8-5-8-10V6l8-4Z" /><path d="m8 12 3 3 5-6" /></svg></span><div class="analytics-stat-copy"><div class="analytics-stat-title">Avg. Confidence</div><div class="analytics-stat-value">{{ percentage(analytics.summary.average_confidence) }}</div><div class="analytics-stat-note">Detection-weighted score</div></div></div>
      </div>

      <div v-if="!analytics.has_data" class="page-card analytics-empty p-10 mb-6 text-center">
        <span class="analytics-empty-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 2h8l5 5v13a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Z" /><path d="M14 2v5h5M8 12h7m-7 4h5" /></svg></span>
        <h3 class="font-semibold text-navy">No engagement data for this session</h3>
        <p class="text-sm text-gray-400 mt-2">Session and slide timing are available, but no classified engagement results were submitted. Unclassified samples are shown above.</p>
      </div>

      <div v-else class="analytics-data-sections mb-6">
        <section class="page-card analytics-chart-panel p-6">
          <div class="analytics-chart-heading">
            <div><h3 class="font-semibold text-navy">Engagement per Slide</h3><p class="text-xs text-gray-400 mt-0.5">Distribution among classified samples</p></div>
            <div class="analytics-chart-legend" aria-label="Engagement categories">
              <span v-for="category in categories" :key="category.key" class="analytics-legend-item"><span class="analytics-legend-dot" :style="{ background: category.color }" aria-hidden="true"></span>{{ category.label }}</span>
            </div>
          </div>
          <div class="analytics-donut-grid">
            <div v-for="slide in analytics.slides" :key="slide.slide_id" class="analytics-donut-card">
              <div class="analytics-donut-title">Slide {{ slide.slide_number }}</div>
              <div class="analytics-donut-topic" :title="slide.title">{{ slide.title }}</div>
              <div class="analytics-donut" :style="donutStyle(slide)" role="img" :aria-label="donutLabel(slide)"><span class="analytics-donut-hole" aria-hidden="true"></span></div>
              <div class="analytics-donut-score">{{ slide.has_data ? percentage(slide.engaged) : '—' }}</div>
              <div class="analytics-donut-caption">{{ slide.has_data ? 'Engaged share' : 'No classified data' }}</div>
            </div>
          </div>
        </section>

        <section class="page-card analytics-insights p-5">
          <h3 class="font-semibold text-sm mb-4 text-navy">Key Insights</h3>
          <div v-if="analytics.insights" class="analytics-insight-grid">
            <div class="insight-card-engaged p-3 rounded-xl border-l-4" style="border-color:var(--primary-dark)"><p class="text-xs font-semibold" style="color:var(--primary-dark)">Highest Engagement</p><p class="text-sm font-bold mt-0.5 text-navy">Slide {{ analytics.insights.highest_engagement.slide_number }} — {{ analytics.insights.highest_engagement.percentage }}%</p><p class="text-xs text-gray-400 mt-0.5">{{ analytics.insights.highest_engagement.title }}</p></div>
            <div class="insight-card-confused p-3 rounded-xl border-l-4" style="border-color:var(--alert)"><p class="text-xs font-semibold text-amber-600">Most Confusion</p><p class="text-sm font-bold mt-0.5 text-navy">Slide {{ analytics.insights.most_confusion.slide_number }} — {{ analytics.insights.most_confusion.percentage }}%</p><p class="text-xs text-gray-400 mt-0.5">{{ analytics.insights.most_confusion.title }}</p></div>
            <div class="insight-card-disengaged p-3 rounded-xl border-l-4" style="border-color:var(--alert)"><p class="text-xs font-semibold text-rose-600">Most Disengaged</p><p class="text-sm font-bold mt-0.5 text-navy">Slide {{ analytics.insights.most_disengaged.slide_number }} — {{ analytics.insights.most_disengaged.percentage }}%</p><p class="text-xs text-gray-400 mt-0.5">{{ analytics.insights.most_disengaged.title }}</p></div>
            <div class="p-3 rounded-xl border-l-4 border-gray-200 bg-gray-50"><p class="text-xs font-semibold text-gray-400">Recommendation</p><p class="text-xs text-gray-600 mt-1">{{ analytics.insights.recommendation }}</p></div>
          </div>
          <div v-else class="rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800">
            <p class="font-semibold">Insights withheld</p>
            <p class="mt-1 text-xs leading-5">{{ analytics.data_quality.explanation }}</p>
          </div>
        </section>
      </div>

      <div class="page-card analytics-breakdown">
        <div class="analytics-breakdown-heading px-6 py-5 border-b border-gray-50"><span class="analytics-breakdown-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="16" rx="2" /><path d="M3 9h18M8 9v11" /></svg></span><h3 class="font-semibold text-sm text-navy">Slide-by-Slide Breakdown</h3></div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead><tr class="border-b border-gray-50"><th v-for="heading in ['Slide', 'Topic', 'Timestamp', 'Duration', 'Detected', 'Unclassified', 'Engaged', 'Attentive', 'Confused', 'Bored', 'Disengaged']" :key="heading" class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">{{ heading }}</th></tr></thead>
            <tbody class="divide-y divide-gray-50">
              <tr v-if="!analytics.slides.length"><td colspan="11" class="px-6 py-10 text-center text-gray-400">No slide activity was recorded.</td></tr>
              <tr v-for="row in analytics.slides" :key="row.slide_id" class="hover:bg-gray-50/50 transition-colors">
                <td class="px-6 py-3 text-gray-400 font-mono text-xs">{{ String(row.slide_number).padStart(2, '0') }}</td>
                <td class="px-6 py-3 font-medium text-navy">{{ row.title }}</td>
                <td class="px-6 py-3 text-gray-400 whitespace-nowrap">{{ formatTime(row.entered_at) }}</td>
                <td class="px-6 py-3 text-gray-500">{{ formatDuration(row.duration_seconds) }}</td>
                <td class="px-6 py-3 text-gray-500">{{ row.has_data ? row.detected : '—' }}</td>
                <td class="px-6 py-3 text-gray-500">{{ row.unclassified }}</td>
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
    </div>
  </AppLayout>
</template>
