<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { currentUser } from '../auth'
import { availableCameraIds, cameraReadinessLabel } from '../cameraSelection'
import {
  createUploadRequestId,
  presentationDirectionForKey,
} from '../presentationControls'
import {
  endSessionWithRecovery,
  findOwnActiveSession,
  restoreSlideIndex,
  startSessionWithRecovery,
} from '../sessionReliability'
import { createSessionCountdown } from '../sessionCountdown'
import AppLayout from '../layouts/AppLayout.vue'
import PaginationControls from '../components/PaginationControls.vue'
import {
  deletePresentation as deletePresentationRequest,
  endClassroomSession,
  enterSessionSlide,
  fetchPresentationPage,
  fetchSessionPage,
  fetchSessionOptions,
  fetchSessionSubjectPage,
  fetchSessions,
  retryPresentation as retryPresentationRequest,
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
const subjectCount = ref(0)
const subjectPage = ref(1)
const subjectPageSize = 20
const subjectSearch = ref('')
const subjectPageLoading = ref(false)
const presentationCount = ref(0)
const presentationPage = ref(1)
const pageSize = 20
const sessions = ref([])
const sessionCount = ref(0)
const sessionPage = ref(1)
const sessionPageSize = 5
const sessionPageLoading = ref(false)
const selectedSubjectId = ref('')
const selectedPresentationId = ref('')
const selectedCameraIds = ref([])
const uploadTitle = ref('')
const uploadFile = ref(null)
const uploadRequestId = ref(null)
const uploadProgress = ref(null)
const fileInput = ref(null)
const presentationBusyId = ref(null)
const activeSession = ref(null)
const presentationStage = ref(null)
const isFullscreen = ref(false)
const currentSlideIndex = ref(0)
const elapsedSeconds = ref(0)
const latestEngagement = ref(null)
const liveAlert = ref(null)
const socketStatus = ref('disconnected')
const simulationRunning = ref(false)
const countdownSeconds = ref(null)
let timer = null
let simulationTimer = null
let engagementSocket = null
let socketReconnectTimer = null
let socketReconnectAttempts = 0
let subjectSearchTimer = null
const maximumSocketReconnectAttempts = 5
const sessionCountdown = createSessionCountdown({
  seconds: 5,
  onTick: value => { countdownSeconds.value = value },
  onComplete: () => {
    countdownSeconds.value = null
    beginSession()
  },
})

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
const availableCameras = computed(() => selectedSubject.value?.cameras || [])
const slides = computed(() => activeSession.value?.presentation?.slides || [])
const currentSlide = computed(() => slides.value[currentSlideIndex.value] || null)
const canStart = computed(() => (
  selectedSubject.value
  && selectedPresentation.value?.processing_status === 'ready'
  && !actionBusy.value
  && countdownSeconds.value === null
))
const elapsedDisplay = computed(() => {
  const hours = Math.floor(elapsedSeconds.value / 3600)
  const minutes = Math.floor((elapsedSeconds.value % 3600) / 60)
  const seconds = elapsedSeconds.value % 60
  return [hours, minutes, seconds].map((value) => String(value).padStart(2, '0')).join(':')
})
const uploadStatusText = computed(() => {
  if (!uploadProgress.value) return ''
  if (uploadProgress.value.phase === 'processing') {
    return 'Upload complete. Generating slide images…'
  }
  return `Uploading file… ${uploadProgress.value.percent}%`
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

function connectEngagement(sessionId, reconnecting = false) {
  clearTimeout(socketReconnectTimer)
  const previousSocket = engagementSocket
  engagementSocket = null
  previousSocket?.close()
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const socket = new WebSocket(`${protocol}//${window.location.host}/ws/sessions/${sessionId}/engagement/`)
  engagementSocket = socket
  socketStatus.value = reconnecting ? 'reconnecting' : 'connecting'
  socket.onopen = () => {
    socketReconnectAttempts = 0
    socketStatus.value = 'connected'
  }
  socket.onclose = () => {
    if (engagementSocket !== socket) return
    if (activeSession.value?.id !== sessionId) {
      socketStatus.value = 'disconnected'
      return
    }
    if (socketReconnectAttempts >= maximumSocketReconnectAttempts) {
      socketStatus.value = 'unavailable'
      return
    }
    socketReconnectAttempts += 1
    socketStatus.value = 'reconnecting'
    const delay = Math.min(1000 * (2 ** (socketReconnectAttempts - 1)), 8000)
    socketReconnectTimer = setTimeout(() => connectEngagement(sessionId, true), delay)
  }
  socket.onerror = () => {
    if (engagementSocket === socket) socketStatus.value = 'reconnecting'
  }
  socket.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data)
      if (message.type === 'engagement.summary') applyEngagement(message.data)
    } catch {
      error.value = 'A live engagement update could not be read.'
    }
  }
}

function retryEngagementConnection() {
  if (!activeSession.value) return
  socketReconnectAttempts = 0
  connectEngagement(activeSession.value.id)
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
  socketReconnectAttempts = 0
  socketStatus.value = 'disconnected'
}

function activateSession(session) {
  activeSession.value = session
  currentSlideIndex.value = restoreSlideIndex(session)
  startTimer()
  connectEngagement(session.id)
}

function applyRouteSelection() {
  const subject = options.value.subjects.find(item => item.id === Number(route.query.subject))
  const presentation = options.value.presentations.find(item => item.id === Number(route.query.presentation))
  if (subject) selectedSubjectId.value = subject.id
  if (presentation) selectedPresentationId.value = presentation.id
}

function selectAllCameras() {
  selectedCameraIds.value = availableCameraIds(selectedSubject.value)
}

function clearCameraSelection() {
  selectedCameraIds.value = []
}

async function loadPage() {
  loading.value = true
  error.value = ''
  try {
    const [sessionOptions, subjectData, presentationData, sessionHistory, activeSessions] = await Promise.all([
      fetchSessionOptions(),
      fetchSessionSubjectPage({
        page: subjectPage.value,
        selected: route.query.subject || '',
      }),
      fetchPresentationPage({ page: presentationPage.value }),
      fetchSessionPage({ page: sessionPage.value, page_size: sessionPageSize }),
      fetchSessions({ status: 'ongoing', page_size: 100 }),
    ])
    options.value = {
      ...sessionOptions,
      subjects: subjectData.results,
      presentations: presentationData.results,
    }
    subjectCount.value = subjectData.count
    presentationCount.value = presentationData.count
    sessions.value = sessionHistory.results
    sessionCount.value = sessionHistory.count
    applyRouteSelection()
    const ongoing = findOwnActiveSession(activeSessions, currentUser.value?.id)
    if (ongoing) {
      activateSession(ongoing)
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    loading.value = false
  }
}

async function changeSubjectPage(page) {
  subjectPageLoading.value = true
  error.value = ''
  try {
    const data = await fetchSessionSubjectPage({
      page,
      search: subjectSearch.value.trim(),
    })
    subjectPage.value = page
    subjectCount.value = data.count
    options.value.subjects = data.results
    if (!data.results.some((item) => item.id === Number(selectedSubjectId.value))) {
      selectedSubjectId.value = ''
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    subjectPageLoading.value = false
  }
}

async function changeSessionPage(page) {
  sessionPageLoading.value = true
  error.value = ''
  try {
    const data = await fetchSessionPage({ page, page_size: sessionPageSize })
    sessionPage.value = page
    sessions.value = data.results
    sessionCount.value = data.count
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    sessionPageLoading.value = false
  }
}

async function changePresentationPage(page) {
  presentationBusyId.value = null
  error.value = ''
  try {
    const data = await fetchPresentationPage({ page })
    presentationPage.value = page
    presentationCount.value = data.count
    options.value.presentations = data.results
    if (!data.results.some((item) => item.id === Number(selectedPresentationId.value))) {
      selectedPresentationId.value = ''
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  }
}

function chooseFile(event) {
  uploadFile.value = event.target.files?.[0] || null
  uploadRequestId.value = uploadFile.value ? createUploadRequestId() : null
  if (uploadFile.value && !uploadTitle.value) {
    uploadTitle.value = uploadFile.value.name.replace(/\.(pdf|pptx)$/i, '')
  }
}

async function submitUpload() {
  if (!uploadFile.value || !uploadTitle.value.trim()) return
  actionBusy.value = true
  error.value = ''
  uploadProgress.value = { phase: 'uploading', percent: 0 }
  try {
    const presentation = await uploadPresentation({
      title: uploadTitle.value.trim(),
      file: uploadFile.value,
      requestId: uploadRequestId.value || createUploadRequestId(),
      onProgress: (progress) => { uploadProgress.value = progress },
    })
    presentationPage.value = 1
    await changePresentationPage(1)
    selectedPresentationId.value = presentation.id
    uploadTitle.value = ''
    uploadFile.value = null
    uploadRequestId.value = null
    if (fileInput.value) fileInput.value.value = ''
    if (presentation.processing_status === 'failed') {
      error.value = presentation.processing_error || 'The presentation could not be converted.'
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
    uploadProgress.value = null
  }
}

function replacePresentation(updated) {
  options.value.presentations = options.value.presentations.map(
    (presentation) => presentation.id === updated.id ? updated : presentation,
  )
}

async function retryPresentation(presentation) {
  if (presentationBusyId.value) return
  presentationBusyId.value = presentation.id
  error.value = ''
  try {
    const updated = await retryPresentationRequest(presentation.id)
    replacePresentation(updated)
    if (updated.processing_status === 'failed') {
      error.value = updated.processing_error || 'The presentation could not be converted.'
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    presentationBusyId.value = null
  }
}

async function deletePresentation(presentation) {
  if (presentationBusyId.value || presentation.in_use) return
  if (!window.confirm(`Delete “${presentation.title}” and all of its generated files?`)) return
  presentationBusyId.value = presentation.id
  error.value = ''
  try {
    await deletePresentationRequest(presentation.id)
    options.value.presentations = options.value.presentations.filter(
      (item) => item.id !== presentation.id,
    )
    presentationCount.value = Math.max(0, presentationCount.value - 1)
    const finalPage = Math.max(1, Math.ceil(presentationCount.value / pageSize))
    await changePresentationPage(Math.min(presentationPage.value, finalPage))
    if (Number(selectedPresentationId.value) === presentation.id) {
      selectedPresentationId.value = ''
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    presentationBusyId.value = null
  }
}

async function beginSession() {
  if (!canStart.value) return
  actionBusy.value = true
  error.value = ''
  try {
    const started = await startSessionWithRecovery({
      start: () => startClassroomSession({
        subject: Number(selectedSubjectId.value),
        presentation: Number(selectedPresentationId.value),
        cameras: selectedCameraIds.value,
      }),
      fetchSessions,
      userId: currentUser.value?.id,
    })
    sessionPage.value = 1
    sessionCount.value += 1
    sessions.value = [started, ...sessions.value.filter((session) => session.id !== started.id)].slice(0, sessionPageSize)
    activateSession(started)
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

function prepareSession() {
  if (!canStart.value) return
  sessionCountdown.start()
}

function cancelSessionCountdown() {
  if (!sessionCountdown.cancel()) return
  countdownSeconds.value = null
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

function handlePresentationKey(event) {
  const direction = presentationDirectionForKey(event, Boolean(activeSession.value))
  if (!direction) return
  event.preventDefault()
  changeSlide(currentSlideIndex.value + direction)
}

function syncFullscreenState() {
  isFullscreen.value = document.fullscreenElement === presentationStage.value
}

async function toggleFullscreen() {
  error.value = ''
  try {
    if (document.fullscreenElement) {
      await document.exitFullscreen()
      return
    }
    if (!presentationStage.value?.requestFullscreen) {
      throw new Error('Fullscreen presentation is not supported by this browser.')
    }
    await presentationStage.value.requestFullscreen()
  } catch (requestError) {
    error.value = requestError.message || 'Fullscreen presentation could not be opened.'
  }
}

async function finishSession() {
  if (!activeSession.value || actionBusy.value) return
  if (!window.confirm('End this classroom session? You will be taken to its analytics report.')) return
  const sessionId = activeSession.value.id
  actionBusy.value = true
  error.value = ''
  try {
    const ended = await endSessionWithRecovery({
      sessionId,
      end: () => endClassroomSession(sessionId),
      fetchSessions,
    })
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

watch(selectedSubjectId, selectAllCameras)
watch(() => [route.query.subject, route.query.presentation], applyRouteSelection)
watch(subjectSearch, () => {
  clearTimeout(subjectSearchTimer)
  subjectSearchTimer = setTimeout(() => {
    subjectPage.value = 1
    changeSubjectPage(1)
  }, 250)
})

onMounted(() => {
  document.addEventListener('keydown', handlePresentationKey)
  document.addEventListener('fullscreenchange', syncFullscreenState)
  loadPage()
})
onUnmounted(() => {
  document.removeEventListener('keydown', handlePresentationKey)
  document.removeEventListener('fullscreenchange', syncFullscreenState)
  clearTimeout(subjectSearchTimer)
  clearInterval(timer)
  cancelSessionCountdown()
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
            <div role="region" aria-labelledby="session-subject-title">
              <label class="block text-sm font-medium text-gray-600">
                <span id="session-subject-title">Subject and classroom</span>
                <input v-model="subjectSearch" type="search" placeholder="Search subjects…" class="mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-navy">
                <select v-model="selectedSubjectId" class="mt-2 w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-navy">
                  <option value="">Select a subject</option>
                  <option v-for="subject in options.subjects" :key="subject.id" :value="subject.id">
                    {{ subject.code }} — {{ subject.name }} ({{ subject.classroom.room_code }})
                  </option>
                </select>
              </label>
              <PaginationControls class="mt-3 rounded-xl border border-gray-100" :page="subjectPage" :count="subjectCount" :page-size="subjectPageSize" :disabled="subjectPageLoading || actionBusy" @change="changeSubjectPage" />
            </div>
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
                <h3 class="text-sm font-semibold text-navy">Session cameras</h3>
                <p class="text-xs text-gray-400 mt-1">Active cameras from the selected classroom are chosen automatically.</p>
              </div>
              <span v-if="availableCameras.length" class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">{{ selectedCameraIds.length }}/{{ availableCameras.length }} selected</span>
              <span v-else class="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">No active cameras</span>
            </div>
            <template v-if="availableCameras.length">
              <div class="mt-4 flex items-center justify-end gap-2">
                <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50" @click="selectAllCameras">Select all</button>
                <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50" @click="clearCameraSelection">Clear</button>
              </div>
              <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <label v-for="camera in availableCameras" :key="camera.id" class="flex cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm" :class="selectedCameraIds.includes(camera.id) ? 'border-indigo-300 bg-indigo-50/50 text-navy' : 'border-gray-200 text-gray-600'">
                  <input v-model="selectedCameraIds" type="checkbox" :value="camera.id" class="accent-brand">
                  <span class="min-w-0 flex-1"><strong class="block truncate font-semibold">{{ camera.name }}</strong><small class="block text-gray-400">{{ camera.position_label || camera.position }}</small></span>
                  <span class="rounded-full bg-emerald-50 px-2 py-0.5 text-[11px] font-semibold text-emerald-700">{{ camera.status_label || 'Active' }}</span>
                </label>
              </div>
            </template>
            <div v-else-if="selectedSubject" class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              This classroom has no active cameras. You can still start the session and use the development simulator.
            </div>
            <p v-else class="mt-4 text-sm text-gray-400">Select a subject to load its classroom cameras.</p>
          </div>

          <button type="button" class="btn-primary mt-5" :disabled="!canStart" @click="prepareSession">
            {{ actionBusy ? 'Starting…' : countdownSeconds !== null ? 'Preparing…' : 'Start Session' }}
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
            {{ actionBusy ? 'Working…' : 'Upload Presentation' }}
          </button>
          <div v-if="uploadProgress" class="mt-3 rounded-lg bg-indigo-50 p-3" role="status">
            <div class="flex items-center justify-between gap-3 text-xs font-medium text-indigo-700">
              <span>{{ uploadStatusText }}</span>
              <span v-if="uploadProgress.phase === 'uploading'">{{ uploadProgress.percent }}%</span>
            </div>
            <div class="mt-2 h-1.5 overflow-hidden rounded-full bg-indigo-100">
              <div class="h-full rounded-full bg-brand transition-all" :class="uploadProgress.phase === 'processing' ? 'animate-pulse' : ''" :style="{ width: `${uploadProgress.percent}%` }"></div>
            </div>
            <p class="mt-2 text-xs text-indigo-700">PPTX conversion can take up to two minutes.</p>
          </div>
          <div v-if="options.presentations.length" role="region" aria-labelledby="presentation-library-title" class="mt-5 border-t border-gray-100 pt-4">
            <h3 id="presentation-library-title" class="text-xs font-semibold uppercase tracking-wide text-gray-400">Presentation Library</h3>
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
                <p v-if="presentation.in_use" class="mt-2 text-xs text-gray-400">Used by a recorded session · deletion protected</p>
                <div class="mt-3 flex flex-wrap items-center gap-3 text-xs font-semibold">
                  <a v-if="presentation.preview_url" :href="presentation.preview_url" target="_blank" rel="noopener" class="text-brand hover:underline">Preview</a>
                  <button v-if="presentation.processing_status === 'failed'" type="button" class="text-brand hover:underline disabled:opacity-50" :disabled="presentationBusyId === presentation.id" @click="retryPresentation(presentation)">
                    {{ presentationBusyId === presentation.id ? 'Retrying…' : 'Retry conversion' }}
                  </button>
                  <button type="button" class="text-red-600 hover:underline disabled:cursor-not-allowed disabled:opacity-40" :disabled="presentation.in_use || presentationBusyId === presentation.id" @click="deletePresentation(presentation)">
                    Delete
                  </button>
                </div>
              </div>
            </div>
            <PaginationControls :page="presentationPage" :count="presentationCount" :page-size="pageSize" :disabled="Boolean(presentationBusyId)" @change="changePresentationPage" />
          </div>
          <div v-else class="mt-5 rounded-lg border border-dashed border-gray-200 px-4 py-6 text-center">
            <p class="text-sm font-medium text-navy">No presentations yet</p>
            <p class="mt-1 text-xs text-gray-400">Upload a PDF or PPTX to create the first one.</p>
          </div>
        </section>

        <section class="page-card p-5" aria-labelledby="recent-sessions-title">
          <h2 id="recent-sessions-title" class="font-semibold text-navy mb-3">Recent Sessions</h2>
          <p v-if="!sessions.length" class="py-6 text-center text-sm text-gray-400">No sessions recorded yet.</p>
          <div v-else class="space-y-3">
            <div v-for="session in sessions" :key="session.id" class="rounded-lg border border-gray-100 p-3">
              <div class="flex justify-between gap-3">
                <p class="text-sm font-medium text-navy">{{ session.subject_code }}</p>
                <span class="text-xs font-semibold" :class="session.status === 'completed' ? 'text-emerald-600' : 'text-brand'">{{ session.status }}</span>
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ formatDate(session.started_at) }}</p>
            </div>
          </div>
          <PaginationControls class="-mx-5 -mb-5 mt-5" :page="sessionPage" :count="sessionCount" :page-size="sessionPageSize" :disabled="loading || sessionPageLoading || actionBusy" @change="changeSessionPage" />
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
        <section ref="presentationStage" class="presenter-stage xl:col-span-3 page-card p-5">
          <div class="mb-3 flex items-center justify-between gap-3">
            <p class="text-xs text-gray-400">Use ← and → to change slides</p>
            <button type="button" class="rounded-lg border border-gray-200 px-3 py-2 text-xs font-semibold text-gray-600 hover:bg-gray-50" @click="toggleFullscreen">
              {{ isFullscreen ? 'Exit fullscreen' : 'Present fullscreen' }}
            </button>
          </div>
          <div v-if="currentSlide" class="presenter-canvas flex min-h-[520px] items-center justify-center rounded-xl bg-slate-900 p-4">
            <img :src="currentSlide.image_url" :alt="currentSlide.slide_title" class="max-h-[70vh] max-w-full object-contain">
          </div>
          <div v-else class="presenter-canvas flex min-h-[520px] items-center justify-center rounded-xl bg-slate-900 text-sm text-slate-400">
            This presentation has no generated slides.
          </div>
          <div class="presenter-controls mt-4 flex items-center justify-between">
            <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40" :disabled="currentSlideIndex === 0 || actionBusy" @click="changeSlide(currentSlideIndex - 1)">Previous</button>
            <span class="text-sm text-gray-500">Slide {{ currentSlideIndex + 1 }} of {{ slides.length }}</span>
            <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40" :disabled="currentSlideIndex >= slides.length - 1 || actionBusy" @click="changeSlide(currentSlideIndex + 1)">Next</button>
          </div>
        </section>

        <aside class="space-y-5">
          <section class="page-card p-5">
            <div class="flex items-center justify-between gap-2">
              <h3 class="text-sm font-semibold text-navy">Camera Configuration</h3>
              <span v-if="activeSession.cameras.length" class="rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">Configuration ready</span>
              <span v-else class="rounded-full bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-700">Simulator only</span>
            </div>
            <p class="mt-3 text-xs leading-5 text-gray-500">Linked camera records are shown below. Video feeds will remain disconnected until CCTV integration is added.</p>
            <div v-if="activeSession.cameras.length" class="space-y-2 mt-4">
              <div v-for="camera in activeSession.cameras" :key="camera.id" class="rounded-lg border border-gray-100 p-3">
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0"><p class="truncate text-sm font-medium text-navy">{{ camera.name }}</p><p class="text-xs text-gray-400">{{ camera.position_label || camera.position }} position</p></div>
                  <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="camera.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'">{{ cameraReadinessLabel(camera) }}</span>
                </div>
                <div class="mt-2 flex items-center gap-1.5 text-xs text-amber-700"><span class="h-1.5 w-1.5 rounded-full bg-amber-500"></span>Video feed not connected</div>
              </div>
            </div>
            <div v-else class="mt-4 rounded-lg border border-violet-200 bg-violet-50 p-3"><p class="text-xs font-semibold text-violet-700">No cameras linked</p><p class="mt-1 text-xs leading-5 text-violet-600">This session can continue with simulated engagement data.</p></div>
          </section>

          <section class="page-card p-5">
            <h3 class="text-sm font-semibold text-navy">Engagement Monitoring</h3>
            <div class="mt-2 flex items-center justify-between text-xs text-gray-500">
              <span>Live updates</span>
              <span :class="socketStatus === 'connected' ? 'text-emerald-600' : socketStatus === 'unavailable' ? 'text-red-600' : 'text-amber-600'">{{ socketStatus }}</span>
            </div>
            <div v-if="socketStatus === 'unavailable'" class="mt-3 rounded-lg border border-red-100 bg-red-50 p-3 text-xs text-red-700">
              Live updates are unavailable. The classroom session remains active.
              <button type="button" class="ml-1 font-semibold underline" @click="retryEngagementConnection">Retry connection</button>
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

    <Teleport to="body">
      <div
        v-if="countdownSeconds !== null"
        class="fixed inset-0 z-[100] flex items-center justify-center bg-slate-950/90 px-6"
        role="dialog"
        aria-modal="true"
        aria-labelledby="session-countdown-title"
        @keydown.esc="cancelSessionCountdown"
      >
        <div class="w-full max-w-lg rounded-2xl border border-white/10 bg-slate-900 p-10 text-center text-white shadow-2xl">
          <p class="text-sm font-semibold uppercase tracking-[0.25em] text-indigo-300">Get Ready</p>
          <h2 id="session-countdown-title" class="mt-3 text-2xl font-semibold">Your classroom session is about to begin</h2>
          <p class="mt-8 text-8xl font-bold tabular-nums" aria-live="assertive">{{ countdownSeconds }}</p>
          <p class="mt-6 text-sm text-slate-300">Cameras, timing, and analytics will start after the countdown.</p>
          <button
            type="button"
            class="mt-8 rounded-lg border border-white/25 px-5 py-2.5 text-sm font-semibold text-white hover:bg-white/10"
            autofocus
            @click="cancelSessionCountdown"
          >
            Cancel session start
          </button>
        </div>
      </div>
    </Teleport>
  </AppLayout>
</template>
