<script setup>
import { computed, nextTick, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppConfirmDialog from '../components/AppConfirmDialog.vue'
import AppDialog from '../components/AppDialog.vue'
import AppLayout from '../layouts/AppLayout.vue'
import PaginationControls from '../components/PaginationControls.vue'
import SearchablePicker from '../components/SearchablePicker.vue'
import { currentUser } from '../auth'
import { fetchConfigurationOptions } from '../configurationOptions'
import { useConfirmation } from '../useConfirmation'
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
const { confirmation, requestConfirmation, acceptConfirmation, cancelConfirmation } = useConfirmation()

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

function firstError(field) {
  const value = fieldErrors.value[field]
  return Array.isArray(value) ? value[0] : value || ''
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
    await nextTick()
    document.querySelector('.app-dialog [aria-invalid="true"]')?.focus()
  } finally {
    saving.value = false
  }
}

async function deactivateUser(user) {
  const confirmed = await requestConfirmation({
    title: 'Deactivate user?',
    description: `${user.username} will no longer be able to sign in. Their account and historical records will remain available for reactivation.`,
    confirmLabel: 'Deactivate user',
  })
  if (!confirmed) return
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
        <img src="/illustrations/administrators.png" width="1536" height="1024" alt="" aria-hidden="true" class="platform-management-hero-art">
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

    <AppDialog
      :open="showForm"
      labelledby="user-form-title"
      describedby="user-form-description"
      panel-class="platform-management-dialog max-w-3xl"
      :busy="saving"
      @close="closeForm"
    >
      <form @submit.prevent="saveUser">
        <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="user-form-title" class="text-lg font-bold text-gray-900">{{ isEditing ? 'Edit User' : 'Add User' }}</h2>
            <p id="user-form-description" class="text-xs text-gray-500 mt-1">Fields marked with * are required.</p>
          </div>
          <button type="button" class="rounded-lg p-2 text-gray-400 hover:bg-gray-100" aria-label="Close" @click="closeForm">✕</button>
        </div>

        <div class="p-6 grid gap-4 sm:grid-cols-2">
          <div v-if="formError" class="sm:col-span-2 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{{ formError }}</div>

          <label class="text-sm font-medium text-gray-700">First name *
            <input id="user-first-name" v-model.trim="form.first_name" required maxlength="150" :aria-invalid="Boolean(firstError('first_name'))" :aria-describedby="firstError('first_name') ? 'user-first-name-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('first_name')" id="user-first-name-error" class="mt-1 block text-xs text-red-600">{{ firstError('first_name') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Last name *
            <input id="user-last-name" v-model.trim="form.last_name" required maxlength="150" :aria-invalid="Boolean(firstError('last_name'))" :aria-describedby="firstError('last_name') ? 'user-last-name-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('last_name')" id="user-last-name-error" class="mt-1 block text-xs text-red-600">{{ firstError('last_name') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Middle name
            <input id="user-middle-name" v-model.trim="form.middle_name" maxlength="50" :aria-invalid="Boolean(firstError('middle_name'))" :aria-describedby="firstError('middle_name') ? 'user-middle-name-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('middle_name')" id="user-middle-name-error" class="mt-1 block text-xs text-red-600">{{ firstError('middle_name') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Contact number
            <input id="user-contact-number" v-model.trim="form.contact_no" maxlength="20" inputmode="tel" :aria-invalid="Boolean(firstError('contact_no'))" :aria-describedby="firstError('contact_no') ? 'user-contact-number-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('contact_no')" id="user-contact-number-error" class="mt-1 block text-xs text-red-600">{{ firstError('contact_no') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Username *
            <input id="user-username" v-model.trim="form.username" required maxlength="150" autocomplete="off" :aria-invalid="Boolean(firstError('username'))" :aria-describedby="firstError('username') ? 'user-username-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('username')" id="user-username-error" class="mt-1 block text-xs text-red-600">{{ firstError('username') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Email address *
            <input id="user-email" v-model.trim="form.email" required type="email" maxlength="254" autocomplete="off" :aria-invalid="Boolean(firstError('email'))" :aria-describedby="firstError('email') ? 'user-email-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('email')" id="user-email-error" class="mt-1 block text-xs text-red-600">{{ firstError('email') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Role *
            <select id="user-role" v-model="form.role" required :disabled="isEditing && editingId === currentUser?.id" :aria-invalid="Boolean(firstError('role'))" :aria-describedby="firstError('role') ? 'user-role-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 bg-white disabled:bg-gray-100">
              <option v-for="role in options.roles" :key="role.value" :value="role.value">{{ role.label }}</option>
            </select>
            <span v-if="firstError('role')" id="user-role-error" class="mt-1 block text-xs text-red-600">{{ firstError('role') }}</span>
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
              control-id="user-organization"
              :invalid="Boolean(firstError('organization'))"
              :describedby="firstError('organization') ? 'user-organization-error' : ''"
            />
            <span v-if="firstError('organization')" id="user-organization-error" class="mt-1 block text-xs text-red-600">{{ firstError('organization') }}</span>
          </label>
          <label v-if="isEditing" class="text-sm font-medium text-gray-700">Status *
            <select id="user-status" v-model="form.status" required :disabled="editingId === currentUser?.id" :aria-invalid="Boolean(firstError('status'))" :aria-describedby="firstError('status') ? 'user-status-error' : undefined" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 bg-white disabled:bg-gray-100">
              <option v-for="status in options.statuses" :key="status.value" :value="status.value">{{ status.label }}</option>
            </select>
            <span v-if="firstError('status')" id="user-status-error" class="mt-1 block text-xs text-red-600">{{ firstError('status') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700" :class="isEditing ? '' : 'sm:col-span-2'">{{ isEditing ? 'New password' : 'Password *' }}
            <input id="user-password" v-model="form.password" :required="!isEditing" type="password" autocomplete="new-password" minlength="12" :aria-invalid="Boolean(firstError('password'))" :aria-describedby="firstError('password') ? 'user-password-help user-password-error' : 'user-password-help'" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span id="user-password-help" class="mt-1 block text-xs text-gray-500">{{ isEditing ? 'Leave blank to keep the current password.' : 'Use at least 12 characters and avoid common or personal passwords.' }}</span>
            <span v-if="firstError('password')" id="user-password-error" class="mt-1 block text-xs text-red-600">{{ firstError('password') }}</span>
          </label>
        </div>

        <div class="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button type="button" class="rounded-xl border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50" :disabled="saving" @click="closeForm">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : (isEditing ? 'Save Changes' : 'Create User') }}</button>
        </div>
      </form>
    </AppDialog>
    <AppConfirmDialog
      :open="Boolean(confirmation)"
      v-bind="confirmation || {}"
      @confirm="acceptConfirmation"
      @cancel="cancelConfirmation"
    />
  </AppLayout>
</template>
