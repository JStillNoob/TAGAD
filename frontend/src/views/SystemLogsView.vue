<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../layouts/AppLayout.vue'
import { fetchSystemLogs } from '../systemLogs'

const logs = ref([])
const total = ref(0)
const page = ref(1)
const loading = ref(false)
const error = ref('')
const filters = reactive({ search: '', date_from: '', date_to: '' })
const pageSize = 20
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

function formatLoggedAt(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

async function loadLogs(targetPage = 1) {
  loading.value = true
  error.value = ''
  try {
    const response = await fetchSystemLogs({
      search: filters.search.trim(),
      date_from: filters.date_from,
      date_to: filters.date_to,
      page: targetPage,
    })
    logs.value = response.results
    total.value = response.count
    page.value = targetPage
  } catch (requestError) {
    error.value = requestError.message || 'Unable to load system logs.'
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  if (filters.date_from && filters.date_to && filters.date_from > filters.date_to) {
    error.value = 'The start date cannot be after the end date.'
    return
  }
  loadLogs(1)
}

function clearFilters() {
  filters.search = ''
  filters.date_from = ''
  filters.date_to = ''
  loadLogs(1)
}

onMounted(() => loadLogs())
</script>

<template>
  <AppLayout page-title="System Logs">
    <div class="page-card">
      <div class="px-6 py-5 border-b border-gray-50">
        <h3 class="text-sm font-semibold text-navy">Activity Log</h3>
        <p class="text-xs text-gray-400 mt-0.5">Record of user actions you are permitted to view</p>

        <form class="grid grid-cols-1 md:grid-cols-4 gap-3 mt-5" @submit.prevent="applyFilters">
          <label class="md:col-span-2 text-xs font-medium text-gray-600">
            User, activity, or IP address
            <input
              v-model="filters.search"
              type="search"
              placeholder="Search logs…"
              class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand"
            >
          </label>
          <label class="text-xs font-medium text-gray-600">
            From
            <input v-model="filters.date_from" type="date" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand">
          </label>
          <label class="text-xs font-medium text-gray-600">
            To
            <input v-model="filters.date_to" type="date" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand">
          </label>
          <div class="md:col-span-4 flex justify-end gap-2">
            <button type="button" class="px-4 py-2 rounded-lg border border-gray-200 text-sm text-gray-600 hover:bg-gray-50 disabled:opacity-50" :disabled="loading" @click="clearFilters">Clear</button>
            <button type="submit" class="px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium hover:opacity-90 disabled:opacity-50" :disabled="loading">Apply filters</button>
          </div>
        </form>

        <p v-if="error" class="mt-4 text-sm text-red-600" role="alert">{{ error }}</p>
      </div>

      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-50">
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">User</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Activity</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">IP Address</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Logged At</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-if="loading">
              <td colspan="4" class="px-6 py-10 text-center text-gray-400">Loading system logs…</td>
            </tr>
            <tr v-else-if="!logs.length">
              <td colspan="4" class="px-6 py-10 text-center text-gray-400">No system logs match the selected filters.</td>
            </tr>
            <tr v-for="log in logs" v-else :key="log.id" class="hover:bg-gray-50/50 transition-colors">
              <td class="px-6 py-3.5">
                <p class="font-medium text-navy">{{ log.user_name }}</p>
                <p class="text-xs text-gray-400">@{{ log.username }}<template v-if="log.organization_name"> · {{ log.organization_name }}</template></p>
              </td>
              <td class="px-6 py-3.5 text-gray-600">{{ log.activity }}</td>
              <td class="px-6 py-3.5 text-gray-400 font-mono text-xs">{{ log.ip_address || '—' }}</td>
              <td class="px-6 py-3.5 text-gray-500 whitespace-nowrap">{{ formatLoggedAt(log.logged_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="!loading && total" class="flex flex-col sm:flex-row items-center justify-between gap-3 px-6 py-4 border-t border-gray-50">
        <p class="text-xs text-gray-400">{{ total }} log{{ total === 1 ? '' : 's' }} · Page {{ page }} of {{ totalPages }}</p>
        <div class="flex gap-2">
          <button class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 disabled:opacity-40" :disabled="page <= 1" @click="loadLogs(page - 1)">Previous</button>
          <button class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-gray-600 disabled:opacity-40" :disabled="page >= totalPages" @click="loadLogs(page + 1)">Next</button>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
