<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { currentUser } from '../auth'
import AppLayout from '../layouts/AppLayout.vue'
import {
  endClassroomSession,
  enterSessionSlide,
  fetchSessionOptions,
  fetchSessions,
  startClassroomSession,
  simulateEngagement,
  uploadPresentation,
} from '../sessions'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const error = ref('')
const actionBusy = ref(false)
const options = ref({ subjects: [], presentations: [] })
const sessions = ref([])
const selectedSubjectId = ref('')
const selectedPresentationId = ref('')
const selectedCameraIds = ref([])
const uploadTitle = ref('')
const uploadFile = ref(null)
const fileInput = ref(null)
const activeSession = ref(null)
const currentSlideIndex = ref(0)
const elapsedSeconds = ref(0)
const latestEngagement = ref(null)
const liveAlert = ref(null)
const socketStatus = ref('disconnected')
const simulationRunning = ref(false)
let timer = null
let simulationTimer = null
let engagementSocket = null
let socketReconnectTimer = null

const engagementCategories = [
  { key: 'engaged', label: 'Engaged', color: '#2D3CC8' },
  { key: 'attentive', label: 'Attentive', color: '#10B981' },
  { key: 'confused', label: 'Confused', color: '#F59E0B' },
  { key: 'bored', label: 'Bored', color: '#F97316' },
  { key: 'disengaged', label: 'Disengaged', color: '#EF476F' },
]

const selectedSubject = computed(() => options.value.subjects.find(
  (subject) => subject.id === Number(selectedSubjectId.value),
))
const selectedPresentation = computed(() => options.value.presentations.find(
  (presentation) => presentation.id === Number(selectedPresentationId.value),
))
const slides = computed(() => activeSession.value?.presentation?.slides || [])
const currentSlide = computed(() => slides.value[currentSlideIndex.value] || null)
const canStart = computed(() => (
  selectedSubject.value
  && selectedPresentation.value?.processing_status === 'ready'
  && !actionBusy.value
))
const elapsedDisplay = computed(() => {
  const hours = Math.floor(elapsedSeconds.value / 3600)
  const minutes = Math.floor((elapsedSeconds.value % 3600) / 60)
  const seconds = elapsedSeconds.value % 60
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':')
})

function messageFrom(errorObject) {
  const fields = errorObject.fields || {}
  for (const value of Object.values(fields)) {
    if (Array.isArray(value) && value.length) return value[0]
    if (typeof value === 'string') return value
  }
  return errorObject.message
}

function startTimer() {
  clearInterval(timer)
  const update = () => {
    const started = new Date(activeSession.value.started_at).getTime()
    elapsedSeconds.value = Math.max(0, Math.floor((Date.now() - started) / 1000))
  }
  update()
  timer = setInterval(update, 1000)
}

function applyEngagement(summary) {
  if (!summary || latestEngagement.value?.id === summary.id) return
  latestEngagement.value = summary
  if (summary.alert) liveAlert.value = summary.alert
  else if (summary.distribution.disengaged <= 50) liveAlert.value = null
}

function connectEngagement(sessionId) {
  clearTimeout(socketReconnectTimer)
  const previousSocket = engagementSocket
  engagementSocket = null
  previousSocket?.close()
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/sessions/${sessionId}/engagement/`)
  engagementSocket = socket
  socketStatus.value = 'connecting'
  socket.onopen = () => { socketStatus.value = 'connected' }
  socket.onclose = () => {
    if (engagementSocket !== socket) return
    socketStatus.value = 'disconnected'
    if (activeSession.value?.id === sessionId) {
      socketReconnectTimer = setTimeout(() => connectEngagement(sessionId), 2000)
    }
  }
  socket.onerror = () => { socketStatus.value = 'error' }
  socket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      if (message.type === 'engagement.summary') applyEngagement(message.data)
    } catch {
      error.value = 'A live engagement update could not be read.'
    }
  }
}

async function emitSimulation() {
  if (!activeSession.value || actionBusy.value) return
  try {
    applyEngagement(await simulateEngagement(activeSession.value.id))
  } catch (requestError) {
    stopSimulation()
    error.value = messageFrom(requestError)
  }
}

function startSimulation() {
  if (simulationRunning.value) return
  simulationRunning.value = true
  emitSimulation()
  simulationTimer = setInterval(emitSimulation, 2000)
}

function stopSimulation() {
  simulationRunning.value = false
  clearInterval(simulationTimer)
  simulationTimer = null
}

function disconnectEngagement() {
  stopSimulation()
  clearTimeout(socketReconnectTimer)
  const socket = engagementSocket
  engagementSocket = null
  socket?.close()
  socketStatus.value = 'disconnected'
}

function applyRouteSelection() {
  const subject = options.value.subjects.find(item => item.id === Number(route.query.subject))
  const presentation = options.value.presentations.find(item => item.id === Number(route.query.presentation))
  if (subject) selectedSubjectId.value = subject.id
  if (presentation) selectedPresentationId.value = presentation.id
}

async function loadPage() {
  loading.value = true
  error.value = ''
  try {
    const [sessionOptions, sessionHistory] = await Promise.all([
      fetchSessionOptions(),
      fetchSessions(),
    ])
    options.value = sessionOptions
    sessions.value = sessionHistory
    applyRouteSelection()
    const ongoing = sessionHistory.find((session) => (
      session.user === currentUser.value?.id && session.status === 'ongoing'
    ))
    if (ongoing) {
      activeSession.value = ongoing
      const savedIndex = ongoing.presentation.slides.findIndex(
        (slide) => slide.id === ongoing.current_slide,
      )
      currentSlideIndex.value = savedIndex >= 0 ? savedIndex : 0
      startTimer()
      connectEngagement(ongoing.id)
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    loading.value = false
  }
}

function chooseFile(event) {
  uploadFile.value = event.target.files?.[0] || null
  if (uploadFile.value && !uploadTitle.value) {
    uploadTitle.value = uploadFile.value.name.replace(/\.(pdf|pptx)$/i, '')
  }
}

async function submitUpload() {
  if (!uploadFile.value || !uploadTitle.value.trim()) return
  actionBusy.value = true
  error.value = ''
  try {
    const presentation = await uploadPresentation({
      title: uploadTitle.value.trim(),
      file: uploadFile.value,
    })
    options.value.presentations.unshift(presentation)
    selectedPresentationId.value = presentation.id
    uploadTitle.value = ''
    uploadFile.value = null
    if (fileInput.value) fileInput.value.value = ''
    if (presentation.processing_status === 'failed') {
      error.value = presentation.processing_error || 'The presentation could not be converted.'
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

async function beginSession() {
  if (!canStart.value) return
  actionBusy.value = true
  error.value = ''
  try {
    activeSession.value = await startClassroomSession({
      subject: Number(selectedSubjectId.value),
      presentation: Number(selectedPresentationId.value),
      cameras: selectedCameraIds.value,
    })
    currentSlideIndex.value = 0
    startTimer()
    connectEngagement(activeSession.value.id)
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

async function changeSlide(nextIndex) {
  if (nextIndex < 0 || nextIndex >= slides.value.length || actionBusy.value) return
  actionBusy.value = true
  error.value = ''
  try {
    await enterSessionSlide(activeSession.value.id, slides.value[nextIndex].id)
    currentSlideIndex.value = nextIndex
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

async function finishSession() {
  if (!activeSession.value || actionBusy.value) return
  actionBusy.value = true
  error.value = ''
  try {
    const ended = await endClassroomSession(activeSession.value.id)
    clearInterval(timer)
    disconnectEngagement()
    activeSession.value = null
    sessions.value = [ended, ...sessions.value.filter((session) => session.id !== ended.id)]
    await router.push({ path: '/analytics', query: { session: String(ended.id) } })
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }).format(new Date(value))
}

watch(selectedSubjectId, () => {
  selectedCameraIds.value = []
})
watch(() => [route.query.subject, route.query.presentation], applyRouteSelection)

onMounted(loadPage)
onUnmounted(() => {
  clearInterval(timer)
  disconnectEngagement()
})
</script>

<template>
  <AppLayout
    :page-title="activeSession ? 'Live Classroom Session' : 'Start New Session'"
    :focus-mode="Boolean(activeSession)"
  >
    <div v-if="error" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {{ error }}
      <button type="button" class="ml-2 font-semibold underline" @click="error = ''">Dismiss</button>
    </div>

    <div v-if="loading" class="page-card p-10 text-center text-sm text-gray-500">
      Loading session setup…
    </div>

    <div v-else-if="!activeSession" class="grid grid-cols-1 xl:grid-cols-3 gap-5">
      <div class="xl:col-span-2 space-y-5">
        <section class="page-card p-6">
          <h2 class="font-semibold text-navy mb-5">Session Details</h2>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label class="block text-sm font-medium text-gray-600">
              Subject and classroom
              <select v-model="selectedSubjectId" class="mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-navy">
                <option value="">Select a subject</option>
                <option v-for="subject in options.subjects" :key="subject.id" :value="subject.id">
                  {{ subject.code }} — {{ subject.name }} ({{ subject.classroom.room_code }})
                </option>
              </select>
            </label>
            <label class="block text-sm font-medium text-gray-600">
              Presentation
              <select v-model="selectedPresentationId" class="mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-navy">
                <option value="">Select a ready presentation</option>
                <option
                  v-for="presentation in options.presentations"
                  :key="presentation.id"
                  :value="presentation.id"
                  :disabled="presentation.processing_status !== 'ready'"
                >
                  {{ presentation.title }} · {{ presentation.processing_status === 'ready' ? `${presentation.total_slides} slides` : presentation.processing_status }}
                </option>
              </select>
            </label>
          </div>

          <div class="mt-5 rounded-xl border border-gray-200 p-4">
            <div class="flex items-center justify-between gap-3">
              <div>
                <h3 class="text-sm font-semibold text-navy">Configured cameras (optional)</h3>
                <p class="text-xs text-gray-400 mt-1">Camera hardware is not connected yet. Selecting a camera only links its configuration to this session.</p>
              </div>
              <span class="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">Hardware pending</span>
            </div>
            <div v-if="selectedSubject?.cameras.length" class="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-4">
              <label v-for="camera in selectedSubject.cameras" :key="camera.id" class="flex items-center gap-2 rounded-lg border border-gray-200 p-3 text-sm text-gray-600">
                <input v-model="selectedCameraIds" type="checkbox" :value="camera.id" class="accent-brand">
                <span>{{ camera.name }} <small class="block text-gray-400">{{ camera.position }}</small></span>
              </label>
            </div>
            <p v-else class="mt-4 text-sm text-gray-400">No active cameras are configured. You can still start the session.</p>
          </div>

          <button type="button" class="btn-primary mt-5" :disabled="!canStart" @click="beginSession">
            {{ actionBusy ? 'Starting…' : 'Start Session' }}
          </button>
        </section>

        <section class="page-card p-6">
          <h2 class="font-semibold text-navy mb-1">Presentation Preview</h2>
          <p class="text-xs text-gray-400 mb-4">PDF files display directly. PPTX files display through their converted PDF.</p>
          <iframe
            v-if="selectedPresentation?.preview_url"
            :src="selectedPresentation.preview_url"
            :title="selectedPresentation.title"
            class="w-full rounded-xl border border-gray-200 bg-gray-50"
            style="height: 480px"
          ></iframe>
          <div v-else class="rounded-xl border border-dashed border-gray-200 py-20 text-center text-sm text-gray-400">
            Select a ready presentation to preview it.
          </div>
        </section>
      </div>

      <aside class="space-y-5">
        <section class="page-card p-5">
          <h2 class="font-semibold text-navy">Upload Presentation</h2>
          <p class="text-xs text-gray-400 mt-1 mb-4">PDF or PPTX, up to 50 MB. The original file is preserved.</p>
          <label class="block text-sm font-medium text-gray-600">
            Title
            <input v-model="uploadTitle" type="text" maxlength="150" class="mt-1.5 w-full rounded-xl border border-gray-200 px-4 py-2.5" placeholder="Lecture title">
          </label>
          <label class="block text-sm font-medium text-gray-600 mt-3">
            File
            <input ref="fileInput" type="file" accept=".pdf,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation" class="mt-1.5 block w-full text-sm text-gray-500" @change="chooseFile">
          </label>
          <button type="button" class="btn-primary w-full justify-center mt-4" :disabled="actionBusy || !uploadFile || !uploadTitle.trim()" @click="submitUpload">
            {{ actionBusy ? 'Uploading and converting…' : 'Upload Presentation' }}
          </button>
          <div v-if="options.presentations.length" class="mt-5 border-t border-gray-100 pt-4">
            <h3 class="text-xs font-semibold uppercase tracking-wide text-gray-400">Presentation Library</h3>
            <div class="mt-3 max-h-64 space-y-2 overflow-y-auto">
              <div v-for="presentation in options.presentations" :key="presentation.id" class="rounded-lg border border-gray-100 p-3">
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium text-navy">{{ presentation.title }}</p>
                    <a :href="presentation.source_url" target="_blank" rel="noopener" class="text-xs text-brand hover:underline">Open original {{ presentation.file_type.toUpperCase() }}</a>
                  </div>
                  <span class="rounded-full px-2 py-0.5 text-xs font-semibold" :class="presentation.processing_status === 'ready' ? 'bg-emerald-50 text-emerald-600' : presentation.processing_status === 'failed' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-700'">
                    {{ presentation.processing_status }}
                  </span>
                </div>
                <p v-if="presentation.processing_status === 'ready'" class="mt-1 text-xs text-gray-400">{{ presentation.total_slides }} generated slides</p>
                <p v-else-if="presentation.processing_error" class="mt-2 text-xs leading-5 text-red-600">{{ presentation.processing_error }}</p>
              </div>
            </div>
          </div>
        </section>

        <section class="page-card p-5">
          <h2 class="font-semibold text-navy mb-3">Recent Sessions</h2>
          <p v-if="!sessions.length" class="py-6 text-center text-sm text-gray-400">No sessions recorded yet.</p>
          <div v-else class="space-y-3">
            <div v-for="session in sessions.slice(0, 5)" :key="session.id" class="rounded-lg border border-gray-100 p-3">
              <div class="flex justify-between gap-3">
                <p class="text-sm font-medium text-navy">{{ session.subject_code }}</p>
                <span class="text-xs font-semibold" :class="session.status === 'completed' ? 'text-emerald-600' : 'text-brand'">{{ session.status }}</span>
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ formatDate(session.started_at) }}</p>
            </div>
          </div>
        </section>
      </aside>
    </div>

    <div v-else class="space-y-5">
      <div class="page-card px-5 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p class="text-xs text-gray-400">{{ activeSession.subject_code }} · {{ activeSession.classroom }}</p>
          <h2 class="font-semibold text-navy">{{ activeSession.presentation_title }}</h2>
        </div>
        <div class="flex items-center gap-4">
          <span class="font-mono text-lg font-semibold text-navy">{{ elapsedDisplay }}</span>
          <button type="button" class="rounded-lg bg-red-500 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50" :disabled="actionBusy" @click="finishSession">
            End Session
          </button>
        </div>
      </div>

      <div class="grid grid-cols-1 xl:grid-cols-4 gap-5">
        <section class="xl:col-span-3 page-card p-5">
          <div v-if="currentSlide" class="flex min-h-[520px] items-center justify-center rounded-xl bg-slate-900 p-4">
            <img :src="currentSlide.image_url" :alt="currentSlide.slide_title" class="max-h-[70vh] max-w-full object-contain">
          </div>
          <div v-else class="flex min-h-[520px] items-center justify-center rounded-xl bg-slate-900 text-sm text-slate-400">
            This presentation has no generated slides.
          </div>
          <div class="mt-4 flex items-center justify-between">
            <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40" :disabled="currentSlideIndex === 0 || actionBusy" @click="changeSlide(currentSlideIndex - 1)">Previous</button>
            <span class="text-sm text-gray-500">Slide {{ currentSlideIndex + 1 }} of {{ slides.length }}</span>
            <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40" :disabled="currentSlideIndex >= slides.length - 1 || actionBusy" @click="changeSlide(currentSlideIndex + 1)">Next</button>
          </div>
        </section>

        <aside class="space-y-5">
          <section class="page-card p-5">
            <div class="flex items-center justify-between gap-2">
              <h3 class="text-sm font-semibold text-navy">Camera Configuration</h3>
              <span class="rounded-full bg-amber-50 px-2 py-1 text-xs font-semibold text-amber-700">Pending</span>
            </div>
            <p class="mt-3 text-xs leading-5 text-gray-500">No live feed is shown because camera hardware integration has not been implemented.</p>
            <div v-if="activeSession.cameras.length" class="space-y-2 mt-4">
              <div v-for="camera in activeSession.cameras" :key="camera.id" class="rounded-lg border border-gray-100 p-3">
                <p class="text-sm font-medium text-navy">{{ camera.name }}</p>
                <p class="text-xs text-gray-400 capitalize">{{ camera.position }} position</p>
              </div>
            </div>
            <p v-else class="mt-4 text-xs text-gray-400">This session has no linked cameras.</p>
          </section>

          <section class="page-card p-5">
            <h3 class="text-sm font-semibold text-navy">Engagement Monitoring</h3>
            <div class="mt-2 flex items-center justify-between text-xs text-gray-500">
              <span>Live updates</span>
              <span :class="socketStatus === 'connected' ? 'text-emerald-600' : 'text-amber-600'">{{ socketStatus }}</span>
            </div>
            <div v-if="liveAlert" class="mt-3 rounded-lg bg-red-50 p-3 text-xs text-red-700" role="alert">
              {{ liveAlert.message }}
            </div>
            <div v-if="latestEngagement" class="mt-4 space-y-3">
              <div v-for="category in engagementCategories" :key="category.key">
                <div class="mb-1 flex justify-between text-xs"><span class="text-gray-600">{{ category.label }}</span><span class="font-semibold" :style="{ color: category.color }">{{ latestEngagement.distribution[category.key] }}%</span></div>
                <div class="h-1.5 overflow-hidden rounded-full bg-gray-100"><div class="h-full rounded-full" :style="{ width: `${latestEngagement.distribution[category.key]}%`, background: category.color }"></div></div>
              </div>
              <p class="text-xs text-gray-400">{{ latestEngagement.total_detected }} detected · {{ latestEngagement.unclassified_count }} unclassified · Slide {{ latestEngagement.slide_number }}</p>
            </div>
            <p v-else class="mt-3 text-xs leading-5 text-gray-500">Waiting for the first aggregated monitoring window.</p>
            <div v-if="options.simulator_enabled" class="mt-4 border-t border-gray-100 pt-4">
              <button v-if="!simulationRunning" type="button" class="btn-primary w-full justify-center" @click="startSimulation">Start Simulation</button>
              <button v-else type="button" class="w-full rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50" @click="stopSimulation">Stop Simulation</button>
              <p class="mt-2 text-xs text-gray-400">Development only · one result every two seconds</p>
            </div>
          </section>
        </aside>
      </div>
    </div>
  </AppLayout>
</template>
