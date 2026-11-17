<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { currentUser } from '../auth'
import {
  availableCameraIds,
  cameraReadinessClass,
  cameraReadinessLabel,
} from '../cameraSelection'
import {
  createUploadRequestId,
  presentationDirectionForKey,
} from '../presentationControls'
import {
  endSessionWithRecovery,
  continueLessonWithRecovery,
  finishLessonWithRecovery,
  findOwnActiveSession,
  findOwnPreparedSession,
  restoreSlideIndex,
  startSessionWithRecovery,
} from '../sessionReliability'
import { createSessionCountdown } from '../sessionCountdown'
import { lessonState, meetingOutcome } from '../sessionLabels'
import { cameraStateClass, cameraStateMessage, mergeCameraHealth } from '../cameraHealth'
import AppLayout from '../layouts/AppLayout.vue'
import AppConfirmDialog from '../components/AppConfirmDialog.vue'
import AppDialog from '../components/AppDialog.vue'
import PaginationControls from '../components/PaginationControls.vue'
import SessionEndDialog from '../components/SessionEndDialog.vue'
import { useConfirmation } from '../useConfirmation'
import {
  archiveClassroomSession,
  cancelPreparedClassroomSession,
  checkSessionCameraAvailability,
  deletePresentation as deletePresentationRequest,
  endClassroomSession,
  enterSessionSlide,
  fetchPresentationPage,
  fetchSessionPage,
  fetchSessionOptions,
  fetchSessionCameraHealth,
  fetchSessionSubjectPage,
  fetchSessions,
  fetchClassroomSession,
  fetchLesson,
  fetchLessonPage,
  finishSavedLesson,
  prepareLessonContinuation,
  prepareClassroomSession,
  retryPresentation as retryPresentationRequest,
  restoreClassroomSession,
  restorePresentation,
  startPreparedClassroomSession,
  simulateEngagement,
  uploadPresentation,
} from '../sessions'

const route = useRoute()
const router = useRouter()
const isTeacher = computed(() => ['org_admin', 'teacher'].includes(currentUser.value?.role))

const loading = ref(true)
const error = ref('')
const notice = ref('')
const lessons = ref([])
const lessonCount = ref(0)
const lessonPage = ref(1)
const lessonsLoading = ref(false)
const lessonsError = ref('')
const selectedLesson = ref(null)
const continuationRequestId = ref(null)
const setupHeading = ref(null)
const pendingAction = ref(null)
const endDialogOpen = ref(false)
const finishingSavedLesson = ref(null)
const endAction = ref('')
const actionBusy = ref(false)
const options = ref({ subjects: [], presentations: [] })
const subjectCount = ref(0)
const subjectPage = ref(1)
const subjectPageSize = 20
const subjectSearch = ref('')
const subjectPageLoading = ref(false)
const presentationCount = ref(0)
const presentationPage = ref(1)
const presentationLibrary = ref([])
const presentationLifecycle = ref('active')
const pageSize = 20
const sessions = ref([])
const sessionCount = ref(0)
const sessionPage = ref(1)
const sessionPageSize = 5
const sessionPageLoading = ref(false)
const historyHeading = ref(null)
const sessionLifecycle = ref('active')
const supportPanel = ref(route.query.lesson ? 'history' : 'presentations')
const selectedSubjectId = ref('')
const selectedPresentationId = ref('')
const selectedCameraIds = ref([])
const uploadTitle = ref('')
const uploadFile = ref(null)
const uploadRequestId = ref(null)
const uploadProgress = ref(null)
const fileInput = ref(null)
const presentationBusyId = ref(null)
const preparedSession = ref(null)
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
const cameraHealth = ref([])
const cameraHealthStatus = ref('idle')
const cameraAvailability = ref({})
const { confirmation, requestConfirmation, acceptConfirmation, cancelConfirmation } = useConfirmation()
let timer = null
let cameraHealthTimer = null
let cameraHealthRequestActive = false
let cameraAvailabilityTimer = null
let cameraAvailabilityRequestActive = false
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
    startPreparedSession()
  },
})

const engagementCategories = [
  { key: 'engaged', label: 'Engaged', color: 'var(--state-engaged)', textColor: 'var(--primary-dark)' },
  { key: 'attentive', label: 'Attentive', color: 'var(--state-attentive)', textColor: 'var(--primary-dark)' },
  { key: 'confused', label: 'Confused', color: 'var(--state-confused)', textColor: 'var(--text-muted)' },
  { key: 'bored', label: 'Bored', color: 'var(--state-bored)', textColor: 'var(--text-muted)' },
  { key: 'disengaged', label: 'Disengaged', color: 'var(--state-disengaged)', textColor: 'var(--text)' },
]

const selectedSubject = computed(() => options.value.subjects.find(
  (subject) => subject.id === Number(selectedSubjectId.value),
))
const selectedPresentation = computed(() => options.value.presentations.find(
  (presentation) => presentation.id === Number(selectedPresentationId.value),
))
const availableCameras = computed(() => selectedSubject.value?.cameras || [])
const monitoredSession = computed(() => activeSession.value || preparedSession.value)
const slides = computed(() => monitoredSession.value?.presentation?.slides || [])
const currentSlide = computed(() => slides.value[currentSlideIndex.value] || null)
const activeCameras = computed(() => mergeCameraHealth(
  monitoredSession.value?.cameras || [], cameraHealth.value,
))
const preparedHasCameras = computed(() => Boolean(preparedSession.value?.cameras?.length))
const preparedCamerasReady = computed(() => (
  !preparedHasCameras.value
  || preparedSession.value.cameras.every(camera => (
    cameraHealth.value.some(health => (
      health.camera_id === camera.id && health.state === 'online'
    ))
  ))
))
const simulatorAvailable = computed(() => (
  options.value.simulator_enabled
  && Boolean(activeSession.value)
  && !(activeSession.value?.cameras || []).length
))
const selectedCamerasAvailable = computed(() => selectedCameraIds.value.every(
  cameraId => cameraAvailability.value[cameraId] === 'available',
))
const canPrepare = computed(() => (
  selectedSubject.value
  && selectedPresentation.value?.processing_status === 'ready'
  && !preparedSession.value
  && !activeSession.value
  && !actionBusy.value
  && !pendingAction.value
  && selectedCamerasAvailable.value
))
const canStartPrepared = computed(() => (
  preparedSession.value
  && preparedCamerasReady.value
  && !actionBusy.value
  && countdownSeconds.value === null
  && !pendingAction.value
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
  if (typeof fields.detail === 'string') return fields.detail
  for (const value of Object.values(fields)) {
    if (Array.isArray(value) && value.length) return value[0]
  }
  return errorObject.message
}

async function loadLessons(page = lessonPage.value) {
  lessonsLoading.value = true
  lessonsError.value = ''
  try {
    const result = await fetchLessonPage({ status: 'saved', page, page_size: 4 })
    lessons.value = result.results
    lessonCount.value = result.count
    lessonPage.value = page
  } catch (requestError) {
    if (page > 1 && requestError.status === 404) return loadLessons(1)
    lessonsError.value = messageFrom(requestError)
  } finally {
    lessonsLoading.value = false
  }
}

function clearMeeting() {
  clearInterval(timer)
  cancelSessionCountdown()
  disconnectEngagement()
  stopCameraHealth()
  activeSession.value = null
  preparedSession.value = null
  selectedLesson.value = null
  continuationRequestId.value = null
}

async function applyMeetingState(session) {
  if (monitoredSession.value?.id === session.id && session.lesson?.revision < monitoredSession.value.lesson?.revision) return
  if (session.status === 'ongoing') {
    if (activeSession.value?.id === session.id) {
      activeSession.value = session
      currentSlideIndex.value = restoreSlideIndex(session)
    } else activateSession(session)
  } else if (session.status === 'preparing') {
    if (preparedSession.value?.id === session.id) preparedSession.value = session
    else activatePreparation(session)
  } else {
    clearMeeting()
    endDialogOpen.value = false
    finishingSavedLesson.value = null
    notice.value = session.end_action === 'save'
      ? `Class saved at slide ${session.lesson?.last_slide_number || 1}. Choose Continue Lesson when you are ready.`
      : 'This class has finished. Its analytics and reports remain available.'
    await Promise.all([loadLessons(1), changeSessionPage(1)])
    const nextId = session.lesson?.active_session || session.lesson?.prepared_session
    if (nextId && nextId !== session.id) {
      try { await applyMeetingState(await fetchClassroomSession(nextId)) }
      catch (requestError) { error.value = messageFrom(requestError) }
    }
  }
}

async function chooseSavedLesson(lesson) {
  if (actionBusy.value || pendingAction.value) return
  actionBusy.value = true
  error.value = ''
  try {
    const fresh = await fetchLesson(lesson.id)
    const existing = fresh.prepared_session || fresh.active_session
    if (existing) {
      await applyMeetingState(await fetchClassroomSession(existing))
      notice.value = 'This lesson already has a class open. Its current setup has been restored.'
      return
    }
    if (!fresh.can_continue) throw new Error(fresh.blocking_reason || 'This lesson cannot be continued.')
    const [previous, subjectData] = await Promise.all([
      fetchClassroomSession(fresh.latest_session),
      fetchSessionSubjectPage({ selected: fresh.subject }),
    ])
    const subject = subjectData.results.find(item => item.id === fresh.subject)
    if (!subject) throw new Error('The saved subject is unavailable. Ask your organization admin to review its assignment.')
    options.value.subjects = [subject, ...options.value.subjects.filter(item => item.id !== subject.id)]
    options.value.presentations = [previous.presentation, ...options.value.presentations.filter(item => item.id !== previous.presentation.id)]
    selectedSubjectId.value = fresh.subject
    selectedPresentationId.value = fresh.presentation
    await nextTick()
    const currentCameraIds = new Set(subject.cameras.map(camera => camera.id))
    selectedCameraIds.value = previous.cameras.map(camera => camera.id).filter(id => currentCameraIds.has(id))
    selectedLesson.value = fresh
    continuationRequestId.value = null
    notice.value = 'Saved lesson selected. Review the cameras, then prepare your continuation.'
    if (selectedCameraIds.value.length !== previous.cameras.length) notice.value += ' Some previous cameras are no longer active.'
    await nextTick()
    setupHeading.value?.focus()
  } catch (requestError) {
    error.value = messageFrom(requestError)
    loadLessons()
  } finally {
    actionBusy.value = false
  }
}

function clearSavedSelection() {
  if (actionBusy.value || pendingAction.value) return
  selectedLesson.value = null
  continuationRequestId.value = null
  notice.value = ''
}

function openEndDialog(lesson = null) {
  if (actionBusy.value || pendingAction.value) return
  error.value = ''
  finishingSavedLesson.value = lesson
  endDialogOpen.value = true
}

function closeEndDialog() {
  if (actionBusy.value || pendingAction.value) return
  endDialogOpen.value = false
  finishingSavedLesson.value = null
}

async function checkPendingAction() {
  if (!pendingAction.value || actionBusy.value) return
  actionBusy.value = true
  endAction.value = 'checking'
  error.value = ''
  try {
    const pending = pendingAction.value
    if (pending.type === 'finish') {
      const lesson = await fetchLesson(pending.lessonId)
      finishingSavedLesson.value = lesson
      if (lesson.state === 'completed') {
        endDialogOpen.value = false
        finishingSavedLesson.value = null
        notice.value = 'Lesson finished. Its class history remains available.'
      } else error.value = 'The lesson is still saved. Review it before trying again.'
      await loadLessons()
    } else if (pending.type === 'continue') {
      const lesson = await fetchLesson(pending.lessonId)
      selectedLesson.value = lesson
      const sessionId = lesson.prepared_session || lesson.active_session
      if (sessionId) await applyMeetingState(await fetchClassroomSession(sessionId))
      else {
        continuationRequestId.value = null
        error.value = 'The lesson remains saved. You can prepare it again.'
      }
    } else {
      try {
        const session = await fetchClassroomSession(pending.sessionId)
        await applyMeetingState(session)
        if (!session.ended_at) error.value = 'The class remains open. Review its current state before trying again.'
      } catch (readError) {
        if (readError.status !== 404 || pending.type !== 'cancel') throw readError
        clearMeeting()
        notice.value = 'Preparation is closed. Your saved lesson remains available.'
        await loadLessons()
      }
    }
    pendingAction.value = null
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
    endAction.value = ''
  }
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
  if (simulationRunning.value || !simulatorAvailable.value) return
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

async function loadCameraHealth(sessionId) {
  if (cameraHealthRequestActive || monitoredSession.value?.id !== sessionId) return
  cameraHealthRequestActive = true
  try {
    const response = await fetchSessionCameraHealth(sessionId)
    if (monitoredSession.value?.id !== sessionId) return
    cameraHealth.value = response.cameras || []
    cameraHealthStatus.value = 'ready'
    if (!actionBusy.value && !pendingAction.value) {
      const session = await fetchClassroomSession(sessionId)
      if (monitoredSession.value?.id === sessionId && !actionBusy.value && !pendingAction.value) {
        await applyMeetingState(session)
      }
    }
  } catch (requestError) {
    if (preparedSession.value?.id === sessionId && requestError.status === 404) {
      selectedPresentationId.value = ''
      preparedSession.value = null
      selectedLesson.value = null
      stopCameraHealth()
      cancelSessionCountdown()
      error.value = 'Preparation expired or was cancelled. Saved lessons remain available below.'
      loadLessons()
    } else if (monitoredSession.value?.id === sessionId) {
      cameraHealthStatus.value = 'unavailable'
      if ([401, 403].includes(requestError.status)) {
        cancelSessionCountdown()
        pendingAction.value = { type: 'status', sessionId }
        error.value = 'Sign in again to refresh this class. Your progress stays on the server.'
      }
    }
  } finally {
    cameraHealthRequestActive = false
  }
}

function startCameraHealth(sessionId) {
  clearInterval(cameraHealthTimer)
  cameraHealth.value = []
  cameraHealthStatus.value = 'loading'
  loadCameraHealth(sessionId)
  cameraHealthTimer = setInterval(() => loadCameraHealth(sessionId), 2000)
}

function stopCameraHealth() {
  clearInterval(cameraHealthTimer)
  cameraHealthTimer = null
  cameraHealth.value = []
  cameraHealthStatus.value = 'idle'
}

function activateSession(session) {
  const alreadyMonitoring = preparedSession.value?.id === session.id
  cancelSessionCountdown()
  stopCameraAvailability()
  preparedSession.value = null
  activeSession.value = session
  currentSlideIndex.value = restoreSlideIndex(session)
  notice.value = session.continued_from ? 'Lesson continued from its saved slide.' : ''
  startTimer()
  connectEngagement(session.id)
  if (!alreadyMonitoring) startCameraHealth(session.id)
}

function activatePreparation(session) {
  stopCameraAvailability()
  activeSession.value = null
  preparedSession.value = session
  currentSlideIndex.value = restoreSlideIndex(session)
  notice.value = session.continued_from ? `Continuation prepared. Teaching will start on slide ${session.lesson.last_slide_number}.` : ''
  elapsedSeconds.value = 0
  startCameraHealth(session.id)
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

function toggleCameraFreeMode(event) {
  if (event.target.checked) clearCameraSelection()
  else selectAllCameras()
}

function stopCameraAvailability() {
  clearInterval(cameraAvailabilityTimer)
  cameraAvailabilityTimer = null
}

async function refreshCameraAvailability() {
  const cameraIds = availableCameraIds(selectedSubject.value)
  if (!cameraIds.length || cameraAvailabilityRequestActive) return
  cameraAvailabilityRequestActive = true
  for (const cameraId of cameraIds) {
    if (!cameraAvailability.value[cameraId]) cameraAvailability.value[cameraId] = 'checking'
  }
  try {
    const response = await checkSessionCameraAvailability(cameraIds)
    const currentIds = new Set(availableCameraIds(selectedSubject.value))
    for (const camera of response.cameras) {
      if (currentIds.has(camera.camera_id)) {
        cameraAvailability.value[camera.camera_id] = camera.state
      }
    }
  } catch {
    for (const cameraId of cameraIds) cameraAvailability.value[cameraId] = 'offline'
  } finally {
    cameraAvailabilityRequestActive = false
  }
}

function startCameraAvailability() {
  stopCameraAvailability()
  cameraAvailability.value = {}
  if (!selectedSubject.value) return
  refreshCameraAvailability()
  cameraAvailabilityTimer = setInterval(refreshCameraAvailability, 5000)
}

async function loadPage() {
  loading.value = true
  error.value = ''
  try {
    const [sessionOptions, subjectData, presentationData, sessionHistory, activeSessions, preparedSessions] = await Promise.all([
      fetchSessionOptions(),
      fetchSessionSubjectPage({
        page: subjectPage.value,
        selected: route.query.subject || '',
      }),
      fetchPresentationPage({ page: presentationPage.value, lifecycle: 'active' }),
      fetchSessionPage({ page: sessionPage.value, page_size: sessionPageSize, lifecycle: sessionLifecycle.value, lesson: route.query.lesson }),
      fetchSessions({ status: 'ongoing', owner: 'me', page_size: 1 }),
      fetchSessions({ status: 'preparing', owner: 'me', page_size: 1 }),
    ])
    const ongoing = findOwnActiveSession(activeSessions, currentUser.value?.id)
    const prepared = findOwnPreparedSession(preparedSessions, currentUser.value?.id)
    let resolvedSubjectData = subjectData
    if (prepared && !subjectData.results.some(subject => subject.id === prepared.subject)) {
      resolvedSubjectData = await fetchSessionSubjectPage({
        selected: prepared.subject,
        page_size: subjectPageSize,
      })
    }
    const restoredPresentation = prepared?.presentation
    const restoredPresentations = (
      restoredPresentation
      && !presentationData.results.some(item => item.id === restoredPresentation.id)
    ) ? [restoredPresentation, ...presentationData.results] : presentationData.results
    options.value = {
      ...sessionOptions,
      subjects: resolvedSubjectData.results,
      presentations: restoredPresentations,
    }
    subjectCount.value = resolvedSubjectData.count
    presentationCount.value = presentationData.count
    presentationLibrary.value = presentationData.results
    sessions.value = sessionHistory.results
    sessionCount.value = sessionHistory.count
    if (ongoing) {
      activateSession(ongoing)
    } else if (prepared) {
      activatePreparation(prepared)
      selectedSubjectId.value = prepared.subject
      selectedPresentationId.value = prepared.presentation.id
      selectedCameraIds.value = prepared.cameras.map(camera => camera.id)
    } else {
      applyRouteSelection()
    }
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    loading.value = false
    loadLessons()
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
    const data = await fetchSessionPage({ page, page_size: sessionPageSize, lifecycle: sessionLifecycle.value, lesson: route.query.lesson })
    sessionPage.value = page
    sessions.value = data.results
    sessionCount.value = data.count
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    sessionPageLoading.value = false
  }
}

async function showLessonHistory(lessonId) {
  supportPanel.value = 'history'
  await router.replace({ query: { ...route.query, lesson: lessonId || undefined } })
  await nextTick()
  historyHeading.value?.focus()
}

async function changePresentationPage(page) {
  presentationBusyId.value = null
  error.value = ''
  try {
    const data = await fetchPresentationPage({ page, lifecycle: presentationLifecycle.value })
    presentationPage.value = page
    presentationCount.value = data.count
    presentationLibrary.value = data.results
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
  if (actionBusy.value || !uploadFile.value || !uploadTitle.value.trim()) return
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
    options.value.presentations = [
      presentation,
      ...options.value.presentations.filter(item => item.id !== presentation.id),
    ]
    presentationLifecycle.value = 'active'
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
  presentationLibrary.value = presentationLibrary.value.map(
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
  if (presentationBusyId.value) return
  const action = presentation.in_use ? 'Archive' : 'Permanently delete'
  const detail = presentation.in_use
    ? 'Completed sessions and reports will be preserved.'
    : 'The original, preview, and generated slides will be removed. This cannot be undone.'
  const confirmed = await requestConfirmation({
    title: `${action} presentation?`,
    description: `${presentation.title}: ${detail}`,
    confirmLabel: action,
  })
  if (!confirmed) return
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

async function restoreArchivedPresentation(presentation) {
  if (presentationBusyId.value) return
  presentationBusyId.value = presentation.id
  error.value = ''
  try {
    const restored = await restorePresentation(presentation.id)
    if (!options.value.presentations.some(item => item.id === restored.id)) {
      options.value.presentations.unshift(restored)
    }
    await changePresentationPage(presentationPage.value)
  } catch (requestError) {
    error.value = messageFrom(requestError)
  } finally {
    presentationBusyId.value = null
  }
}

async function archiveSession(session) {
  const confirmed = await requestConfirmation({
    title: 'Archive classroom session?',
    description: `${session.subject_code} will move to archived sessions. Its analytics and reports stay available.`,
    confirmLabel: 'Archive session',
  })
  if (!confirmed) return
  error.value = ''
  try {
    await archiveClassroomSession(session.id)
    await changeSessionPage(sessionPage.value)
  } catch (requestError) {
    error.value = messageFrom(requestError)
  }
}

async function restoreArchivedSession(session) {
  error.value = ''
  try {
    await restoreClassroomSession(session.id)
    await changeSessionPage(sessionPage.value)
  } catch (requestError) {
    error.value = messageFrom(requestError)
  }
}

watch(presentationLifecycle, () => {
  presentationPage.value = 1
  changePresentationPage(1)
})

watch(sessionLifecycle, () => {
  sessionPage.value = 1
  changeSessionPage(1)
})

async function prepareSession() {
  if (!canPrepare.value) return
  actionBusy.value = true
  error.value = ''
  try {
    let prepared
    if (selectedLesson.value) {
      const lesson = selectedLesson.value
      continuationRequestId.value ||= createUploadRequestId()
      prepared = await continueLessonWithRecovery({
        lessonId: lesson.id, requestId: continuationRequestId.value,
        prepare: () => prepareLessonContinuation(lesson.id, {
          requestId: continuationRequestId.value, revision: lesson.revision,
          fromSession: lesson.latest_session, cameras: selectedCameraIds.value,
        }),
        fetchLesson, fetchSession: fetchClassroomSession,
      })
    } else {
      prepared = await prepareClassroomSession({
        subject: Number(selectedSubjectId.value), presentation: Number(selectedPresentationId.value),
        cameras: selectedCameraIds.value,
      })
    }
    await applyMeetingState(prepared)
  } catch (requestError) {
    if (requestError.recoveredLesson) selectedLesson.value = requestError.recoveredLesson
    if (requestError.recoveredSession && !requestError.recoveredSession.ended_at) {
      await applyMeetingState(requestError.recoveredSession)
      notice.value = 'This lesson was already prepared in another tab. Its current class is open.'
    } else if (requestError.recoveryPending && selectedLesson.value) {
      pendingAction.value = { type: 'continue', lessonId: selectedLesson.value.id }
    } else if (!requestError.recoveryPending) continuationRequestId.value = null
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

function beginPreparedSession() {
  if (!canStartPrepared.value || pendingAction.value) return
  sessionCountdown.start()
}

async function startPreparedSession() {
  if (!preparedSession.value || !preparedCamerasReady.value || actionBusy.value || pendingAction.value) return
  actionBusy.value = true
  error.value = ''
  const sessionId = preparedSession.value.id
  try {
    const started = await startSessionWithRecovery({
      start: () => startPreparedClassroomSession(sessionId, preparedSession.value.lesson?.revision),
      sessionId, fetchSession: fetchClassroomSession,
      userId: currentUser.value?.id,
    })
    sessionPage.value = 1
    sessionCount.value += 1
    sessions.value = [started, ...sessions.value.filter((session) => session.id !== started.id)].slice(0, sessionPageSize)
    await applyMeetingState(started)
  } catch (requestError) {
    if (requestError.recoveredSession) await applyMeetingState(requestError.recoveredSession)
    if (requestError.recoveryPending) pendingAction.value = { type: 'start', sessionId }
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

async function cancelPreparation() {
  if (!preparedSession.value || actionBusy.value || pendingAction.value) return
  const confirmed = await requestConfirmation({
    title: 'Cancel session preparation?',
    description: 'The camera worker will stop. Saved lesson progress remains available and no classroom timing or analytics will start.',
    confirmLabel: 'Cancel preparation',
  })
  if (!confirmed) return
  actionBusy.value = true
  error.value = ''
  const sessionId = preparedSession.value.id
  try {
    await cancelPreparedClassroomSession(sessionId)
    clearMeeting()
    notice.value = 'Preparation cancelled. Saved lesson progress remains available.'
    await loadLessons()
  } catch (requestError) {
    try {
      await applyMeetingState(await fetchClassroomSession(sessionId))
    } catch (readError) {
      if (readError.status === 404) {
        clearMeeting()
        notice.value = 'Preparation is closed. Saved lesson progress remains available.'
        await loadLessons()
      } else pendingAction.value = { type: 'cancel', sessionId }
    }
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
  }
}

function cancelSessionCountdown() {
  if (!sessionCountdown.cancel()) return
  countdownSeconds.value = null
}

async function changeSlide(nextIndex) {
  if (nextIndex < 0 || nextIndex >= slides.value.length || actionBusy.value || pendingAction.value || endDialogOpen.value) return
  if (preparedSession.value && !activeSession.value) {
    currentSlideIndex.value = nextIndex
    return
  }
  actionBusy.value = true
  error.value = ''
  const sessionId = activeSession.value.id
  const target = slides.value[nextIndex]
  try {
    const result = await enterSessionSlide(sessionId, target.id, activeSession.value.lesson?.revision)
    currentSlideIndex.value = nextIndex
    activeSession.value.current_slide = target.id
    if (activeSession.value.lesson && result.lesson_revision) {
      activeSession.value.lesson.revision = result.lesson_revision
      activeSession.value.lesson.last_slide = target.id
      activeSession.value.lesson.last_slide_number = target.slide_number
    }
  } catch (requestError) {
    try {
      const session = await fetchClassroomSession(sessionId)
      await applyMeetingState(session)
      if (session.current_slide !== target.id) error.value = messageFrom(requestError)
    } catch {
      pendingAction.value = { type: 'slide', sessionId }
      error.value = messageFrom(requestError)
    }
  } finally {
    actionBusy.value = false
  }
}

function handlePresentationKey(event) {
  if (endDialogOpen.value || pendingAction.value) return
  const direction = presentationDirectionForKey(event, Boolean(monitoredSession.value))
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

async function finishSession(action = 'finish') {
  if ((!activeSession.value && !finishingSavedLesson.value) || actionBusy.value || pendingAction.value) return
  actionBusy.value = true
  endAction.value = action
  error.value = ''
  const savedLesson = finishingSavedLesson.value
  const sessionId = activeSession.value?.id
  try {
    if (savedLesson) {
      await finishLessonWithRecovery({
        lessonId: savedLesson.id, fetchLesson,
        finish: () => finishSavedLesson(savedLesson.id, savedLesson.revision),
      })
      endDialogOpen.value = false
      finishingSavedLesson.value = null
      if (selectedLesson.value?.id === savedLesson.id) {
        selectedLesson.value = null
        continuationRequestId.value = null
      }
      notice.value = 'Lesson finished. Its class history, analytics, and reports remain available.'
      await loadLessons()
    } else {
      const ended = await endSessionWithRecovery({
        sessionId, action, fetchSession: fetchClassroomSession,
        end: () => endClassroomSession(sessionId, action, activeSession.value.lesson?.revision),
      })
      await applyMeetingState(ended)
      if (action === 'finish') await router.push({ path: '/analytics', query: { session: String(ended.id) } })
    }
  } catch (requestError) {
    if (requestError.recoveredSession) await applyMeetingState(requestError.recoveredSession)
    if (requestError.recoveredLesson) finishingSavedLesson.value = requestError.recoveredLesson
    if (requestError.recoveryPending) pendingAction.value = savedLesson
      ? { type: 'finish', lessonId: savedLesson.id }
      : { type: 'end', sessionId, action }
    error.value = messageFrom(requestError)
  } finally {
    actionBusy.value = false
    endAction.value = ''
  }
}

function formatDate(value) {
  if (!value) return '—'
  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
  }).format(new Date(value))
}

function formatHeartbeat(value) {
  return value ? formatDate(value) : 'No heartbeat yet'
}

watch(selectedSubjectId, () => {
  if (preparedSession.value || activeSession.value) {
    stopCameraAvailability()
    return
  }
  selectAllCameras()
  startCameraAvailability()
})
watch(() => [route.query.subject, route.query.presentation], applyRouteSelection)
watch(() => route.query.lesson, () => changeSessionPage(1))
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
  stopCameraHealth()
  stopCameraAvailability()
})
</script>

<template>
  <AppLayout
    page-title="Live Session"
    :focus-mode="Boolean(activeSession || preparedSession)"
  >
    <div v-if="error" class="mb-5 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">
      {{ error }}
      <button type="button" class="ml-2 font-semibold underline" @click="error = ''">Dismiss</button>
    </div>
    <div v-if="notice" class="page-card mb-5 p-4 text-sm" role="status">{{ notice }}</div>
    <div v-if="pendingAction && !endDialogOpen" class="page-card mb-5 p-5" role="region" aria-label="Class recovery">
      <p class="text-sm">The last action is still unconfirmed. Reconnect and check its saved status before continuing.</p>
      <div class="mt-3 flex flex-wrap items-center gap-4">
        <button type="button" class="btn-primary" :disabled="actionBusy" @click="checkPendingAction">{{ actionBusy ? 'Checking status…' : 'Check status' }}</button>
        <a href="/" class="text-sm font-semibold text-brand">Sign in again</a>
      </div>
    </div>

    <div v-if="loading" class="page-card p-10 text-center text-sm text-gray-500">
      Loading session setup…
    </div>

    <template v-else-if="!activeSession && !preparedSession">
    <section v-if="isTeacher" class="app-page-hero teacher-session-hero page-card">
      <div class="teacher-session-hero-copy">
        <h1>Live Session</h1>
        <p>Prepare, upload, and manage your classroom session and presentations.</p>
      </div>
      <img src="/illustrations/teacher-hero.png" width="1536" height="1024" alt="" aria-hidden="true" class="teacher-session-hero-art">
    </section>
    <section class="page-card mb-6 p-6" role="region" aria-labelledby="saved-lessons-title">
      <div class="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="saved-lessons-title" class="font-semibold text-navy">Saved for Later</h2>
          <p class="mt-1 text-sm text-gray-500">Continue an unfinished lesson from its saved slide.</p>
        </div>
        <button type="button" class="btn-secondary" :disabled="lessonsLoading || actionBusy || Boolean(pendingAction)" @click="loadLessons()">Refresh lessons</button>
      </div>
      <p v-if="lessonsError" class="mt-4 text-sm text-red-700" role="alert">{{ lessonsError }} <button type="button" class="font-semibold underline" @click="loadLessons()">Retry lessons</button></p>
      <p v-if="lessonsLoading" class="mt-5 text-sm text-gray-500">Loading saved lessons…</p>
      <p v-else-if="!lessons.length && !lessonsError" class="mt-5 text-sm text-gray-500">Lessons you save will appear here.</p>
      <div v-else class="mt-5 grid gap-4 md:grid-cols-2">
        <article v-for="lesson in lessons" :key="lesson.id" class="rounded-xl border border-gray-200 p-4" :aria-label="lesson.presentation_title">
          <h3 class="font-semibold text-navy break-words">{{ lesson.presentation_title }}</h3>
          <p class="mt-1 text-sm text-gray-500">{{ lesson.subject_name }} · {{ lesson.classroom_name }}</p>
          <p class="mt-3 text-sm font-semibold">Slide {{ lesson.last_slide_number }} of {{ lesson.total_slides }}</p>
          <p class="mt-1 text-xs text-gray-500">Last taught {{ formatDate(lesson.last_taught_at) }}</p>
          <p v-if="lesson.blocking_reason" class="mt-3 text-sm text-gray-500">{{ lesson.blocking_reason }}</p>
          <div class="mt-4 flex flex-wrap gap-3">
            <button type="button" class="btn-secondary" :disabled="actionBusy || Boolean(pendingAction) || (!lesson.can_continue && !lesson.prepared_session && !lesson.active_session)" @click="chooseSavedLesson(lesson)">{{ lesson.prepared_session ? 'Open Preparation' : 'Continue Lesson' }}</button>
            <button type="button" class="btn-secondary" :disabled="actionBusy || Boolean(pendingAction) || Boolean(lesson.prepared_session || lesson.active_session)" @click="openEndDialog(lesson)">Finish Lesson</button>
            <button type="button" class="btn-secondary" @click="showLessonHistory(lesson.id)">Class history</button>
          </div>
        </article>
      </div>
      <PaginationControls v-if="lessonCount > 4" class="mt-4" :page="lessonPage" :count="lessonCount" :page-size="4" :disabled="lessonsLoading || actionBusy || Boolean(pendingAction)" @change="loadLessons" />
    </section>
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-5" :class="isTeacher ? 'teacher-session-layout' : ''">
      <div class="xl:col-span-2 space-y-5">
        <section class="page-card p-6" :class="isTeacher ? 'teacher-session-details' : ''" role="region" aria-labelledby="session-details-title">
          <div class="teacher-session-card-heading mb-5">
            <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="4" width="14" height="18" rx="2" /><path d="M9 4.5V3h6v1.5M9 10h6m-6 4h6m-6 4h4" /></svg></span>
            <h2 id="session-details-title" ref="setupHeading" tabindex="-1" class="font-semibold text-navy">Session Details</h2>
          </div>
          <div v-if="selectedLesson" class="mb-5 rounded-xl border border-gray-200 p-4">
            <p class="font-semibold">Continue {{ selectedLesson.presentation_title }}</p>
            <p class="mt-1 text-sm text-gray-500">Teaching will resume on slide {{ selectedLesson.last_slide_number }} of {{ selectedLesson.total_slides }}. Review the camera selection below.</p>
            <button type="button" class="btn-secondary mt-3" :disabled="actionBusy || Boolean(pendingAction)" @click="clearSavedSelection">Choose a different lesson</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div role="region" aria-labelledby="session-subject-title">
              <label class="block text-sm font-medium text-gray-600">
                <span id="session-subject-title">Subject and classroom</span>
                <span class="teacher-session-subject-search">
                  <svg v-if="isTeacher" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m16 16 4 4" /></svg>
                  <input v-model="subjectSearch" type="search" :disabled="Boolean(selectedLesson) || actionBusy || Boolean(pendingAction)" placeholder="Search subjects…" class="mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-navy">
                </span>
                <select v-model="selectedSubjectId" :disabled="Boolean(selectedLesson) || actionBusy || Boolean(pendingAction)" class="mt-2 w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-navy">
                  <option value="">Select a subject</option>
                  <option v-for="subject in options.subjects" :key="subject.id" :value="subject.id">
                    {{ subject.code }} — {{ subject.name }} ({{ subject.classroom.room_code }})
                  </option>
                </select>
              </label>
              <PaginationControls v-if="subjectCount > subjectPageSize" class="mt-3 rounded-xl border border-gray-100" :page="subjectPage" :count="subjectCount" :page-size="subjectPageSize" :disabled="subjectPageLoading || actionBusy" @change="changeSubjectPage" />
            </div>
            <label class="block text-sm font-medium text-gray-600">
              Presentation
              <select v-model="selectedPresentationId" :disabled="Boolean(selectedLesson) || actionBusy || Boolean(pendingAction)" class="mt-1.5 w-full rounded-xl border border-gray-200 bg-white px-4 py-3 text-navy">
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

          <div class="mt-5 rounded-xl border border-gray-200 p-4" :class="isTeacher ? 'teacher-session-cameras' : ''">
            <div class="flex items-center justify-between gap-3">
              <div class="teacher-session-camera-heading">
                <span v-if="isTeacher" class="teacher-session-small-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><rect x="3" y="6" width="13" height="12" rx="2" /><path d="m16 10 5-3v10l-5-3" /></svg></span>
                <div>
                <h3 class="text-sm font-semibold text-navy">Session cameras</h3>
                <p class="text-xs text-gray-400 mt-1">Connections are checked automatically before preparation. Camera video is never shown.</p>
                </div>
              </div>
              <span v-if="availableCameras.length" class="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700">{{ selectedCameraIds.length ? `${selectedCameraIds.length}/${availableCameras.length} selected` : 'No cameras selected' }}</span>
              <span v-else class="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700">No active cameras</span>
            </div>
            <template v-if="availableCameras.length">
              <label class="session-camera-free-option mt-4">
                <input type="checkbox" :checked="selectedCameraIds.length === 0" @change="toggleCameraFreeMode">
                <span>
                  <strong>Prepare and start without cameras for now</strong>
                  <small>Use the presentation and session controls without camera analytics.</small>
                </span>
              </label>
              <div class="mt-4 flex items-center justify-end gap-2">
                <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50" @click="selectAllCameras">Select all</button>
                <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-semibold text-gray-600 hover:bg-gray-50" @click="clearCameraSelection">Clear</button>
              </div>
              <div class="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <label v-for="camera in availableCameras" :key="camera.id" class="flex items-center gap-3 rounded-lg border p-3 text-sm" :class="selectedCameraIds.includes(camera.id) ? 'border-indigo-300 bg-indigo-50/50 text-navy' : 'border-gray-200 text-gray-600'">
                  <input v-model="selectedCameraIds" type="checkbox" :value="camera.id" class="accent-brand">
                  <span class="min-w-0 flex-1"><strong class="block truncate font-semibold">{{ camera.name }}</strong><small class="block text-gray-400">{{ camera.position_label || camera.position }}</small></span>
                  <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="cameraReadinessClass(cameraAvailability[camera.id])">{{ cameraReadinessLabel(cameraAvailability[camera.id]) }}</span>
                </label>
              </div>
              <p v-if="selectedCameraIds.length && !selectedCamerasAvailable" class="mt-3 text-xs text-amber-700">Prepare Session unlocks when every selected camera is Available. Add a missing IP address in Classes, or choose to start without cameras for now.</p>
            </template>
            <div v-else-if="selectedSubject" class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              This classroom has no active cameras. You can still start the session<span v-if="options.simulator_enabled"> and use the development simulator</span>.
            </div>
            <p v-else class="mt-4 text-sm text-gray-400">Select a subject to load its classroom cameras.</p>
          </div>

          <button type="button" class="btn-primary mt-5 w-full justify-center disabled:cursor-not-allowed disabled:opacity-50 disabled:shadow-none sm:w-auto" :disabled="!canPrepare" @click="prepareSession">
            <svg class="h-5 w-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m7 4 13 8-13 8V4Z" /></svg>
            {{ actionBusy ? 'Preparing…' : selectedLesson ? 'Prepare Continuation' : 'Prepare Session' }}
          </button>
        </section>

        <section class="page-card p-6" :class="isTeacher ? 'teacher-session-preview' : ''">
          <div class="teacher-session-card-heading">
            <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8m-4-4v4" /></svg></span>
            <h2 class="font-semibold text-navy mb-1">Presentation Preview</h2>
          </div>
          <p class="text-xs text-gray-400 mb-4">PDF files display directly. PPTX files display through their converted PDF.</p>
          <iframe
            v-if="selectedPresentation?.preview_url"
            :src="selectedPresentation.preview_url"
            :title="selectedPresentation.title"
            class="w-full rounded-xl border border-gray-200 bg-gray-50"
            style="height: 480px"
          ></iframe>
          <div v-else class="rounded-xl border border-dashed border-gray-200 py-20 text-center text-sm text-gray-400" :class="isTeacher ? 'teacher-session-preview-empty' : ''">
            <span v-if="isTeacher" class="teacher-session-document-art" aria-hidden="true"><svg viewBox="0 0 120 120" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M29 14h43l20 20v68H29a7 7 0 0 1-7-7V21a7 7 0 0 1 7-7Z" stroke-width="3" /><path d="M72 14v20h20M36 48h28M36 57h20" stroke-width="3" /><circle cx="64" cy="78" r="20" stroke-width="3" /><path d="m58 67 15 11-15 11V67Z" fill="currentColor" stroke="none" /></svg></span>
            <p>Select a ready presentation to preview it.</p>
          </div>
        </section>
      </div>

      <aside class="space-y-5">
        <div class="session-support-tabs page-card" role="tablist" aria-label="Session support panels">
          <button id="presentations-tab" type="button" role="tab" :aria-selected="supportPanel === 'presentations'" aria-controls="presentations-panel" :class="{ active: supportPanel === 'presentations' }" @click="supportPanel = 'presentations'">Presentations</button>
          <button id="history-tab" type="button" role="tab" :aria-selected="supportPanel === 'history'" aria-controls="history-panel" :class="{ active: supportPanel === 'history' }" @click="supportPanel = 'history'">Class history</button>
        </div>
        <div v-if="supportPanel === 'presentations'" id="presentations-panel" class="space-y-5" role="tabpanel" aria-labelledby="presentations-tab">
        <section class="page-card p-5" :class="isTeacher ? 'teacher-session-upload' : ''">
          <div class="teacher-session-card-heading">
            <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M6 18H5a3 3 0 0 1-.4-6A7.5 7.5 0 0 1 19 10.5a3.8 3.8 0 0 1 0 7.5h-1M12 21V10m-4 4 4-4 4 4" /></svg></span>
            <h2 class="font-semibold text-navy">Upload Presentation</h2>
          </div>
          <p class="text-xs text-gray-400 mt-1 mb-4">PDF or PPTX, up to 50 MB. The original file is preserved.</p>
          <label class="block text-sm font-medium text-gray-600">
            Title
            <input v-model="uploadTitle" type="text" maxlength="150" class="mt-1.5 w-full rounded-xl border border-gray-200 px-4 py-2.5" placeholder="Lecture title">
          </label>
          <label class="block text-sm font-medium text-gray-600 mt-3">
            File
            <input ref="fileInput" type="file" accept=".pdf,.pptx,application/pdf,application/vnd.openxmlformats-officedocument.presentationml.presentation" class="mt-1.5 block w-full text-sm text-gray-500" @change="chooseFile">
          </label>
          <button type="button" class="btn-secondary w-full justify-center mt-4" :disabled="actionBusy || !uploadFile || !uploadTitle.trim()" @click="submitUpload">
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
        </section>

        <section class="page-card p-5" :class="isTeacher ? 'teacher-session-library' : ''">
          <div role="region" aria-labelledby="presentation-library-title">
            <div class="flex items-center justify-between gap-3">
              <div class="teacher-session-card-heading">
                <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 9 5-9 5-9-5 9-5Zm-9 9 9 5 9-5m-18 5 9 5 9-5" /></svg></span>
                <h3 id="presentation-library-title" class="text-xs font-semibold uppercase tracking-wide text-gray-400">Presentation Library</h3>
              </div>
              <select v-model="presentationLifecycle" aria-label="Presentation records" class="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600">
                <option value="active">Active</option>
                <option value="archived">Archived</option>
                <option value="all">All</option>
              </select>
            </div>
            <div v-if="!presentationLibrary.length" class="py-6 text-center text-xs text-gray-400" :class="isTeacher ? 'teacher-session-list-empty' : ''">
              <span v-if="isTeacher" class="teacher-session-document-art" aria-hidden="true"><svg viewBox="0 0 120 120" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"><path d="M29 14h43l20 20v68H29a7 7 0 0 1-7-7V21a7 7 0 0 1 7-7Z" stroke-width="3" /><path d="M72 14v20h20M36 48h28M36 57h20" stroke-width="3" /><circle cx="64" cy="78" r="20" stroke-width="3" /><path d="m58 67 15 11-15 11V67Z" fill="currentColor" stroke="none" /></svg></span>
              <p>No presentations match this filter.</p>
            </div>
            <div class="mt-3 max-h-64 space-y-2 overflow-y-auto">
              <div v-for="presentation in presentationLibrary" :key="presentation.id" class="rounded-lg border border-gray-100 p-3">
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <p class="truncate text-sm font-medium text-navy">{{ presentation.title }}</p>
                    <a :href="presentation.source_url" target="_blank" rel="noopener" class="text-xs text-brand hover:underline">Open original {{ presentation.file_type.toUpperCase() }}</a>
                  </div>
                  <span class="rounded-full px-2 py-0.5 text-xs font-semibold" :class="presentation.processing_status === 'ready' ? 'bg-emerald-50 text-emerald-600' : presentation.processing_status === 'failed' ? 'bg-red-50 text-red-600' : 'bg-amber-50 text-amber-700'">
                    {{ presentation.is_archived ? 'archived' : presentation.processing_status }}
                  </span>
                </div>
                <p v-if="presentation.processing_status === 'ready'" class="mt-1 text-xs text-gray-400">{{ presentation.total_slides }} generated slides</p>
                <p v-else-if="presentation.processing_error" class="mt-2 text-xs leading-5 text-red-600">{{ presentation.processing_error }}</p>
                <p v-if="presentation.in_use" class="mt-2 text-xs text-gray-400">Used by a recorded session · permanent deletion protected</p>
                <div class="mt-3 flex flex-wrap items-center gap-3 text-xs font-semibold">
                  <a v-if="presentation.preview_url" :href="presentation.preview_url" target="_blank" rel="noopener" class="text-brand hover:underline">Preview</a>
                  <button v-if="presentation.processing_status === 'failed' && !presentation.is_archived" type="button" class="text-brand hover:underline disabled:opacity-50" :disabled="presentationBusyId === presentation.id" @click="retryPresentation(presentation)">
                    {{ presentationBusyId === presentation.id ? 'Retrying…' : 'Retry conversion' }}
                  </button>
                  <button v-if="!presentation.is_archived" type="button" :class="presentation.in_use ? 'text-amber-700' : 'text-red-600'" class="hover:underline disabled:cursor-not-allowed disabled:opacity-40" :disabled="presentationBusyId === presentation.id" @click="deletePresentation(presentation)">
                    {{ presentation.in_use ? 'Archive' : 'Delete permanently' }}
                  </button>
                  <button v-else type="button" class="text-emerald-700 hover:underline disabled:opacity-40" :disabled="presentationBusyId === presentation.id" @click="restoreArchivedPresentation(presentation)">
                    Restore
                  </button>
                </div>
              </div>
            </div>
            <PaginationControls v-if="presentationCount > pageSize" :page="presentationPage" :count="presentationCount" :page-size="pageSize" :disabled="Boolean(presentationBusyId)" @change="changePresentationPage" />
          </div>
        </section>

        </div>

        <section v-if="supportPanel === 'history'" id="history-panel" class="page-card p-5" :class="isTeacher ? 'teacher-session-recent' : ''" role="tabpanel" aria-labelledby="history-tab recent-sessions-title">
          <div class="mb-3 flex items-center justify-between gap-3">
            <div class="teacher-session-card-heading">
              <span v-if="isTeacher" class="teacher-panel-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></svg></span>
              <h2 id="recent-sessions-title" ref="historyHeading" tabindex="-1" class="font-semibold text-navy">{{ route.query.lesson ? 'Lesson Class History' : 'Recent Sessions' }}</h2>
            </div>
            <select v-model="sessionLifecycle" aria-label="Session records" class="rounded-lg border border-gray-200 bg-white px-2 py-1 text-xs text-gray-600">
              <option value="active">Active</option>
              <option value="archived">Archived</option>
              <option value="all">All</option>
            </select>
          </div>
          <div v-if="route.query.lesson" class="mb-4 text-xs text-gray-500">
            <p>Lesson #{{ route.query.lesson }} · Meetings in teaching order. Each has its own timing and results.</p>
            <button type="button" class="btn-secondary mt-2" @click="showLessonHistory(null)">Show recent classes</button>
          </div>
          <div v-if="!sessions.length" class="py-6 text-center text-sm text-gray-400" :class="isTeacher ? 'teacher-session-list-empty' : ''">
            <img v-if="isTeacher" src="/illustrations/teacher-sessions-empty.png" width="1536" height="1024" alt="" aria-hidden="true">
            <p>{{ route.query.lesson ? 'No class meetings match this filter.' : 'No sessions recorded yet.' }}</p>
          </div>
          <div v-else class="space-y-3">
            <div v-for="session in sessions" :key="session.id" class="rounded-lg border border-gray-100 p-3">
              <div class="flex justify-between gap-3">
                <p class="text-sm font-medium text-navy">{{ session.subject_code }}</p>
                <span class="text-xs font-semibold" :class="session.is_archived ? 'text-gray-500' : session.status === 'completed' ? 'text-emerald-600' : 'text-brand'">{{ session.is_archived ? 'Archived · ' : '' }}{{ meetingOutcome(session) }}</span>
              </div>
              <p class="text-xs text-gray-400 mt-1">{{ formatDate(session.started_at) }}</p>
              <p class="mt-1 text-xs text-gray-500">Class #{{ session.id }}<template v-if="session.lesson"> · Lesson {{ lessonState(session) }}</template></p>
              <p v-if="session.continued_from" class="mt-1 text-xs text-gray-500">Continued from class #{{ session.continued_from }}</p>
              <div class="mt-3 flex flex-wrap gap-3 text-xs font-semibold">
                <RouterLink class="text-brand underline" :to="{ path: '/analytics', query: { session: session.id } }">View analytics</RouterLink>
                <button v-if="session.lesson && !route.query.lesson" type="button" class="text-brand underline" @click="showLessonHistory(session.lesson.id)">Lesson history</button>
              </div>
              <div v-if="session.status === 'completed'" class="mt-2 text-right text-xs font-semibold">
                <button v-if="!session.is_archived" type="button" class="text-amber-700 hover:underline" @click="archiveSession(session)">Archive</button>
                <button v-else type="button" class="text-emerald-700 hover:underline" @click="restoreArchivedSession(session)">Restore</button>
              </div>
            </div>
          </div>
          <PaginationControls v-if="sessionCount > sessionPageSize" class="-mx-5 -mb-5 mt-5" :page="sessionPage" :count="sessionCount" :page-size="sessionPageSize" :disabled="loading || sessionPageLoading || actionBusy" @change="changeSessionPage" />
        </section>
      </aside>
    </div>
    </template>

    <div v-else class="space-y-5">
      <div class="page-card px-5 py-4 flex flex-wrap items-center justify-between gap-4">
        <div>
          <p class="text-xs text-gray-400">{{ monitoredSession.subject_code }} · {{ monitoredSession.classroom }}</p>
          <h2 class="font-semibold text-navy">{{ monitoredSession.presentation_title }}</h2>
          <p v-if="preparedSession" class="mt-1 text-xs text-amber-700">Review mode · session timing and analytics have not started</p>
        </div>
        <div class="flex items-center gap-4" :class="{ 'session-ready-actions': canStartPrepared }">
          <span class="font-mono text-lg font-semibold text-navy">{{ elapsedDisplay }}</span>
          <button v-if="preparedSession" type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm font-semibold text-gray-600 disabled:opacity-50" :disabled="actionBusy || Boolean(pendingAction)" @click="cancelPreparation">
            Change setup
          </button>
          <button v-if="preparedSession" type="button" class="btn-primary" :disabled="!canStartPrepared" @click="beginPreparedSession">
            {{ countdownSeconds !== null ? 'Starting…' : 'Start Session' }}
          </button>
          <button v-else type="button" class="btn-secondary" :disabled="actionBusy || Boolean(pendingAction)" @click="openEndDialog()">
            End Class
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
            <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40" :disabled="currentSlideIndex === 0 || actionBusy || Boolean(pendingAction)" @click="changeSlide(currentSlideIndex - 1)">Previous</button>
            <span class="text-sm text-gray-500">Slide {{ currentSlideIndex + 1 }} of {{ slides.length }}</span>
            <button type="button" class="rounded-lg border border-gray-200 px-4 py-2 text-sm disabled:opacity-40" :disabled="currentSlideIndex >= slides.length - 1 || actionBusy || Boolean(pendingAction)" @click="changeSlide(currentSlideIndex + 1)">Next</button>
          </div>
        </section>

        <aside class="space-y-5">
          <section class="page-card p-5">
            <div class="flex items-center justify-between gap-2">
              <h3 class="text-sm font-semibold text-navy">Camera & Worker Health</h3>
              <span v-if="monitoredSession.cameras.length" class="rounded-full bg-blue-50 px-2 py-1 text-xs font-semibold text-blue-700">{{ cameraHealthStatus === 'ready' ? 'Live status' : cameraHealthStatus === 'unavailable' ? 'Status unavailable' : 'Loading status' }}</span>
              <span v-else class="rounded-full bg-violet-50 px-2 py-1 text-xs font-semibold text-violet-700">{{ options.simulator_enabled ? 'Simulator only' : 'No cameras' }}</span>
            </div>
            <p class="mt-3 text-xs leading-5 text-gray-500">Each selected camera runs independently and contributes official analytics.</p>
            <div v-if="cameraHealthStatus === 'unavailable'" class="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">
              Worker health is temporarily unavailable. Slides and session controls are unaffected.
            </div>
            <div v-if="monitoredSession.cameras.length" class="space-y-2 mt-4">
              <div v-for="camera in activeCameras" :key="camera.id" class="rounded-lg border border-gray-100 p-3">
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0"><p class="truncate text-sm font-medium text-navy">{{ camera.name }}</p><p class="text-xs text-gray-400">{{ camera.position_label || camera.position }} position</p></div>
                  <span class="rounded-full px-2 py-0.5 text-[11px] font-semibold" :class="cameraStateClass(camera.state)">{{ camera.state === 'starting' ? 'Preparing' : camera.state_label }}</span>
                </div>
                <div class="mt-2 flex flex-wrap gap-1.5">
                  <span v-if="camera.source_type" class="rounded-full bg-violet-50 px-2 py-0.5 text-[11px] font-semibold text-violet-700">{{ camera.source_label }}</span>
                  <span class="rounded-full bg-indigo-50 px-2 py-0.5 text-[11px] font-semibold text-indigo-700">Official analytics</span>
                </div>
                <p class="mt-2 text-xs text-gray-500">{{ cameraStateMessage(camera, Boolean(preparedSession)) }}</p>
                <p class="mt-1 text-[11px] text-gray-400">{{ formatHeartbeat(camera.last_heartbeat) }}</p>
                <p v-if="camera.state === 'online'" class="mt-2 text-xs text-gray-500">{{ camera.confirmed_students }} confirmed · {{ camera.unclassified_students }} unclassified · {{ camera.analysis_rate }} fps</p>
              </div>
            </div>
            <div v-else class="mt-4 rounded-lg border border-violet-200 bg-violet-50 p-3"><p class="text-xs font-semibold text-violet-700">No cameras linked</p><p class="mt-1 text-xs leading-5 text-violet-600">{{ options.simulator_enabled ? 'This session can continue with simulated engagement data.' : 'You can start and present slides, but camera analytics will not be recorded.' }}</p></div>
            <div v-if="preparedHasCameras && !preparedCamerasReady" class="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3 text-xs text-amber-800">Start Session unlocks when all selected cameras become Online.</div>
            <div v-else-if="preparedHasCameras" class="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-xs text-emerald-800">All selected cameras are Online. You can start the session.</div>
          </section>

          <section v-if="activeSession" class="page-card p-5">
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
                <div class="mb-1 flex justify-between text-xs"><span class="text-gray-600">{{ category.label }}</span><span class="font-semibold" :style="{ color: category.textColor }">{{ latestEngagement.distribution[category.key] }}%</span></div>
                <div class="h-1.5 overflow-hidden rounded-full bg-gray-100"><div class="h-full rounded-full" :style="{ width: `${latestEngagement.distribution[category.key]}%`, background: category.color }"></div></div>
              </div>
              <p class="text-xs text-gray-400">{{ latestEngagement.total_detected }} detected · {{ latestEngagement.unclassified_count }} unclassified · Slide {{ latestEngagement.slide_number }}</p>
            </div>
            <p v-else class="mt-3 text-xs leading-5 text-gray-500">Waiting for the first aggregated monitoring window.</p>
            <div v-if="options.simulator_enabled" class="mt-4 border-t border-gray-100 pt-4">
              <template v-if="simulatorAvailable">
                <button v-if="!simulationRunning" type="button" class="btn-secondary w-full justify-center" @click="startSimulation">Start Simulation</button>
                <button v-else type="button" class="w-full rounded-lg border border-red-200 px-4 py-2 text-sm font-semibold text-red-600 hover:bg-red-50" @click="stopSimulation">Stop Simulation</button>
                <p class="mt-2 text-xs text-gray-400">Development only · one result every two seconds</p>
              </template>
              <p v-else class="text-xs leading-5 text-gray-500">Simulation is unavailable because this session has assigned camera sources.</p>
            </div>
          </section>
        </aside>
      </div>
    </div>

    <SessionEndDialog
      :open="endDialogOpen"
      :can-save="Boolean(activeSession?.lesson)"
      :saved-lesson="Boolean(finishingSavedLesson)"
      :title="finishingSavedLesson?.presentation_title || activeSession?.presentation_title || ''"
      :progress="finishingSavedLesson ? `Saved at slide ${finishingSavedLesson.last_slide_number} of ${finishingSavedLesson.total_slides}` : `Current slide ${currentSlideIndex + 1} of ${slides.length}`"
      :busy-action="endAction"
      :pending="Boolean(pendingAction)"
      :error="error"
      @close="closeEndDialog"
      @choose="finishSession"
      @recover="checkPendingAction"
    />
    <AppConfirmDialog
      :open="Boolean(confirmation)"
      v-bind="confirmation || {}"
      @confirm="acceptConfirmation"
      @cancel="cancelConfirmation"
    />
    <AppDialog
      :open="countdownSeconds !== null"
      labelledby="session-countdown-title"
      describedby="session-countdown-description"
      panel-class="session-countdown-panel"
      initial-focus="[data-countdown-cancel]"
      @close="cancelSessionCountdown"
    >
      <p class="session-countdown-eyebrow">Get Ready</p>
      <h2 id="session-countdown-title">Your classroom session is about to begin</h2>
      <p class="session-countdown-value" aria-live="assertive">{{ countdownSeconds }}</p>
      <p id="session-countdown-description" class="session-countdown-description">Session timing and analytics will start after the countdown.</p>
      <button type="button" class="session-countdown-cancel" data-countdown-cancel @click="cancelSessionCountdown">Cancel session start</button>
    </AppDialog>
  </AppLayout>
</template>
