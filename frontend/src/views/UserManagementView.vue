<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppLayout from '../layouts/AppLayout.vue'
import PaginationControls from '../components/PaginationControls.vue'
import SearchablePicker from '../components/SearchablePicker.vue'
import { currentUser } from '../auth'
import { fetchConfigurationOptions } from '../configurationOptions'
import {
  createManagedUser,
  deactivateManagedUser,
  fetchManagedUsers,
  fetchUserOptions,
  updateManagedUser,
} from '../userManagement'

const route = useRoute()

const users = ref([])
const userCount = ref(0)
const userPage = ref(1)
const pageSize = 20
const options = ref({ roles: [], statuses: [] })
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
const filteredUsers = computed(() => users.value)
let filterTimer = null

watch(() => form.role, (role) => {
  if (role === 'system_admin') form.organization = ''
})
watch(() => route.query.search, (value) => {
  search.value = typeof value === 'string' ? value : ''
}, { immediate: true })

function labelFor(items, value) {
  return items.find((item) => item.value === value)?.label || value
}

function resetForm() {
  Object.assign(form, blankForm())
  if (isSystemAdmin.value) {
    form.role = 'org_admin'
  } else {
    form.role = 'teacher'
    form.organization = currentUser.value?.organization || ''
  }
  editingId.value = null
  formError.value = ''
  fieldErrors.value = {}
}

function loadOrganizationOptions(parameters) {
  return fetchConfigurationOptions('organizations', parameters)
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
      fetchManagedUsers({
        page: userPage.value,
        search: search.value.trim(),
        role: roleFilter.value,
        status: statusFilter.value,
      }),
      fetchUserOptions(),
    ])
    users.value = userList.results
    userCount.value = userList.count
    options.value = userOptions
  } catch (error) {
    pageError.value = error.message
  } finally {
    loading.value = false
  }
}

function changePage(page) {
  userPage.value = page
  loadPage()
}

watch([search, roleFilter, statusFilter], () => {
  clearTimeout(filterTimer)
  filterTimer = setTimeout(() => {
    userPage.value = 1
    loadPage()
  }, 250)
})

async function saveUser() {
  if (saving.value) return
  saving.value = true
  formError.value = ''
  fieldErrors.value = {}
  const payload = { ...form }
  payload.organization = payload.organization || null
  if (isEditing.value && !payload.password) delete payload.password

  try {
    isEditing.value
      ? await updateManagedUser(editingId.value, payload)
      : await createManagedUser(payload)
    showForm.value = false
    await loadPage()
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

onMounted(async () => {
  await loadPage()
})
onUnmounted(() => {
  clearTimeout(filterTimer)
})
</script>

<template>
  <AppLayout :page-title="isSystemAdmin ? 'Organization Admins' : 'User Management'">
    <div class="platform-management-page space-y-6">
      <section class="app-page-hero platform-management-hero page-card">
        <div class="platform-management-hero-copy">
          <h1>{{ isSystemAdmin ? 'Organization Administrators' : 'User Management' }}</h1>
          <p>{{ isSystemAdmin ? 'Assign an administrator to each organization.' : 'Manage teachers in your organization.' }}</p>
          <button type="button" class="btn-primary disabled:cursor-not-allowed disabled:opacity-60" :disabled="loading" @click="openCreate">
            <span class="text-xl leading-none" aria-hidden="true">+</span> {{ isSystemAdmin ? 'Add Organization Admin' : 'Add User' }}
          </button>
        </div>
        <img src="/illustrations/administrators.png" alt="" aria-hidden="true" class="platform-management-hero-art">
      </section>

      <div v-if="pageError" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ pageError }}
      </div>

      <section class="platform-data-panel page-card" aria-label="Users">
        <div class="platform-filter-panel platform-admin-filters" role="group" aria-label="User filters">
          <label class="platform-filter-field">
            <span>Search</span>
            <span class="platform-search-field">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m16 16 4 4" /></svg>
              <input v-model="search" type="search" placeholder="Search name, username, or email…" />
            </span>
          </label>
          <label class="platform-filter-field">
            <span>Role</span>
            <select v-model="roleFilter">
              <option value="">All roles</option>
              <option v-for="role in options.roles" :key="role.value" :value="role.value">{{ role.label }}</option>
            </select>
          </label>
          <label class="platform-filter-field">
            <span>Status</span>
            <select v-model="statusFilter">
              <option value="">All statuses</option>
              <option v-for="status in options.statuses" :key="status.value" :value="status.value">{{ status.label }}</option>
            </select>
          </label>
        </div>

        <div v-if="loading" class="p-10 text-center text-sm text-gray-500">Loading users…</div>
        <div v-else-if="!filteredUsers.length" class="p-10 text-center text-sm text-gray-500">No users match these filters.</div>
        <div v-else class="platform-table-scroll">
          <table class="platform-data-table w-full min-w-[920px] text-left text-sm">
            <thead>
              <tr>
                <th>User</th>
                <th>Role</th>
                <th>Organization</th>
                <th>Status</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in filteredUsers" :key="user.id">
                <td>
                  <div class="platform-record-identity">
                    <span class="platform-record-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="3.5" /><path d="M4.5 20v-1a7.5 7.5 0 0 1 15 0v1h-15Z" /></svg></span>
                    <span><strong>{{ [user.first_name, user.last_name].filter(Boolean).join(' ') || user.username }}</strong><small>{{ user.username }} · {{ user.email }}</small></span>
                  </div>
                </td>
                <td data-label="Role"><span class="platform-role-badge">{{ labelFor(options.roles, user.role) }}</span></td>
                <td data-label="Organization">{{ user.organization_name || 'Platform-wide' }}</td>
                <td data-label="Status">
                  <span class="platform-status-badge" :class="user.status === 'active' ? 'is-active' : 'is-inactive'">
                    {{ labelFor(options.statuses, user.status) }}
                  </span>
                </td>
                <td data-label="Actions">
                  <div class="platform-row-actions">
                    <button type="button" class="platform-action-button" @click="openEdit(user)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20ZM13.5 7.5l3 3" /></svg>Edit</button>
                    <button v-if="user.id !== currentUser?.id && user.status === 'active'" type="button" class="platform-action-button is-alert" @click="deactivateUser(user)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v9m-5-6a9 9 0 1 0 10 0" /></svg>Deactivate</button>
                    <button v-else-if="user.id !== currentUser?.id" type="button" class="platform-action-button" @click="reactivateUser(user)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3v9m-5-6a9 9 0 1 0 10 0" /></svg>Reactivate</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <PaginationControls class="platform-pagination" :page="userPage" :count="userCount" :page-size="pageSize" :disabled="loading" @change="changePage" />
      </section>

    </div>

    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" @click.self="closeForm">
      <form role="dialog" aria-labelledby="user-form-title" class="platform-management-dialog w-full max-w-3xl max-h-[90vh] overflow-y-auto rounded-2xl bg-white shadow-xl" @submit.prevent="saveUser">
        <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="user-form-title" class="text-lg font-bold text-gray-900">{{ isEditing ? 'Edit User' : 'Add User' }}</h2>
            <p class="text-xs text-gray-500 mt-1">Fields marked with * are required.</p>
          </div>
          <button type="button" class="rounded-lg p-2 text-gray-400 hover:bg-gray-100" aria-label="Close" @click="closeForm">✕</button>
        </div>

        <div class="p-6 grid gap-4 sm:grid-cols-2">
          <div v-if="formError" class="sm:col-span-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">{{ formError }}</div>

          <label class="text-sm font-medium text-gray-700">First name *
            <input v-model.trim="form.first_name" required maxlength="150" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.first_name" class="mt-1 block text-xs text-red-600">{{ fieldErrors.first_name[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Last name *
            <input v-model.trim="form.last_name" required maxlength="150" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.last_name" class="mt-1 block text-xs text-red-600">{{ fieldErrors.last_name[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Middle name
            <input v-model.trim="form.middle_name" maxlength="50" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.middle_name" class="mt-1 block text-xs text-red-600">{{ fieldErrors.middle_name[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Contact number
            <input v-model.trim="form.contact_no" maxlength="20" inputmode="tel" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.contact_no" class="mt-1 block text-xs text-red-600">{{ fieldErrors.contact_no[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Username *
            <input v-model.trim="form.username" required maxlength="150" autocomplete="off" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.username" class="mt-1 block text-xs text-red-600">{{ fieldErrors.username[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Email address *
            <input v-model.trim="form.email" required type="email" maxlength="254" autocomplete="off" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="fieldErrors.email" class="mt-1 block text-xs text-red-600">{{ fieldErrors.email[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Role *
            <select v-model="form.role" required :disabled="isEditing && editingId === currentUser?.id" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 bg-white disabled:bg-gray-100">
              <option v-for="role in options.roles" :key="role.value" :value="role.value">{{ role.label }}</option>
            </select>
            <span v-if="fieldErrors.role" class="mt-1 block text-xs text-red-600">{{ fieldErrors.role[0] }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Organization {{ organizationRequired ? '*' : '' }}
            <SearchablePicker
              v-model="form.organization"
              :loader="loadOrganizationOptions"
              :required="organizationRequired"
              :disabled="!isSystemAdmin || !organizationRequired || (isEditing && editingId === currentUser?.id)"
              :placeholder="organizationRequired ? 'Select organization' : 'Platform-wide'"
              select-label="Organization"
              search-label="Search organizations"
              search-placeholder="Search organization name or code…"
            />
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
