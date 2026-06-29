<script setup>
import AppLayout from '../layouts/AppLayout.vue'

const sessions = [
  { subject: 'Data Structures',         cls: 'IT 301', date: 'Jun 25, 2026', duration: '1h 15m', eng: 82 },
  { subject: 'Database Management',     cls: 'IT 302', date: 'Jun 24, 2026', duration: '1h 30m', eng: 74 },
  { subject: 'Algorithms & Complexity', cls: 'IT 301', date: 'Jun 23, 2026', duration: '1h 00m', eng: 61 },
  { subject: 'Operating Systems',       cls: 'IT 303', date: 'Jun 22, 2026', duration: '1h 45m', eng: 79 },
  { subject: 'Software Engineering',    cls: 'IT 302', date: 'Jun 21, 2026', duration: '1h 20m', eng: 55 },
]

const engagementBars = [
  { label: 'Engaged',    pct: 62, color: '#2D3CC8' },
  { label: 'Attentive',  pct: 16, color: '#10B981' },
  { label: 'Confused',   pct: 12, color: '#F59E0B' },
  { label: 'Bored',      pct: 6,  color: '#F97316' },
  { label: 'Disengaged', pct: 4,  color: '#EF476F' },
]
</script>

<template>
  <AppLayout page-title="Dashboard">

    <!-- Welcome -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h2 class="text-xl font-bold text-navy">Good morning, Dr. Santos 👋</h2>
        <p class="text-sm text-gray-400 mt-0.5">Here's what's happening in your classroom today.</p>
      </div>
      <RouterLink to="/session" class="btn-primary">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" />
        </svg>
        Start New Session
      </RouterLink>
    </div>

    <!-- Stat cards — TailAdmin format -->
    <div class="grid grid-cols-2 xl:grid-cols-4 gap-5 mb-6">

      <div class="stat-card">
        <div class="flex items-center justify-between mb-5">
          <p class="text-sm font-medium text-gray-500">Total Students</p>
          <div class="w-11 h-11 rounded-full flex items-center justify-center" style="background:rgba(70,95,241,0.1);">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="#465FF1" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
            </svg>
          </div>
        </div>
        <h3 class="text-3xl font-bold text-navy mb-1">34</h3>
        <p class="text-xs text-gray-400">Across 2 active classes</p>
        <div class="flex items-center gap-1.5 mt-4 pt-3 border-t border-gray-100">
          <span class="text-xs font-bold" style="color:#16a34a;">↑ +2</span>
          <span class="text-xs text-gray-400">new this month</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="flex items-center justify-between mb-5">
          <p class="text-sm font-medium text-gray-500">Sessions Today</p>
          <div class="w-11 h-11 rounded-full flex items-center justify-center" style="background:rgba(70,95,241,0.1);">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="#465FF1" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
            </svg>
          </div>
        </div>
        <h3 class="text-3xl font-bold text-navy mb-1">2</h3>
        <p class="text-xs text-gray-400">1 completed, 1 upcoming</p>
        <div class="flex items-center gap-1.5 mt-4 pt-3 border-t border-gray-100">
          <span class="text-xs font-bold" style="color:#16a34a;">↑ +1</span>
          <span class="text-xs text-gray-400">vs yesterday</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="flex items-center justify-between mb-5">
          <p class="text-sm font-medium text-gray-500">Avg. Engagement</p>
          <div class="w-11 h-11 rounded-full flex items-center justify-center" style="background:rgba(70,95,241,0.1);">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="#465FF1" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
            </svg>
          </div>
        </div>
        <h3 class="text-3xl font-bold text-navy mb-1">78%</h3>
        <p class="text-xs text-gray-400">Last 30 days</p>
        <div class="flex items-center gap-1.5 mt-4 pt-3 border-t border-gray-100">
          <span class="text-xs font-bold" style="color:#16a34a;">↑ +4%</span>
          <span class="text-xs text-gray-400">vs last session</span>
        </div>
      </div>

      <div class="stat-card">
        <div class="flex items-center justify-between mb-5">
          <p class="text-sm font-medium text-gray-500">Alerts Today</p>
          <div class="w-11 h-11 rounded-full flex items-center justify-center" style="background:rgba(239,71,111,0.1);">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="#EF476F" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
            </svg>
          </div>
        </div>
        <h3 class="text-3xl font-bold text-danger mb-1">3</h3>
        <p class="text-xs text-gray-400">Disengagement detected</p>
        <div class="flex items-center gap-1.5 mt-4 pt-3 border-t border-gray-100">
          <span class="text-xs font-bold text-danger">↑ +1</span>
          <span class="text-xs text-gray-400">vs yesterday</span>
        </div>
      </div>
    </div>

    <!-- Lower section -->
    <div class="grid grid-cols-3 gap-6">

      <!-- Recent Sessions table -->
      <div class="col-span-2 page-card">
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-100">
          <div>
            <h3 class="text-sm font-semibold text-navy">Recent Sessions</h3>
            <p class="text-xs text-gray-400 mt-0.5">Last 5 classroom sessions</p>
          </div>
          <RouterLink to="/analytics" class="text-xs font-semibold text-brand">View all →</RouterLink>
        </div>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-100">
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Subject</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Class</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Date</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Duration</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Avg. Eng.</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Status</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-100">
            <tr v-for="s in sessions" :key="s.subject" class="hover:bg-gray-50 transition-colors">
              <td class="px-6 py-3.5 font-medium text-navy">{{ s.subject }}</td>
              <td class="px-6 py-3.5 text-gray-500">{{ s.cls }}</td>
              <td class="px-6 py-3.5 text-gray-500">{{ s.date }}</td>
              <td class="px-6 py-3.5 text-gray-500">{{ s.duration }}</td>
              <td class="px-6 py-3.5 font-semibold" :style="{ color: s.eng >= 70 ? '#2D3CC8' : s.eng >= 60 ? '#465FF1' : '#6B7280' }">{{ s.eng }}%</td>
              <td class="px-6 py-3.5"><span class="badge-engaged">Completed</span></td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Right column -->
      <div class="flex flex-col gap-5">

        <!-- Today's Engagement -->
        <div class="page-card p-5">
          <div class="flex items-center justify-between mb-4">
            <h3 class="text-sm font-semibold text-navy">Today's Engagement</h3>
            <button class="text-gray-400 hover:text-gray-600 transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 3a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM10 8.5a1.5 1.5 0 1 1 0 3 1.5 1.5 0 0 1 0-3ZM11.5 15.5a1.5 1.5 0 1 0-3 0 1.5 1.5 0 0 0 3 0Z" />
              </svg>
            </button>
          </div>
          <div class="space-y-3.5">
            <div v-for="e in engagementBars" :key="e.label">
              <div class="flex justify-between text-xs mb-1.5">
                <span class="font-medium text-gray-600">{{ e.label }}</span>
                <span class="font-semibold" :style="{ color: e.color }">{{ e.pct }}%</span>
              </div>
              <div class="h-1.5 rounded-full bg-gray-100 overflow-hidden">
                <div class="h-full rounded-full" :style="{ width: e.pct + '%', background: e.color }"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div class="page-card p-5">
          <h3 class="text-sm font-semibold text-navy mb-4">Quick Actions</h3>
          <div class="space-y-1">
            <RouterLink to="/session" class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors group">
              <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style="background:rgba(70,95,241,0.1);">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="#465FF1" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z" /></svg>
              </div>
              <span class="text-sm text-gray-600 group-hover:text-navy transition-colors">Start Monitoring</span>
            </RouterLink>
            <RouterLink to="/analytics" class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors group">
              <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style="background:rgba(70,95,241,0.1);">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="#465FF1" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" /></svg>
              </div>
              <span class="text-sm text-gray-600 group-hover:text-navy transition-colors">Download Report</span>
            </RouterLink>
            <RouterLink to="/students" class="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-50 transition-colors group">
              <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style="background:rgba(70,95,241,0.1);">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="#465FF1" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" /></svg>
              </div>
              <span class="text-sm text-gray-600 group-hover:text-navy transition-colors">View Classes</span>
            </RouterLink>
          </div>
        </div>
      </div>
    </div>
  </AppLayout>
</template>
