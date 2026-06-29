<script setup>
import AppLayout from '../layouts/AppLayout.vue'

const stats = [
  { value: '3',   label: 'Active Classes',      sub: 'This Semester',   color: '#465FF1', bg: '#ECEFFE' },
  { value: '94',  label: 'Students Enrolled',   sub: 'Across All Classes', color: '#2D3CC8', bg: '#E5E8F9' },
  { value: '77%', label: 'Avg. Engagement',     sub: 'All Classes',     color: '#10B981', bg: '#D1FAE5' },
  { value: '21',  label: 'Total Sessions',      sub: 'Conducted',       color: '#465FF1', bg: '#ECEFFE' },
]

const classes = [
  {
    code: 'IT 301',
    subject: 'Data Structures',
    enrolled: 34,
    sessions: 8,
    lastSession: 'Jun 25, 2026',
    avgEng: 82,
    breakdown: { eng: 62, att: 10, conf: 18, bored: 6, dis: 4 },
  },
  {
    code: 'IT 302',
    subject: 'Database Management',
    enrolled: 31,
    sessions: 7,
    lastSession: 'Jun 24, 2026',
    avgEng: 76,
    breakdown: { eng: 58, att: 12, conf: 20, bored: 6, dis: 4 },
  },
  {
    code: 'IT 303',
    subject: 'Operating Systems',
    enrolled: 29,
    sessions: 6,
    lastSession: 'Jun 22, 2026',
    avgEng: 71,
    breakdown: { eng: 52, att: 11, conf: 22, bored: 9, dis: 6 },
  },
]

const engColor = (v) => {
  if (v >= 80) return '#2D3CC8'
  if (v >= 70) return '#465FF1'
  return '#6B7280'
}
</script>

<template>
  <AppLayout page-title="Classes">

    <!-- Stats strip -->
    <div class="grid grid-cols-4 gap-5 mb-6">
      <div v-for="stat in stats" :key="stat.label" class="stat-card flex items-center gap-3">
        <div class="w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0" :style="{ background: stat.bg }">
          <span class="text-sm font-bold" :style="{ color: stat.color }">{{ stat.value }}</span>
        </div>
        <div>
          <p class="text-xs text-gray-400">{{ stat.sub }}</p>
          <p class="text-sm font-semibold text-navy">{{ stat.label }}</p>
        </div>
      </div>
    </div>

    <!-- Class cards -->
    <div class="grid grid-cols-3 gap-6">
      <div v-for="cls in classes" :key="cls.code" class="page-card p-6 flex flex-col gap-5">

        <!-- Header -->
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="text-xs font-bold px-2 py-0.5 rounded-md" style="background:#ECEFFE; color:#1E3A5F;">{{ cls.code }}</span>
              <span class="text-xs font-medium px-2 py-0.5 rounded-md" style="background:#D1FAE5; color:#065F46;">Active</span>
            </div>
            <h3 class="text-base font-semibold text-navy">{{ cls.subject }}</h3>
          </div>
          <div class="text-right">
            <p class="text-2xl font-bold" :style="{ color: engColor(cls.avgEng) }">{{ cls.avgEng }}%</p>
            <p class="text-xs text-gray-400">Avg. Engagement</p>
          </div>
        </div>

        <!-- Stats row -->
        <div class="grid grid-cols-3 gap-3 text-center">
          <div class="bg-gray-50 rounded-xl py-3">
            <p class="text-xl font-bold text-navy">{{ cls.enrolled }}</p>
            <p class="text-xs text-gray-400 mt-0.5">Students</p>
          </div>
          <div class="bg-gray-50 rounded-xl py-3">
            <p class="text-xl font-bold text-navy">{{ cls.sessions }}</p>
            <p class="text-xs text-gray-400 mt-0.5">Sessions</p>
          </div>
          <div class="bg-gray-50 rounded-xl py-3">
            <p class="text-xs font-semibold text-navy leading-snug pt-1.5">{{ cls.lastSession }}</p>
            <p class="text-xs text-gray-400 mt-0.5">Last Session</p>
          </div>
        </div>

        <!-- Engagement breakdown bar -->
        <div>
          <p class="text-xs text-gray-400 mb-2">Engagement Breakdown</p>
          <div class="flex h-2.5 rounded-full overflow-hidden">
            <div :style="{ width: cls.breakdown.eng + '%', background: '#2D3CC8' }"></div>
            <div :style="{ width: cls.breakdown.att + '%', background: '#10B981' }"></div>
            <div :style="{ width: cls.breakdown.conf + '%', background: '#F59E0B' }"></div>
            <div :style="{ width: cls.breakdown.bored + '%', background: '#F97316' }"></div>
            <div :style="{ width: cls.breakdown.dis + '%', background: '#EF476F' }"></div>
          </div>
          <div class="flex items-center gap-4 mt-2">
            <span class="flex items-center gap-1.5 text-xs text-gray-500">
              <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:#2D3CC8"></span>{{ cls.breakdown.eng }}% Engaged
            </span>
            <span class="flex items-center gap-1.5 text-xs text-gray-500">
              <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:#F59E0B"></span>{{ cls.breakdown.conf }}% Confused
            </span>
            <span class="flex items-center gap-1.5 text-xs text-gray-500">
              <span class="w-2 h-2 rounded-full flex-shrink-0" style="background:#EF476F"></span>{{ cls.breakdown.dis }}% Disengaged
            </span>
          </div>
        </div>

        <!-- Action -->
        <RouterLink to="/session" class="btn-primary w-full justify-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.347a1.125 1.125 0 0 1 0 1.972l-11.54 6.347a1.125 1.125 0 0 1-1.667-.986V5.653Z"/></svg>
          Start Session
        </RouterLink>

      </div>
    </div>
  </AppLayout>
</template>
