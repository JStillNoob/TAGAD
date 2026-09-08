<script setup>
import { computed, onMounted, ref } from 'vue'
import AppLayout from '../layouts/AppLayout.vue'
import { fetchReportOptions, fetchReports, generateReport } from '../reports'
import { currentTheme } from '../theme'

const reports = ref([])
const sessions = ref([])
const selectedSessionId = ref('')
const loading = ref(true)
const generating = ref('')
const error = ref('')
const success = ref('')

const pdfCount = computed(() => reports.value.filter(report => report.report_type === 'pdf').length)
const csvCount = computed(() => reports.value.filter(report => report.report_type === 'csv').length)
const latestSession = computed(() => reports.value[0]?.session_date || null)

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(`${value}T00:00:00`))
}

function formatDateTime(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function sessionLabel(session) {
  return `${session.subject_code} — ${session.subject_name} · ${session.classroom} · ${formatDate(session.session_date)}`
}

function formatStyle(format) {
  if (currentTheme.value === 'dark') {
    return format === 'PDF'
      ? { bg: '#202A55', color: '#A5B4FC' }
      : { bg: '#052E2B', color: '#6EE7B7' }
  }
  return format === 'PDF'
    ? { bg: '#E5E8F9', color: '#2D3CC8' }
    : { bg: '#D1FAE5', color: '#065F46' }
}

function fieldError(requestError) {
  const first = Object.values(requestError.fields || {}).flat()[0]
  return first || requestError.message || 'Unable to generate the report.'
}

async function loadReports() {
  loading.value = true
  error.value = ''
  try {
    const [reportData, sessionData] = await Promise.all([fetchReports(), fetchReportOptions()])
    reports.value = reportData
    sessions.value = sessionData
    if (!selectedSessionId.value && sessionData.length) selectedSessionId.value = String(sessionData[0].id)
  } catch (requestError) {
    error.value = requestError.message || 'Unable to load reports.'
  } finally {
    loading.value = false
  }
}

async function createReport(reportType) {
  if (!selectedSessionId.value || generating.value) return
  generating.value = reportType
  error.value = ''
  success.value = ''
  try {
    const report = await generateReport(Number(selectedSessionId.value), reportType)
    reports.value = [report, ...reports.value]
    success.value = reportType === 'pdf'
      ? 'Polished PDF report generated successfully.'
      : 'Raw CSV data generated successfully.'
  } catch (requestError) {
    error.value = fieldError(requestError)
  } finally {
    generating.value = ''
  }
}

onMounted(loadReports)
</script>

<template>
  <AppLayout page-title="Reports">
    <section class="page-card p-6 mb-6">
      <div class="flex flex-col xl:flex-row xl:items-end justify-between gap-5">
        <div class="max-w-2xl">
          <p class="text-xs font-semibold uppercase tracking-widest text-brand">Post-lesson reporting</p>
          <h2 class="text-xl font-bold text-navy mt-1">Turn a completed session into a clear classroom report</h2>
          <p class="text-sm text-gray-500 mt-2">The PDF is the presentation-ready report for teachers and administrators. CSV is a secondary export for Excel, statistics, and research.</p>
        </div>
        <label class="block w-full xl:w-[430px] text-xs font-semibold text-gray-600">
          Completed session
          <select
            v-model="selectedSessionId"
            class="mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-navy outline-none focus:border-brand disabled:bg-gray-50"
            :disabled="loading || !sessions.length || Boolean(generating)"
          >
            <option v-if="!sessions.length" value="">No completed sessions available</option>
            <option v-for="session in sessions" :key="session.id" :value="String(session.id)">{{ sessionLabel(session) }}</option>
          </select>
        </label>
      </div>

      <div class="flex flex-col sm:flex-row gap-3 mt-5">
        <button class="btn-primary justify-center disabled:opacity-50" :disabled="!selectedSessionId || Boolean(generating)" @click="createReport('pdf')">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" /></svg>
          {{ generating === 'pdf' ? 'Building PDF…' : 'Generate polished PDF' }}
        </button>
        <button class="inline-flex items-center justify-center gap-2 rounded-lg border border-gray-200 px-4 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-50 disabled:opacity-50" :disabled="!selectedSessionId || Boolean(generating)" @click="createReport('csv')">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
          {{ generating === 'csv' ? 'Building CSV…' : 'Export raw CSV' }}
        </button>
      </div>
      <p v-if="error" class="mt-4 text-sm text-red-600" role="alert">{{ error }}</p>
      <p v-if="success" class="mt-4 text-sm text-emerald-600" role="status">{{ success }}</p>
    </section>

    <div class="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
      <div class="stat-card"><p class="text-2xl font-bold text-navy">{{ reports.length }}</p><p class="text-xs text-gray-400 mt-1">Total Reports</p></div>
      <div class="stat-card"><p class="text-2xl font-bold" style="color:#2D3CC8">{{ pdfCount }}</p><p class="text-xs text-gray-400 mt-1">Polished PDFs</p></div>
      <div class="stat-card"><p class="text-2xl font-bold" style="color:#059669">{{ csvCount }}</p><p class="text-xs text-gray-400 mt-1">Raw CSV Exports</p></div>
      <div class="stat-card"><p class="text-base font-bold text-navy">{{ formatDate(latestSession) }}</p><p class="text-xs text-gray-400 mt-1">Latest Reported Session</p></div>
    </div>

    <section class="page-card">
      <div class="px-6 py-5 border-b border-gray-50">
        <h3 class="text-sm font-semibold text-navy">Generated Reports</h3>
        <p class="text-xs text-gray-400 mt-0.5">Only sessions available to your account are shown</p>
      </div>
      <div v-if="loading" class="p-12 text-center text-sm text-gray-400">Loading reports…</div>
      <div v-else-if="error && !reports.length" class="p-12 text-center">
        <p class="text-sm text-red-600">{{ error }}</p>
        <button class="mt-4 px-4 py-2 rounded-lg bg-brand text-white text-sm" @click="loadReports">Try again</button>
      </div>
      <div v-else-if="!reports.length" class="p-12 text-center">
        <h3 class="font-semibold text-navy">No reports generated yet</h3>
        <p class="text-sm text-gray-400 mt-2">Choose a completed session above and generate your first polished PDF.</p>
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead><tr class="border-b border-gray-50"><th v-for="heading in ['Report', 'Class', 'Generated By', 'Generated At', 'File', '']" :key="heading" class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">{{ heading }}</th></tr></thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="report in reports" :key="report.id" class="hover:bg-gray-50/50 transition-colors">
              <td class="px-6 py-3.5"><p class="font-medium text-navy whitespace-nowrap">{{ report.report_name }}</p><span class="inline-block mt-1 px-1.5 py-0.5 rounded text-xs font-semibold" :style="{ background: formatStyle(report.format).bg, color: formatStyle(report.format).color }">{{ report.format }}</span></td>
              <td class="px-6 py-3.5 whitespace-nowrap"><p class="font-medium text-navy">{{ report.subject_code }} <span class="font-normal text-gray-400">— {{ report.subject_name }}</span></p><p class="text-xs text-gray-400 mt-0.5">{{ report.classroom }} · {{ formatDate(report.session_date) }}</p></td>
              <td class="px-6 py-3.5 text-gray-500 whitespace-nowrap">{{ report.generated_by }}</td>
              <td class="px-6 py-3.5 text-gray-500 whitespace-nowrap">{{ formatDateTime(report.generated_at) }}</td>
              <td class="px-6 py-3.5 text-gray-400 font-mono text-xs max-w-[240px] truncate" :title="report.file_name">{{ report.file_name }}</td>
              <td class="px-6 py-3.5 text-right"><a :href="report.download_url" download class="inline-flex items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium text-brand hover:bg-brand-light"><svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>Download</a></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </AppLayout>
</template>
