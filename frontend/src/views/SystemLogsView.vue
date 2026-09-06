<script setup>
import AppLayout from '../layouts/AppLayout.vue'

const logs = [
  { id: 1, user: 'Dr. Santos', activity: 'Logged in', ip_address: '192.168.1.24', logged_at: 'Jun 26, 2026, 8:02 AM' },
  { id: 2, user: 'Dr. Santos', activity: 'Started session for IT 301 — Data Structures', ip_address: '192.168.1.24', logged_at: 'Jun 26, 2026, 10:30 AM' },
  { id: 3, user: 'Dr. Santos', activity: 'Uploaded presentation "Binary Trees.pptx"', ip_address: '192.168.1.24', logged_at: 'Jun 26, 2026, 10:31 AM' },
  { id: 4, user: 'Dr. Santos', activity: 'Ended session for IT 301 — Data Structures', ip_address: '192.168.1.24', logged_at: 'Jun 26, 2026, 11:45 AM' },
  { id: 5, user: 'Dr. Santos', activity: 'Generated engagement report (CSV)', ip_address: '192.168.1.24', logged_at: 'Jun 26, 2026, 11:47 AM' },
  { id: 6, user: 'Dr. Santos', activity: 'Logged out', ip_address: '192.168.1.24', logged_at: 'Jun 26, 2026, 12:15 PM' },
]
</script>

<template>
  <AppLayout page-title="System Logs">

    <div class="page-card">
      <div class="px-6 py-5 border-b border-gray-50">
        <h3 class="text-sm font-semibold text-navy">Activity Log</h3>
        <p class="text-xs text-gray-400 mt-0.5">Record of user actions performed in the system</p>
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
            <tr v-for="log in logs" :key="log.id" class="hover:bg-gray-50/50 transition-colors">
              <td class="px-6 py-3.5 font-medium text-navy">{{ log.user }}</td>
              <td class="px-6 py-3.5 text-gray-600">{{ log.activity }}</td>
              <td class="px-6 py-3.5 text-gray-400 font-mono text-xs">{{ log.ip_address }}</td>
              <td class="px-6 py-3.5 text-gray-500">{{ log.logged_at }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AppLayout>
</template>
