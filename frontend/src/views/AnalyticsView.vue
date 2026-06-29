<script setup>
import { onMounted } from 'vue'
import { Chart, registerables } from 'chart.js'
import AppLayout from '../layouts/AppLayout.vue'

Chart.register(...registerables)

const roundedTopPlugin = {
  id: 'roundedTop',
  afterDatasetsDraw(chart) {
    const { ctx } = chart
    const r = 8
    chart.data.labels.forEach((_, i) => {
      let minY = Infinity
      let color = '#C8D5FB'
      for (let di = chart.data.datasets.length - 1; di >= 0; di--) {
        const val = chart.data.datasets[di].data[i]
        const bar = chart.getDatasetMeta(di).data[i]
        if (bar && val > 0) {
          minY = Math.min(minY, bar.y)
          if (color === '#C8D5FB') color = chart.data.datasets[di].backgroundColor
        }
      }
      const topBar = chart.getDatasetMeta(0).data[i]
      if (!topBar || minY === Infinity) return
      const left = topBar.x - topBar.width / 2
      const w = topBar.width
      ctx.save()
      ctx.fillStyle = color
      ctx.beginPath()
      ctx.moveTo(left, minY + r)
      ctx.arcTo(left, minY, left + r, minY, r)
      ctx.lineTo(left + w - r, minY)
      ctx.arcTo(left + w, minY, left + w, minY + r, r)
      ctx.lineTo(left + w, minY + r * 2)
      ctx.lineTo(left, minY + r * 2)
      ctx.closePath()
      ctx.fill()
      ctx.restore()
    })
  }
}

const chartLegend = [
  { label:'Engaged', color:'#2D3CC8' }, { label:'Attentive', color:'#10B981' },
  { label:'Confused', color:'#F59E0B' }, { label:'Bored', color:'#F97316' },
  { label:'Disengaged', color:'#EF476F' },
]

const sessions = [
  'IT 301 — Data Structures · Jun 25, 2026',
  'IT 302 — Database Management · Jun 24, 2026',
  'IT 301 — Algorithms & Complexity · Jun 23, 2026',
  'IT 303 — Operating Systems · Jun 22, 2026',
]

const tableRows = [
  { n:'01', topic:'Introduction to Trees',    time:'10:30 AM', dur:'5:20',  eng:79, att:6,  conf:8,  bored:5, dis:2  },
  { n:'02', topic:'Tree Terminology',          time:'10:35 AM', dur:'6:10',  eng:83, att:5,  conf:6,  bored:4, dis:2  },
  { n:'03', topic:'Binary Trees Defined',      time:'10:41 AM', dur:'7:45',  eng:87, att:7,  conf:3,  bored:2, dis:1  },
  { n:'04', topic:'Tree Representation',       time:'10:49 AM', dur:'8:30',  eng:74, att:5,  conf:12, bored:5, dis:4  },
  { n:'05', topic:'Binary Trees & Traversal',  time:'10:57 AM', dur:'9:15',  eng:76, att:6,  conf:10, bored:4, dis:4  },
  { n:'06', topic:'Inorder Traversal',         time:'11:07 AM', dur:'6:55',  eng:70, att:7,  conf:15, bored:5, dis:3  },
  { n:'07', topic:'Preorder Traversal',        time:'11:14 AM', dur:'5:40',  eng:75, att:5,  conf:11, bored:6, dis:3  },
  { n:'08', topic:'Postorder Traversal',       time:'11:19 AM', dur:'6:20',  eng:70, att:6,  conf:16, bored:5, dis:3  },
  { n:'09', topic:'BST Operations',            time:'11:26 AM', dur:'10:05', eng:43, att:5,  conf:41, bored:7, dis:4  },
  { n:'10', topic:'Binary Search Trees',       time:'11:36 AM', dur:'8:15',  eng:65, att:6,  conf:18, bored:7, dis:4  },
  { n:'11', topic:'Tree Balancing Intro',      time:'11:44 AM', dur:'7:30',  eng:50, att:5,  conf:23, bored:0, dis:22 },
  { n:'12', topic:'Summary & Q&A',             time:'11:52 AM', dur:'8:45',  eng:84, att:7,  conf:4,  bored:3, dis:2  },
]

const engColor = (v) => {
  if (v >= 80) return '#2D3CC8'
  if (v >= 65) return '#465FF1'
  return '#6B7280'
}

onMounted(() => {
  new Chart(document.getElementById('engagementChart'), {
    type: 'bar',
    plugins: [roundedTopPlugin],
    data: {
      labels: tableRows.map(r => `Slide ${r.n}`),
      datasets: [
        { label:'Engaged',    data: tableRows.map(r=>r.eng),   backgroundColor:'#2D3CC8', borderRadius:0, categoryPercentage:0.6, barPercentage:1 },
        { label:'Attentive',  data: tableRows.map(r=>r.att),   backgroundColor:'#10B981', borderRadius:0, categoryPercentage:0.6, barPercentage:1 },
        { label:'Confused',   data: tableRows.map(r=>r.conf),  backgroundColor:'#F59E0B', borderRadius:0, categoryPercentage:0.6, barPercentage:1 },
        { label:'Bored',      data: tableRows.map(r=>r.bored), backgroundColor:'#F97316', borderRadius:0, categoryPercentage:0.6, barPercentage:1 },
        { label:'Disengaged', data: tableRows.map(r=>r.dis),   backgroundColor:'#EF476F', borderRadius:0, categoryPercentage:0.6, barPercentage:1 },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { stacked: true, grid: { display:false }, ticks: { font:{ family:'Inter', size:11 }, color:'#94a3b8' } },
        y: { stacked: true, max:100, grid:{ color:'#f1f5f9' }, ticks: { font:{ family:'Inter', size:11 }, color:'#94a3b8', callback: v => v+'%' } }
      }
    }
  })
})
</script>

<template>
  <AppLayout page-title="Post-Lesson Analytics">

    <!-- Session selector + download -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center gap-3">
        <label for="session-select" class="text-sm font-semibold text-gray-600">Session:</label>
        <select id="session-select" class="border border-gray-200 rounded-xl px-4 py-2.5 text-sm outline-none bg-white text-navy"
          @focus="$event.target.style.borderColor='#465FF1'" @blur="$event.target.style.borderColor='#e2e8f0'">
          <option v-for="s in sessions" :key="s">{{ s }}</option>
        </select>
      </div>
      <a href="#" class="btn-primary">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
        </svg>
        Download CSV
      </a>
    </div>

    <!-- Summary stats -->
    <div class="grid grid-cols-4 gap-5 mb-6">
      <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Total Students</div><div class="text-3xl font-bold text-navy">34</div><div class="text-xs text-gray-400 mt-1">IT 301 class</div></div>
      <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Session Duration</div><div class="text-3xl font-bold text-navy">1h 15m</div><div class="text-xs text-gray-400 mt-1">12 slides covered</div></div>
      <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Avg. Engagement</div><div class="text-3xl font-bold" style="color:#2D3CC8">82%</div><div class="flex items-center gap-1 mt-1"><span class="text-xs font-medium" style="color:#2D3CC8">▲ 4%</span><span class="text-xs text-gray-400">vs last session</span></div></div>
      <div class="stat-card"><div class="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-3">Most Confused Slide</div><div class="text-3xl font-bold" style="color:#7B92F5">Slide 9</div><div class="text-xs text-gray-400 mt-1">BST Operations — 41% confused</div></div>
    </div>

    <!-- Chart + insights -->
    <div class="grid grid-cols-3 gap-6 mb-6">
      <div class="col-span-2 page-card p-6">
        <div class="flex items-center justify-between mb-5">
          <div>
            <h3 class="font-semibold text-navy">Engagement per Slide</h3>
            <p class="text-xs text-gray-400 mt-0.5">Stacked breakdown by engagement state</p>
          </div>
          <div class="flex items-center gap-3 text-xs text-gray-500 flex-wrap">
            <span v-for="l in chartLegend" :key="l.label" class="flex items-center gap-1.5">
              <span class="w-3 h-3 rounded-sm inline-block" :style="{ background: l.color }"></span>{{ l.label }}
            </span>
          </div>
        </div>
        <div style="position:relative; height:300px;">
          <canvas id="engagementChart"></canvas>
        </div>
      </div>

      <!-- Insights -->
      <div class="flex flex-col gap-4">
        <div class="page-card p-5">
          <h3 class="font-semibold text-sm mb-4 text-navy">Key Insights</h3>
          <div class="space-y-3">
            <div class="p-3 rounded-xl border-l-4" style="border-color:#2D3CC8; background:#E5E8F9;">
              <p class="text-xs font-semibold" style="color:#2D3CC8">Highest Engagement</p>
              <p class="text-sm font-bold mt-0.5 text-navy">Slide 3 — 94% engaged</p>
              <p class="text-xs text-gray-400 mt-0.5">Binary Trees Defined</p>
            </div>
            <div class="p-3 rounded-xl border-l-4" style="border-color:#F59E0B; background:#FEF9EE;">
              <p class="text-xs font-semibold" style="color:#D97706">Most Confusion</p>
              <p class="text-sm font-bold mt-0.5 text-navy">Slide 9 — 41% confused</p>
              <p class="text-xs text-gray-400 mt-0.5">BST Operations</p>
            </div>
            <div class="p-3 rounded-xl border-l-4" style="border-color:#EF476F; background:#FEF0F3;">
              <p class="text-xs font-semibold" style="color:#C73F62">Most Disengaged</p>
              <p class="text-sm font-bold mt-0.5 text-navy">Slide 11 — 22% disengaged</p>
              <p class="text-xs text-gray-400 mt-0.5">Tree Balancing Intro</p>
            </div>
            <div class="p-3 rounded-xl border-l-4 border-gray-200" style="background:rgba(148,163,184,0.05);">
              <p class="text-xs font-semibold text-gray-400">Recommendation</p>
              <p class="text-xs text-gray-600 mt-1">Revisit Slides 9 and 11 in the next session — high confusion and disengagement signals detected.</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Table -->
    <div class="page-card">
      <div class="px-6 py-5 border-b border-gray-50">
        <h3 class="font-semibold text-sm text-navy">Slide-by-Slide Breakdown</h3>
      </div>
      <div class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-gray-50">
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Slide</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Topic</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Timestamp</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Duration</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Engaged</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Attentive</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Confused</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Bored</th>
              <th class="text-left px-6 py-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">Disengaged</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50">
            <tr v-for="row in tableRows" :key="row.n" class="hover:bg-gray-50/50 transition-colors">
              <td class="px-6 py-3 text-gray-400 font-mono text-xs">{{ row.n }}</td>
              <td class="px-6 py-3 font-medium" :style="{ color: row.conf >= 30 ? '#D97706' : row.dis >= 15 ? '#C73F62' : '#1D2A3B' }">{{ row.topic }}</td>
              <td class="px-6 py-3 text-gray-400 font-mono text-xs">{{ row.time }}</td>
              <td class="px-6 py-3 text-gray-500">{{ row.dur }}</td>
              <td class="px-6 py-3 font-semibold" :style="{ color: engColor(row.eng) }">{{ row.eng }}%</td>
              <td class="px-6 py-3 text-gray-500">{{ row.att }}%</td>
              <td class="px-6 py-3" :style="row.conf >= 30 ? 'font-weight:600;color:#D97706' : 'color:#6b7280'">{{ row.conf }}%</td>
              <td class="px-6 py-3 text-gray-500">{{ row.bored }}%</td>
              <td class="px-6 py-3" :style="row.dis >= 15 ? 'font-weight:600;color:#C73F62' : 'color:#6b7280'">{{ row.dis }}%</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </AppLayout>
</template>
