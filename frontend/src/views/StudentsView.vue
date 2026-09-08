<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import { currentUser } from '../auth'
import {
  createCamera,
  createClassroom,
  createQuickSetup,
  createSubject,
  deleteCamera,
  deleteClassroom,
  deleteSubject,
  fetchCameras,
  fetchClassManagementOptions,
  fetchClassrooms,
  fetchSubjects,
  updateClassroom,
  updateCamera,
  updateSubject,
} from '../classManagement'

const route = useRoute()

const classrooms = ref([])
const subjects = ref([])
const cameras = ref([])
const options = ref({ organizations: [], teachers: [], camera_positions: [], camera_statuses: [] })
const loading = ref(true)
const saving = ref(false)
const pageError = ref('')
const formError = ref('')
const fieldErrors = ref({})
const search = ref('')
const modal = ref(null)
const editingId = ref(null)

const classroomForm = reactive({ organization: '', room_code: '', building: '', capacity: '' })
const subjectForm = reactive({ subject_code: '', subject_name: '', classroom: '', teacher: '' })
const cameraForm = reactive({ classroom: '', camera_name: '', position: 'front', status: 'active' })
const quickForm = reactive({
  mode: 'new',
  classroom_id: '',
  organization: '',
  room_code: '',
  building: '',
  capacity: '',
  cameras: [],
  include_subject: true,
  subject_code: '',
  subject_name: '',
  teacher: '',
})

const canManage = computed(() => ['system_admin', 'org_admin'].includes(currentUser.value?.role))
const isSystemAdmin = computed(() => currentUser.value?.role === 'system_admin')
const isEditing = computed(() => editingId.value !== null)
const totalCapacity = computed(() => classrooms.value.reduce((sum, item) => sum + (item.capacity || 0), 0))
const cameraCount = computed(() => cameras.value.length)
const filteredSubjects = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return subjects.value
  return subjects.value.filter((subject) => [
    subject.subject_code,
    subject.subject_name,
    subject.teacher_name,
    subject.classroom_room_code,
    subject.organization_name,
  ].join(' ').toLowerCase().includes(term))
})
const filteredClassrooms = computed(() => {
  const term = search.value.trim().toLowerCase()
  if (!term) return classrooms.value
  return classrooms.value.filter((classroom) => [
    classroom.room_code,
    classroom.building,
    classroom.organization_name,
  ].join(' ').toLowerCase().includes(term))
})
const selectedClassroom = computed(() => classrooms.value.find(
  (item) => item.id === Number(subjectForm.classroom),
))
const availableTeachers = computed(() => {
  const organization = selectedClassroom.value?.organization
  return organization
    ? options.value.teachers.filter((teacher) => teacher.organization === organization)
    : []
})
const quickClassroom = computed(() => classrooms.value.find(
  (item) => item.id === Number(quickForm.classroom_id),
))
const quickOrganizationId = computed(() => (
  quickForm.mode === 'existing'
    ? quickClassroom.value?.organization
    : Number(quickForm.organization)
))
const quickTeachers = computed(() => options.value.teachers.filter(
  (teacher) => teacher.organization === quickOrganizationId.value,
))
const quickSelectedCameras = computed(() => quickForm.cameras.filter((camera) => camera.selected))

watch(() => subjectForm.classroom, () => {
  if (!availableTeachers.value.some((teacher) => teacher.id === Number(subjectForm.teacher))) {
    subjectForm.teacher = ''
  }
})
watch(() => route.query.search, (value) => {
  search.value = typeof value === 'string' ? value : ''
}, { immediate: true })
watch(() => [quickForm.mode, quickForm.classroom_id], resetQuickCameras)
watch(quickOrganizationId, () => {
  if (!quickTeachers.value.some((teacher) => teacher.id === Number(quickForm.teacher))) {
    quickForm.teacher = ''
  }
})

function firstError(field) {
  const value = fieldErrors.value[field]
  return Array.isArray(value) ? value[0] : value
}

function nestedError(...path) {
  let value = fieldErrors.value
  for (const part of path) value = value?.[part]
  return Array.isArray(value) ? value[0] : (typeof value === 'string' ? value : '')
}

function resetErrors() {
  formError.value = ''
  fieldErrors.value = {}
}

function openClassroomCreate() {
  editingId.value = null
  Object.assign(classroomForm, {
    organization: isSystemAdmin.value ? '' : options.value.organizations[0]?.id || '',
    room_code: '',
    building: '',
    capacity: '',
  })
  resetErrors()
  modal.value = 'classroom'
}

function quickRoomCode() {
  return quickForm.mode === 'existing'
    ? quickClassroom.value?.room_code || 'Classroom'
    : quickForm.room_code.trim() || 'Classroom'
}

function generatedCameraName(camera) {
  return `${quickRoomCode()} ${camera.label} Camera`
}

function quickCameraError(camera, field) {
  const index = quickSelectedCameras.value.indexOf(camera)
  return index < 0 ? '' : nestedError('cameras', String(index), field)
}

function resetQuickCameras() {
  const configured = new Set(
    quickForm.mode === 'existing'
      ? cameras.value.filter((camera) => camera.classroom === Number(quickForm.classroom_id)).map((camera) => camera.position)
      : [],
  )
  quickForm.cameras = options.value.camera_positions.map((position) => ({
    position: position.value,
    label: position.label,
    selected: false,
    configured: configured.has(position.value),
    camera_name: '',
  }))
  const firstAvailable = quickForm.cameras.find((camera) => !camera.configured)
  if (firstAvailable) firstAvailable.selected = true
}

function openQuickSetup() {
  Object.assign(quickForm, {
    mode: classrooms.value.length ? 'existing' : 'new',
    classroom_id: classrooms.value[0]?.id || '',
    organization: options.value.organizations[0]?.id || '',
    room_code: '',
    building: '',
    capacity: '',
    include_subject: true,
    subject_code: '',
    subject_name: '',
    teacher: '',
  })
  resetQuickCameras()
  resetErrors()
  editingId.value = null
  modal.value = 'quick'
}

function openClassroomEdit(classroom) {
  editingId.value = classroom.id
  Object.assign(classroomForm, {
    organization: classroom.organization,
    room_code: classroom.room_code,
    building: classroom.building,
    capacity: classroom.capacity ?? '',
  })
  resetErrors()
  modal.value = 'classroom'
}

function openSubjectCreate() {
  editingId.value = null
  Object.assign(subjectForm, {
    subject_code: '',
    subject_name: '',
    classroom: classrooms.value[0]?.id || '',
    teacher: '',
  })
  resetErrors()
  modal.value = 'subject'
}

function openSubjectEdit(subject) {
  editingId.value = subject.id
  Object.assign(subjectForm, {
    subject_code: subject.subject_code,
    subject_name: subject.subject_name,
    classroom: subject.classroom,
    teacher: subject.teacher,
  })
  resetErrors()
  modal.value = 'subject'
}

function openCameraCreate() {
  editingId.value = null
  Object.assign(cameraForm, {
    classroom: classrooms.value[0]?.id || '',
    camera_name: '',
    position: options.value.camera_positions[0]?.value || 'front',
    status: 'active',
  })
  resetErrors()
  modal.value = 'camera'
}

function openCameraEdit(camera) {
  editingId.value = camera.id
  Object.assign(cameraForm, {
    classroom: camera.classroom,
    camera_name: camera.camera_name,
    position: camera.position,
    status: camera.status,
  })
  resetErrors()
  modal.value = 'camera'
}

function closeModal() {
  if (!saving.value) modal.value = null
}

async function loadPage() {
  loading.value = true
  pageError.value = ''
  try {
    const [classroomData, subjectData, cameraData, optionData] = await Promise.all([
      fetchClassrooms(),
      fetchSubjects(),
      fetchCameras(),
      fetchClassManagementOptions(),
    ])
    classrooms.value = classroomData
    subjects.value = subjectData
    cameras.value = cameraData
    options.value = optionData
  } catch (error) {
    pageError.value = error.message
  } finally {
    loading.value = false
  }
}

async function saveClassroom() {
  saving.value = true
  resetErrors()
  const payload = {
    ...classroomForm,
    organization: Number(classroomForm.organization),
    capacity: classroomForm.capacity === '' ? null : Number(classroomForm.capacity),
  }
  try {
    const saved = isEditing.value
      ? await updateClassroom(editingId.value, payload)
      : await createClassroom(payload)
    const index = classrooms.value.findIndex((item) => item.id === saved.id)
    if (index === -1) classrooms.value.push(saved)
    else classrooms.value[index] = saved
    classrooms.value.sort((a, b) => a.room_code.localeCompare(b.room_code))
    modal.value = null
  } catch (error) {
    formError.value = error.message
    fieldErrors.value = error.fields || {}
  } finally {
    saving.value = false
  }
}

async function saveSubject() {
  saving.value = true
  resetErrors()
  try {
    const payload = {
      ...subjectForm,
      classroom: Number(subjectForm.classroom),
      teacher: Number(subjectForm.teacher),
    }
    const saved = isEditing.value
      ? await updateSubject(editingId.value, payload)
      : await createSubject(payload)
    const index = subjects.value.findIndex((item) => item.id === saved.id)
    if (index === -1) subjects.value.push(saved)
    else subjects.value[index] = saved
    subjects.value.sort((a, b) => a.subject_code.localeCompare(b.subject_code))
    await refreshClassroomCounts()
    modal.value = null
  } catch (error) {
    formError.value = error.message
    fieldErrors.value = error.fields || {}
  } finally {
    saving.value = false
  }
}

async function saveCamera() {
  saving.value = true
  resetErrors()
  try {
    const payload = { ...cameraForm, classroom: Number(cameraForm.classroom) }
    const saved = isEditing.value
      ? await updateCamera(editingId.value, payload)
      : await createCamera(payload)
    const index = cameras.value.findIndex((item) => item.id === saved.id)
    if (index === -1) cameras.value.push(saved)
    else cameras.value[index] = saved
    cameras.value.sort((a, b) => (
      a.classroom_room_code.localeCompare(b.classroom_room_code)
      || a.position.localeCompare(b.position)
    ))
    await refreshClassroomCounts()
    modal.value = null
  } catch (error) {
    formError.value = error.message
    fieldErrors.value = error.fields || {}
  } finally {
    saving.value = false
  }
}

async function saveQuickSetup() {
  saving.value = true
  resetErrors()
  const selectedCameras = quickSelectedCameras.value.map((camera) => ({
    position: camera.position,
    camera_name: camera.camera_name.trim() || generatedCameraName(camera),
  }))
  const payload = {
    cameras: selectedCameras,
    subject: quickForm.include_subject ? {
      subject_code: quickForm.subject_code,
      subject_name: quickForm.subject_name,
      teacher: Number(quickForm.teacher),
    } : null,
  }
  if (quickForm.mode === 'existing') {
    payload.classroom_id = Number(quickForm.classroom_id)
  } else {
    payload.classroom = {
      organization: Number(quickForm.organization),
      room_code: quickForm.room_code,
      building: quickForm.building,
      capacity: quickForm.capacity === '' ? null : Number(quickForm.capacity),
    }
  }

  try {
    await createQuickSetup(payload)
    modal.value = null
    await loadPage()
  } catch (error) {
    formError.value = error.message
    fieldErrors.value = error.fields || {}
  } finally {
    saving.value = false
  }
}

async function refreshClassroomCounts() {
  classrooms.value = await fetchClassrooms()
}

async function removeClassroom(classroom) {
  if (!window.confirm(`Delete classroom ${classroom.room_code}?`)) return
  pageError.value = ''
  try {
    await deleteClassroom(classroom.id)
    classrooms.value = classrooms.value.filter((item) => item.id !== classroom.id)
  } catch (error) {
    pageError.value = error.message
  }
}

async function removeSubject(subject) {
  if (!window.confirm(`Delete subject ${subject.subject_code}?`)) return
  pageError.value = ''
  try {
    await deleteSubject(subject.id)
    subjects.value = subjects.value.filter((item) => item.id !== subject.id)
    await refreshClassroomCounts()
  } catch (error) {
    pageError.value = error.message
  }
}

async function removeCamera(camera) {
  if (!window.confirm(`Delete camera ${camera.camera_name}?`)) return
  pageError.value = ''
  try {
    await deleteCamera(camera.id)
    cameras.value = cameras.value.filter((item) => item.id !== camera.id)
    await refreshClassroomCounts()
  } catch (error) {
    pageError.value = error.message
  }
}

onMounted(loadPage)
</script>

<template>
  <AppLayout page-title="Classes">
    <div class="max-w-7xl mx-auto space-y-6">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Classes</h1>
          <p class="text-sm text-gray-500 mt-1">Real classroom and subject records from TAGAD.</p>
        </div>
        <div v-if="canManage" class="flex flex-wrap gap-2">
          <button type="button" class="btn-primary justify-center" @click="openQuickSetup">Quick Setup</button>
          <button type="button" class="btn-navy justify-center" @click="openClassroomCreate">Add Classroom</button>
          <button type="button" class="rounded-xl border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50" :disabled="!classrooms.length" @click="openSubjectCreate">Add Subject</button>
          <button type="button" class="btn-teal justify-center" :disabled="!classrooms.length" @click="openCameraCreate">Add Camera</button>
        </div>
      </div>

      <div v-if="pageError" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{{ pageError }}</div>

      <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div class="stat-card"><p class="text-xs text-gray-400">Accessible records</p><p class="text-2xl font-bold text-navy mt-1">{{ classrooms.length }}</p><p class="text-sm text-gray-600">Classrooms</p></div>
        <div class="stat-card"><p class="text-xs text-gray-400">Accessible records</p><p class="text-2xl font-bold text-navy mt-1">{{ subjects.length }}</p><p class="text-sm text-gray-600">Subjects</p></div>
        <div class="stat-card"><p class="text-xs text-gray-400">Combined room capacity</p><p class="text-2xl font-bold text-navy mt-1">{{ totalCapacity }}</p><p class="text-sm text-gray-600">Seats</p></div>
        <div class="stat-card"><p class="text-xs text-gray-400">Configuration base</p><p class="text-2xl font-bold text-navy mt-1">{{ cameraCount }}</p><p class="text-sm text-gray-600">Cameras</p></div>
      </div>

      <section class="page-card overflow-hidden">
        <div class="flex flex-col gap-3 border-b border-gray-200 p-5 sm:flex-row sm:items-center sm:justify-between">
          <div><h2 class="font-bold text-gray-900">Subjects</h2><p class="text-xs text-gray-500 mt-1">Teachers see only subjects assigned to them.</p></div>
          <input v-model="search" type="search" placeholder="Search classes and subjects…" class="w-full sm:w-72 rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-indigo-500" />
        </div>
        <div v-if="loading" class="p-10 text-center text-sm text-gray-500">Loading classes…</div>
        <div v-else-if="!filteredSubjects.length" class="p-10 text-center text-sm text-gray-500">No subjects found.</div>
        <div v-else class="grid gap-5 p-5 md:grid-cols-2 xl:grid-cols-3">
          <article v-for="subject in filteredSubjects" :key="subject.id" class="rounded-xl border border-gray-200 p-5">
            <div class="flex items-start justify-between gap-3">
              <div><span class="rounded-md bg-indigo-50 px-2 py-1 text-xs font-bold text-indigo-700">{{ subject.subject_code }}</span><h3 class="mt-3 font-bold text-gray-900">{{ subject.subject_name }}</h3></div>
              <div v-if="canManage" class="flex gap-1">
                <button type="button" class="rounded-lg p-2 text-gray-500 hover:bg-gray-100" title="Edit subject" @click="openSubjectEdit(subject)">✎</button>
                <button type="button" class="rounded-lg p-2 text-red-500 hover:bg-red-50" title="Delete subject" @click="removeSubject(subject)">✕</button>
              </div>
            </div>
            <dl class="mt-4 space-y-2 text-sm">
              <div class="flex justify-between gap-3"><dt class="text-gray-500">Teacher</dt><dd class="font-medium text-gray-800 text-right">{{ subject.teacher_name }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-gray-500">Classroom</dt><dd class="font-medium text-gray-800 text-right">{{ subject.classroom_room_code }}<span v-if="subject.building">, {{ subject.building }}</span></dd></div>
              <div v-if="isSystemAdmin" class="flex justify-between gap-3"><dt class="text-gray-500">Organization</dt><dd class="font-medium text-gray-800 text-right">{{ subject.organization_name }}</dd></div>
              <div class="flex justify-between gap-3"><dt class="text-gray-500">Sessions</dt><dd class="font-medium text-gray-800">{{ subject.session_count }}</dd></div>
            </dl>
            <RouterLink :to="`/session?subject=${subject.id}`" class="btn-primary mt-5 w-full justify-center">Start Session</RouterLink>
          </article>
        </div>
      </section>

      <section class="page-card overflow-hidden">
        <div class="border-b border-gray-200 p-5"><h2 class="font-bold text-gray-900">Classrooms</h2><p class="text-xs text-gray-500 mt-1">Rooms must be empty before they can be deleted.</p></div>
        <div v-if="!loading && !filteredClassrooms.length" class="p-10 text-center text-sm text-gray-500">No classrooms found.</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 text-xs uppercase text-gray-500"><tr><th class="px-5 py-3">Room</th><th class="px-5 py-3">Building</th><th class="px-5 py-3">Capacity</th><th class="px-5 py-3">Subjects</th><th class="px-5 py-3">Cameras</th><th v-if="isSystemAdmin" class="px-5 py-3">Organization</th><th v-if="canManage" class="px-5 py-3 text-right">Actions</th></tr></thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="classroom in filteredClassrooms" :key="classroom.id">
                <td class="px-5 py-4 font-semibold text-gray-900">{{ classroom.room_code }}</td>
                <td class="px-5 py-4 text-gray-600">{{ classroom.building || '—' }}</td>
                <td class="px-5 py-4 text-gray-600">{{ classroom.capacity || '—' }}</td>
                <td class="px-5 py-4 text-gray-600">{{ classroom.subject_count }}</td>
                <td class="px-5 py-4 text-gray-600">{{ classroom.camera_count }}</td>
                <td v-if="isSystemAdmin" class="px-5 py-4 text-gray-600">{{ classroom.organization_name }}</td>
                <td v-if="canManage" class="px-5 py-4"><div class="flex justify-end gap-2"><button type="button" class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold hover:bg-gray-50" @click="openClassroomEdit(classroom)">Edit</button><button type="button" class="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50" @click="removeClassroom(classroom)">Delete</button></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section class="page-card overflow-hidden">
        <div class="border-b border-gray-200 p-5">
          <h2 class="font-bold text-gray-900">Camera Setup</h2>
          <p class="text-xs text-gray-500 mt-1">Configure classroom camera positions now; live CCTV connections will be added later.</p>
        </div>
        <div v-if="!loading && !cameras.length" class="p-10 text-center text-sm text-gray-500">No cameras configured.</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 text-xs uppercase text-gray-500">
              <tr><th class="px-5 py-3">Camera</th><th class="px-5 py-3">Classroom</th><th class="px-5 py-3">Position</th><th class="px-5 py-3">Status</th><th v-if="isSystemAdmin" class="px-5 py-3">Organization</th><th v-if="canManage" class="px-5 py-3 text-right">Actions</th></tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="camera in cameras" :key="camera.id">
                <td class="px-5 py-4 font-semibold text-gray-900">{{ camera.camera_name }}</td>
                <td class="px-5 py-4 text-gray-600">{{ camera.classroom_room_code }}</td>
                <td class="px-5 py-4 text-gray-600">{{ camera.position_label }}</td>
                <td class="px-5 py-4"><span :class="camera.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'" class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold">{{ camera.status_label }}</span></td>
                <td v-if="isSystemAdmin" class="px-5 py-4 text-gray-600">{{ camera.organization_name }}</td>
                <td v-if="canManage" class="px-5 py-4"><div class="flex justify-end gap-2"><button type="button" class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold hover:bg-gray-50" @click="openCameraEdit(camera)">Edit</button><button type="button" class="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50" @click="removeCamera(camera)">Delete</button></div></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-if="modal" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" @click.self="closeModal">
      <form v-if="modal === 'quick'" class="max-h-[90vh] w-full max-w-4xl overflow-y-auto rounded-2xl bg-white shadow-xl" @submit.prevent="saveQuickSetup">
        <div class="sticky top-0 z-10 flex items-center justify-between border-b bg-white px-6 py-4">
          <div><h2 class="text-lg font-bold text-gray-900">Quick Classroom Setup</h2><p class="mt-0.5 text-xs text-gray-500">Configure the room, cameras, and first subject in one save.</p></div>
          <button type="button" class="text-gray-400" aria-label="Close quick setup" @click="closeModal">✕</button>
        </div>

        <div class="space-y-6 p-6">
          <div v-if="formError" class="rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ formError }}</div>

          <section>
            <div class="mb-3 flex items-center gap-3"><span class="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">1</span><h3 class="font-bold text-gray-900">Classroom</h3></div>
            <div v-if="classrooms.length" class="mb-4 inline-flex rounded-xl bg-gray-100 p-1 text-sm">
              <button type="button" class="rounded-lg px-4 py-2 font-semibold" :class="quickForm.mode === 'existing' ? 'bg-white text-indigo-700 shadow-sm' : 'text-gray-500'" @click="quickForm.mode = 'existing'">Use existing</button>
              <button type="button" class="rounded-lg px-4 py-2 font-semibold" :class="quickForm.mode === 'new' ? 'bg-white text-indigo-700 shadow-sm' : 'text-gray-500'" @click="quickForm.mode = 'new'">Create new</button>
            </div>
            <label v-if="quickForm.mode === 'existing'" class="block text-sm font-medium text-gray-700">Classroom *
              <select v-model="quickForm.classroom_id" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5">
                <option value="">Select classroom</option>
                <option v-for="classroom in classrooms" :key="classroom.id" :value="classroom.id">{{ classroom.room_code }}<template v-if="classroom.building"> — {{ classroom.building }}</template> · {{ classroom.camera_count }} camera(s)</option>
              </select>
              <span v-if="nestedError('classroom_id')" class="mt-1 block text-xs text-red-600">{{ nestedError('classroom_id') }}</span>
            </label>
            <div v-else class="grid gap-4 md:grid-cols-2">
              <label v-if="isSystemAdmin" class="md:col-span-2 text-sm font-medium text-gray-700">Organization *
                <select v-model="quickForm.organization" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option value="">Select organization</option><option v-for="organization in options.organizations" :key="organization.id" :value="organization.id">{{ organization.name }}</option></select>
                <span v-if="nestedError('classroom', 'organization')" class="mt-1 block text-xs text-red-600">{{ nestedError('classroom', 'organization') }}</span>
              </label>
              <label class="text-sm font-medium text-gray-700">Room code *<input v-model.trim="quickForm.room_code" required placeholder="e.g. ROOM-204" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="nestedError('classroom', 'room_code')" class="mt-1 block text-xs text-red-600">{{ nestedError('classroom', 'room_code') }}</span></label>
              <label class="text-sm font-medium text-gray-700">Building<input v-model.trim="quickForm.building" placeholder="e.g. Main Building" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"></label>
              <label class="md:col-span-2 text-sm font-medium text-gray-700">Capacity<input v-model="quickForm.capacity" type="number" min="1" placeholder="Optional" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="nestedError('classroom', 'capacity')" class="mt-1 block text-xs text-red-600">{{ nestedError('classroom', 'capacity') }}</span></label>
            </div>
          </section>

          <section class="border-t border-gray-200 pt-6">
            <div class="mb-1 flex items-center gap-3"><span class="flex h-7 w-7 items-center justify-center rounded-full bg-teal-100 text-xs font-bold text-teal-700">2</span><h3 class="font-bold text-gray-900">Cameras</h3></div>
            <p class="mb-4 ml-10 text-xs text-gray-500">Select every position you want to configure. Names are generated automatically unless you enter your own.</p>
            <div class="grid gap-3 md:grid-cols-3">
              <label v-for="camera in quickForm.cameras" :key="camera.position" class="rounded-xl border p-4" :class="camera.configured ? 'border-gray-200 bg-gray-50 opacity-60' : camera.selected ? 'border-teal-400 bg-teal-50/40' : 'border-gray-200'">
                <span class="flex items-center gap-2 text-sm font-semibold text-gray-800"><input v-model="camera.selected" type="checkbox" :disabled="camera.configured" class="h-4 w-4 rounded border-gray-300 text-teal-600">{{ camera.label }}<span v-if="camera.configured" class="ml-auto text-xs font-normal text-gray-500">Configured</span></span>
                <input v-if="camera.selected" v-model.trim="camera.camera_name" :placeholder="generatedCameraName(camera)" maxlength="50" class="mt-3 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm">
                <span v-if="quickCameraError(camera, 'camera_name')" class="mt-1 block text-xs text-red-600">{{ quickCameraError(camera, 'camera_name') }}</span>
                <span v-if="quickCameraError(camera, 'position')" class="mt-1 block text-xs text-red-600">{{ quickCameraError(camera, 'position') }}</span>
              </label>
            </div>
            <span v-if="nestedError('cameras')" class="mt-2 block text-xs text-red-600">{{ nestedError('cameras') }}</span>
          </section>

          <section class="border-t border-gray-200 pt-6">
            <div class="flex items-center justify-between gap-4">
              <div><div class="flex items-center gap-3"><span class="flex h-7 w-7 items-center justify-center rounded-full bg-violet-100 text-xs font-bold text-violet-700">3</span><h3 class="font-bold text-gray-900">First subject</h3></div><p class="ml-10 mt-1 text-xs text-gray-500">Optional—you can add more subjects later.</p></div>
              <label class="flex items-center gap-2 text-sm font-medium text-gray-700"><input v-model="quickForm.include_subject" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-indigo-600">Add subject</label>
            </div>
            <div v-if="quickForm.include_subject" class="mt-4 grid gap-4 md:grid-cols-2">
              <label class="text-sm font-medium text-gray-700">Subject code *<input v-model.trim="quickForm.subject_code" required placeholder="e.g. IT-301" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="nestedError('subject', 'subject_code')" class="mt-1 block text-xs text-red-600">{{ nestedError('subject', 'subject_code') }}</span></label>
              <label class="text-sm font-medium text-gray-700">Subject name *<input v-model.trim="quickForm.subject_name" required placeholder="e.g. Data Structures" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="nestedError('subject', 'subject_name')" class="mt-1 block text-xs text-red-600">{{ nestedError('subject', 'subject_name') }}</span></label>
              <label class="md:col-span-2 text-sm font-medium text-gray-700">Teacher *
                <select v-model="quickForm.teacher" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option value="">Select teacher</option><option v-for="teacher in quickTeachers" :key="teacher.id" :value="teacher.id">{{ teacher.name }}</option></select>
                <span v-if="!quickTeachers.length" class="mt-1 block text-xs text-amber-600">No active teacher belongs to this organization. Turn off “Add subject” or create a teacher first.</span>
                <span v-if="nestedError('subject', 'teacher')" class="mt-1 block text-xs text-red-600">{{ nestedError('subject', 'teacher') }}</span>
              </label>
            </div>
          </section>
        </div>

        <div class="sticky bottom-0 flex items-center justify-between gap-3 border-t bg-white px-6 py-4">
          <p class="text-xs text-gray-500">{{ quickSelectedCameras.length }} camera(s) selected<span v-if="quickForm.include_subject"> · 1 subject</span></p>
          <div class="flex gap-3"><button type="button" class="rounded-xl border px-5 py-2.5 text-sm font-semibold" @click="closeModal">Cancel</button><button class="btn-primary" :disabled="saving || !quickSelectedCameras.length">{{ saving ? 'Saving everything…' : 'Complete Setup' }}</button></div>
        </div>
      </form>

      <form v-else-if="modal === 'classroom'" class="w-full max-w-xl rounded-2xl bg-white shadow-xl" @submit.prevent="saveClassroom">
        <div class="flex items-center justify-between border-b px-6 py-4"><h2 class="text-lg font-bold">{{ isEditing ? 'Edit Classroom' : 'Add Classroom' }}</h2><button type="button" class="text-gray-400" @click="closeModal">✕</button></div>
        <div class="grid gap-4 p-6 sm:grid-cols-2">
          <div v-if="formError" class="sm:col-span-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ formError }}</div>
          <label v-if="isSystemAdmin" class="sm:col-span-2 text-sm font-medium text-gray-700">Organization *<select v-model="classroomForm.organization" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option value="">Select organization</option><option v-for="organization in options.organizations" :key="organization.id" :value="organization.id">{{ organization.name }}</option></select><span v-if="firstError('organization')" class="mt-1 block text-xs text-red-600">{{ firstError('organization') }}</span></label>
          <label class="text-sm font-medium text-gray-700">Room code *<input v-model.trim="classroomForm.room_code" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="firstError('room_code')" class="mt-1 block text-xs text-red-600">{{ firstError('room_code') }}</span></label>
          <label class="text-sm font-medium text-gray-700">Building<input v-model.trim="classroomForm.building" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"></label>
          <label class="sm:col-span-2 text-sm font-medium text-gray-700">Capacity<input v-model="classroomForm.capacity" type="number" min="1" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="firstError('capacity')" class="mt-1 block text-xs text-red-600">{{ firstError('capacity') }}</span></label>
        </div>
        <div class="flex justify-end gap-3 border-t px-6 py-4"><button type="button" class="rounded-xl border px-5 py-2.5 text-sm font-semibold" @click="closeModal">Cancel</button><button class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : 'Save Classroom' }}</button></div>
      </form>

      <form v-else-if="modal === 'subject'" class="w-full max-w-xl rounded-2xl bg-white shadow-xl" @submit.prevent="saveSubject">
        <div class="flex items-center justify-between border-b px-6 py-4"><h2 class="text-lg font-bold">{{ isEditing ? 'Edit Subject' : 'Add Subject' }}</h2><button type="button" class="text-gray-400" @click="closeModal">✕</button></div>
        <div class="grid gap-4 p-6 sm:grid-cols-2">
          <div v-if="formError" class="sm:col-span-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ formError }}</div>
          <label class="text-sm font-medium text-gray-700">Subject code *<input v-model.trim="subjectForm.subject_code" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="firstError('subject_code')" class="mt-1 block text-xs text-red-600">{{ firstError('subject_code') }}</span></label>
          <label class="text-sm font-medium text-gray-700">Subject name *<input v-model.trim="subjectForm.subject_name" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"></label>
          <label class="text-sm font-medium text-gray-700">Classroom *<select v-model="subjectForm.classroom" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option value="">Select classroom</option><option v-for="classroom in classrooms" :key="classroom.id" :value="classroom.id">{{ classroom.room_code }} — {{ classroom.organization_name }}</option></select><span v-if="firstError('classroom')" class="mt-1 block text-xs text-red-600">{{ firstError('classroom') }}</span></label>
          <label class="text-sm font-medium text-gray-700">Teacher *<select v-model="subjectForm.teacher" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option value="">Select teacher</option><option v-for="teacher in availableTeachers" :key="teacher.id" :value="teacher.id">{{ teacher.name }}</option></select><span v-if="firstError('teacher')" class="mt-1 block text-xs text-red-600">{{ firstError('teacher') }}</span></label>
        </div>
        <div class="flex justify-end gap-3 border-t px-6 py-4"><button type="button" class="rounded-xl border px-5 py-2.5 text-sm font-semibold" @click="closeModal">Cancel</button><button class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : 'Save Subject' }}</button></div>
      </form>

      <form v-else class="w-full max-w-xl rounded-2xl bg-white shadow-xl" @submit.prevent="saveCamera">
        <div class="flex items-center justify-between border-b px-6 py-4"><h2 class="text-lg font-bold">{{ isEditing ? 'Edit Camera' : 'Add Camera' }}</h2><button type="button" class="text-gray-400" @click="closeModal">✕</button></div>
        <div class="grid gap-4 p-6 sm:grid-cols-2">
          <div v-if="formError" class="sm:col-span-2 rounded-lg bg-red-50 p-3 text-sm text-red-700">{{ formError }}</div>
          <label class="sm:col-span-2 text-sm font-medium text-gray-700">Classroom *<select v-model="cameraForm.classroom" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option value="">Select classroom</option><option v-for="classroom in classrooms" :key="classroom.id" :value="classroom.id">{{ classroom.room_code }} — {{ classroom.organization_name }}</option></select><span v-if="firstError('classroom')" class="mt-1 block text-xs text-red-600">{{ firstError('classroom') }}</span></label>
          <label class="sm:col-span-2 text-sm font-medium text-gray-700">Camera name *<input v-model.trim="cameraForm.camera_name" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5"><span v-if="firstError('camera_name')" class="mt-1 block text-xs text-red-600">{{ firstError('camera_name') }}</span></label>
          <label class="text-sm font-medium text-gray-700">Position *<select v-model="cameraForm.position" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option v-for="position in options.camera_positions" :key="position.value" :value="position.value">{{ position.label }}</option></select><span v-if="firstError('position')" class="mt-1 block text-xs text-red-600">{{ firstError('position') }}</span></label>
          <label class="text-sm font-medium text-gray-700">Status *<select v-model="cameraForm.status" required class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5"><option v-for="status in options.camera_statuses" :key="status.value" :value="status.value">{{ status.label }}</option></select><span v-if="firstError('status')" class="mt-1 block text-xs text-red-600">{{ firstError('status') }}</span></label>
        </div>
        <div class="flex justify-end gap-3 border-t px-6 py-4"><button type="button" class="rounded-xl border px-5 py-2.5 text-sm font-semibold" @click="closeModal">Cancel</button><button class="btn-teal" :disabled="saving">{{ saving ? 'Saving…' : 'Save Camera' }}</button></div>
      </form>
    </div>
  </AppLayout>
</template>
