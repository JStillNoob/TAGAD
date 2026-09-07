<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import AppLayout from '../layouts/AppLayout.vue'
import { currentUser } from '../auth'
import {
  createManagedUser,
  deactivateManagedUser,
  fetchManagedUsers,
  fetchUserOptions,
  updateManagedUser,
} from '../userManagement'

const users = ref([])
const options = ref({ roles: [], statuses: [], organizations: [] })
const loading = ref(true)
const saving = ref(false)
const pageError = ref('')
const formError = ref('')
const fieldErrors = ref({})
const search = ref('')
const roleFilter = ref('')
const statusFilter = ref('')
const showForm = ref(false)
const editingId = ref(null)

const blankForm = () => ({
  username: '',
  email: '',
  first_name: '',
  middle_name: '',
  last_name: '',
  contact_no: '',
  organization: '',
  role: 'teacher',
  status: 'active',
  password: '',
})
const form = reactive(blankForm())

const isSystemAdmin = computed(() => currentUser.value?.role === 'system_admin')
const isEditing = computed(() => editingId.value !== null)
const organizationRequired = computed(() => form.role !== 'system_admin')
const filteredUsers = computed(() => {
  const term = search.value.trim().toLowerCase()
  return users.value.filter((user) => {
    const searchable = [
      user.username,
      user.email,
      user.first_name,
      user.middle_name,
      user.last_name,
      user.organization_name,
    ].join(' ').toLowerCase()
    return (!term || searchable.includes(term))
      && (!roleFilter.value || user.role === roleFilter.value)
      && (!statusFilter.value || user.status === statusFilter.value)
  })
})

watch(() => form.role, (role) => {
  if (role === 'system_admin') form.organization = ''
})

function labelFor(items, value) {
  return items.find((item) => item.value === value)?.label || value
}

function resetForm() {
  Object.assign(form, blankForm())
  if (!isSystemAdmin.value) {
    form.role = 'teacher'
    form.organization = options.value.organizations[0]?.id || ''
  }
  editingId.value = null
  formError.value = ''
  fieldErrors.value = {}
}

function openCreate() {
  resetForm()
  showForm.value = true
}

function openEdit(user) {
  resetForm()
  editingId.value = user.id
  Object.assign(form, {
    username: user.username,
    email: user.email,
    first_name: user.first_name,
    middle_name: user.middle_name,
    last_name: user.last_name,
    contact_no: user.contact_no,
    organization: user.organization || '',
    role: user.role,
    status: user.status,
    password: '',
  })
  showForm.value = true
}

function closeForm() {
  if (!saving.value) showForm.value = false
}

async function loadPage() {
  loading.value = true
  pageError.value = ''
  try {
    const [userList, userOptions] = await Promise.all([
      fetchManagedUsers(),
      fetchUserOptions(),
    ])
    users.value = userList
    options.value = userOptions
  } catch (error) {
    pageError.value = error.message
  } finally {
    loading.value = false
  }
}

async function saveUser() {
  saving.value = true
  formError.value = ''
  fieldErrors.value = {}
  const payload = { ...form }
  payload.organization = payload.organization || null
  if (isEditing.value && !payload.password) delete payload.password

  try {
    const saved = isEditing.value
      ? await updateManagedUser(editingId.value, payload)
      : await createManagedUser(payload)
    const index = users.value.findIndex((user) => user.id === saved.id)
    if (index === -1) users.value.push(saved)
    else users.value[index] = saved
    showForm.value = false
  } catch (error) {
    formError.value = error.message
    fieldErrors.value = error.fields || {}
  } finally {
    saving.value = false
  }
}

async function deactivateUser(user) {
  if (!window.confirm(`Deactivate ${user.username}? They will no longer be able to sign in.`)) return
  pageError.value = ''
  try {
    await deactivateManagedUser(user.id)
    user.status = 'inactive'
  } catch (error) {
    pageError.value = error.message
  }
}

async function reactivateUser(user) {
  pageError.value = ''
  try {
    const updated = await updateManagedUser(user.id, { status: 'active' })
    Object.assign(user, updated)
  } catch (error) {
    pageError.value = error.message
  }
}

onMounted(loadPage)
</script>

<template>
  <AppLayout page-title="User Management">
    <div class="max-w-7xl mx-auto space-y-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">User Management</h1>
          <p class="text-sm text-gray-500 mt-1">
            {{ isSystemAdmin ? 'Manage accounts across all organizations.' : 'Manage teachers in your organization.' }}
          </p>
        </div>
        <button type="button" class="btn-primary justify-center" @click="openCreate">
          <span class="text-lg leading-none">+</span> Add User
        </button>
      </div>

      <div v-if="pageError" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ pageError }}
      </div>

      <section class="page-card overflow-hidden">
        <div class="p-4 border-b border-gray-200 grid gap-3 md:grid-cols-[1fr_180px_160px]">
          <label>
            <span class="sr-only">Search users</span>
            <input v-model="search" type="search" placeholder="Search name, username, or email…" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-indigo-500" />
          </label>
          <label>
            <span class="sr-only">Filter by role</span>
            <select v-model="roleFilter" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white">
              <option value="">All roles</option>
              <option v-for="role in options.roles" :key="role.value" :value="role.value">{{ role.label }}</option>
            </select>
          </label>
          <label>
            <span class="sr-only">Filter by status</span>
            <select v-model="statusFilter" class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm bg-white">
              <option value="">All statuses</option>
              <option v-for="status in options.statuses" :key="status.value" :value="status.value">{{ status.label }}</option>
            </select>
          </label>
        </div>

        <div v-if="loading" class="p-10 text-center text-sm text-gray-500">Loading users…</div>
        <div v-else-if="!filteredUsers.length" class="p-10 text-center text-sm text-gray-500">No users match these filters.</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-left text-sm">
            <thead class="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th class="px-5 py-3 font-semibold">User</th>
                <th class="px-5 py-3 font-semibold">Role</th>
                <th class="px-5 py-3 font-semibold">Organization</th>
                <th class="px-5 py-3 font-semibold">Status</th>
                <th class="px-5 py-3 font-semibold text-right">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="user in filteredUsers" :key="user.id" class="hover:bg-gray-50">
                <td class="px-5 py-4">
                  <div class="font-semibold text-gray-900">{{ [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username }}</div>
                  <div class="text-xs text-gray-500 mt-0.5">{{ user.username }} · {{ user.email }}</div>
                </td>
                <td class="px-5 py-4 text-gray-700">{{ labelFor(options.roles, user.role) }}</td>
                <td class="px-5 py-4 text-gray-700">{{ user.organization_name || 'Platform-wide' }}</td>
                <td class="px-5 py-4">
                  <span :class="user.status === 'active' ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-600'" class="inline-flex rounded-full px-2.5 py-1 text-xs font-semibold">
                    {{ labelFor(options.statuses, user.status) }}
                  </span>
                </td>
                <td class="px-5 py-4">
                  <div class="flex justify-end gap-2">
                    <button type="button" class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50" @click="openEdit(user)">Edit</button>
                    <button v-if="user.id !== currentUser?.id && user.status === 'active'" type="button" class="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-semibold text-red-600 hover:bg-red-50" @click="deactivateUser(user)">Deactivate</button>
                    <button v-else-if="user.id !== currentUser?.id" type="button" class="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50" @click="reactivateUser(user)">Reactivate</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>

    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" @click.self="closeForm">
      <form class="w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-xl" @submit.prevent="saveUser">
        <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 class="text-lg font-bold text-gray-900">{{ isEditing ? 'Edit User' : 'Add User' }}</h2>
            <p class="text-xs text-gray-500 mt-1">Fields marked with * are required.</p>
          </div>
          <button type="button" class="rounded-lg p-2 text-gray-400 hover:bg-gray-100" aria-label="Close" @click="closeForm">✕</button>
        </div>

        <div class="p-6 grid gap-4 sm:grid-cols-2">
          <div v-if="formError" class="sm:col-span-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{{ formError }}</div>

          <label class="text-sm font-medium text-gray-700">First name *
            <input v-model.trim="form.first_name" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.first_name" class="mt-1 block text-xs text-red-600">{{ fieldErrors.first_name[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Last name *
            <input v-model.trim="form.last_name" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.last_name" class="mt-1 block text-xs text-red-600">{{ fieldErrors.last_name[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Middle name
            <input v-model.trim="form.middle_name" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
          </label>
          <label class="text-sm font-medium text-gray-700">Contact number
            <input v-model.trim="form.contact_no" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
          </label>
          <label class="text-sm font-medium text-gray-700">Username *
            <input v-model.trim="form.username" required autocomplete="off" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.username" class="mt-1 block text-xs text-red-600">{{ fieldErrors.username[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Email address *
            <input v-model.trim="form.email" required type="email" autocomplete="off" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.email" class="mt-1 block text-xs text-red-600">{{ fieldErrors.email[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Role *
            <select v-model="form.role" required :disabled="isEditing && editingId === currentUser?.id" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 bg-white disabled:bg-gray-100">
              <option v-for="role in options.roles" :key="role.value" :value="role.value">{{ role.label }}</option>
            </select>
            <span v-if="fieldErrors.role" class="mt-1 block text-xs text-red-600">{{ fieldErrors.role[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Organization {{ organizationRequired ? '*' : '' }}
            <select v-model="form.organization" :required="organizationRequired" :disabled="!isSystemAdmin || !organizationRequired || (isEditing && editingId === currentUser?.id)" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 bg-white disabled:bg-gray-100">
              <option value="">{{ organizationRequired ? 'Select organization' : 'Platform-wide' }}</option>
              <option v-for="organization in options.organizations" :key="organization.id" :value="organization.id">{{ organization.name }}</option>
            </select>
            <span v-if="fieldErrors.organization" class="mt-1 block text-xs text-red-600">{{ fieldErrors.organization[0] }}</span>
          </label>
          <label v-if="isEditing" class="text-sm font-medium text-gray-700">Status *
            <select v-model="form.status" required :disabled="editingId === currentUser?.id" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 bg-white disabled:bg-gray-100">
              <option v-for="status in options.statuses" :key="status.value" :value="status.value">{{ status.label }}</option>
            </select>
            <span v-if="fieldErrors.status" class="mt-1 block text-xs text-red-600">{{ fieldErrors.status[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700" :class="isEditing ? '' : 'sm:col-span-2'">{{ isEditing ? 'New password' : 'Password *' }}
            <input v-model="form.password" :required="!isEditing" type="password" autocomplete="new-password" minlength="12" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span class="mt-1 block text-xs text-gray-500">{{ isEditing ? 'Leave blank to keep the current password.' : 'Use at least 12 characters and avoid common or personal passwords.' }}</span>
            <span v-if="fieldErrors.password" class="mt-1 block text-xs text-red-600">{{ fieldErrors.password[0] }}</span>
          </label>
        </div>

        <div class="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button type="button" class="rounded-xl border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50" :disabled="saving" @click="closeForm">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : (isEditing ? 'Save Changes' : 'Create User') }}</button>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
