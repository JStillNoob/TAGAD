<script setup>
import AppLayout from '../layouts/AppLayout.vue'

const reports = [
  { id: 1, classCode: 'IT 301', subject: 'Data Structures', sessionDate: 'Jun 25, 2026', reportName: 'Session Summary', format: 'PDF', generated_by: 'Dr. Santos', report_path: 'reports/it301_20260625_summary.pdf', generated_at: 'Jun 25, 2026 · 12:05 PM' },
  { id: 2, classCode: 'IT 301', subject: 'Data Structures', sessionDate: 'Jun 25, 2026', reportName: 'Engagement Data', format: 'CSV', generated_by: 'Dr. Santos', report_path: 'reports/it301_20260625_engagement.csv', generated_at: 'Jun 25, 2026 · 12:06 PM' },
  { id: 3, classCode: 'IT 302', subject: 'Database Management', sessionDate: 'Jun 24, 2026', reportName: 'Session Summary', format: 'PDF', generated_by: 'Dr. Santos', report_path: 'reports/it302_20260624_summary.pdf', generated_at: 'Jun 24, 2026 · 11:52 AM' },
  { id: 4, classCode: 'IT 303', subject: 'Operating Systems', sessionDate: 'Jun 22, 2026', reportName: 'Engagement Data', format: 'CSV', generated_by: 'Dr. Santos', report_path: 'reports/it303_20260622_engagement.csv', generated_at: 'Jun 22, 2026 · 3:18 PM' },
]

const stats = [
  { value: reports.length,                                label: 'Total Reports',  color: '#465FF1', bg: '#ECEFFE',
    icon: 'M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z' },
  { value: reports.filter(r => r.format === 'PDF').length, label: 'PDF Reports',    color: '#2D3CC8', bg: '#E5E8F9',
    icon: 'M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25Z' },
  { value: reports.filter(r => r.format === 'CSV').length, label: 'CSV Reports',    color: '#10B981', bg: '#D1FAE5',
    icon: 'M3.375 19.5h17.25m-17.25 0a1.125 1.125 0 0 1-1.125-1.125M3.375 19.5h7.5c.621 0 1.125-.504 1.125-1.125m-9.75 0V5.625m0 12.75v-1.5c0-.621.504-1.125 1.125-1.125m18.375 2.625V5.625m0 12.75c0 .621-.504 1.125-1.125 1.125m1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125m0 3.75h-7.5A1.125 1.125 0 0 1 12 18.375M3.375 5.625c0-.621.504-1.125 1.125-1.125h15c.621 0 1.125.504 1.125 1.125M3.375 5.625v1.5c0 .621.504 1.125 1.125 1.125h15c.621 0 1.125-.504 1.125-1.125v-1.5' },
  { value: reports[0].sessionDate,                          label: 'Latest Session', color: '#465FF1', bg: '#ECEFFE',
    icon: 'M6.75 3v2.25M17.25 3v2.25M3 18.75V7.5a2.25 2.25 0 0 1 2.25-2.25h13.5A2.25 2.25 0 0 1 21 7.5v11.25m-18 0A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75m-18 0v-7.5A2.25 2.25 0 0 1 5.25 9h13.5A2.25 2.25 0 0 1 21 11.25v7.5' },
]

const formatStyle = (format) => format === 'PDF'
  ? { bg: '#E5E8F9', color: '#2D3CC8' }
  : { bg: '#D1FAE5', color: '#065F46' }
</script>

<template>
  <AppLayout page-title="Reports">

    <!-- Stats strip -->
    <div class="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-6">
      <div v-for="stat in stats" :key="stat.label" class="stat-card flex items-center gap-3">
        <div class="w-11 h-11 rounded-full flex items-center justify-center flex-shrink-0" :style="{ background: stat.bg }">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" :stroke="stat.color" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" :d="stat.icon" />
          </svg>
        </div>
        <div class="min-w-0">
          <p class="text-base font-bold text-navy leading-none truncate">{{ stat.value }}</p>
          <p class="text-xs text-gray-400 mt-1.5">{{ stat.label }}</p>
        </div>
      </div>
    </div>

    <div class="page-card">
      <div class="flex items-center justify-between px-6 py-5 border-b border-gray-50">
        <div>
          <h3 class="text-sm font-semibold text-navy">Generated Reports</h3>
          <p class="text-xs text-gray-400 mt-0.5">Reports produced from completed classroom sessions</p>
        </div>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-50">
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">Report</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">Class</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">Generated By</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">Generated At</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide whitespace-nowrap">File</th>
              <th class="px-6 py-3"></th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="r in reports" :key="r.id" class="hover:bg-gray-50/50 transition-colors">
              <td class="px-6 py-3.5">
                <div class="flex items-center gap-3">
                  <div class="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0" :style="{ background: formatStyle(r.format).bg }">
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" :stroke="formatStyle(r.format).color" stroke-width="1.8">
                      <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                    </svg>
                  </div>
                  <div class="min-w-0">
                    <p class="font-medium text-navy whitespace-nowrap">{{ r.reportName }}</p>
                    <span class="inline-block mt-0.5 px-1.5 py-0.5 rounded text-xs font-semibold whitespace-nowrap" :style="{ background: formatStyle(r.format).bg, color: formatStyle(r.format).color }">{{ r.format }}</span>
                  </div>
                </div>
              </td>
              <td class="px-6 py-3.5 whitespace-nowrap">
                <p class="font-medium text-navy">{{ r.classCode }} <span class="text-gray-400 font-normal">— {{ r.subject }}</span></p>
                <p class="text-xs text-gray-400 mt-0.5">{{ r.sessionDate }}</p>
              </td>
              <td class="px-6 py-3.5 text-gray-500 whitespace-nowrap">{{ r.generated_by }}</td>
              <td class="px-6 py-3.5 text-gray-500 whitespace-nowrap">{{ r.generated_at }}</td>
              <td class="px-6 py-3.5 text-gray-400 font-mono text-xs max-w-[220px] truncate" :title="r.report_path">{{ r.report_path }}</td>
              <td class="px-6 py-3.5 text-right">
                <a href="#" :title="`Download ${r.reportName}`"
                  class="inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-brand hover:bg-brand-light transition-colors">
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
                  </svg>
                </a>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AppLayout>
</template>
