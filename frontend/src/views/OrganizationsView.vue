<script setup>
import { onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import AppLayout from '../layouts/AppLayout.vue'
import PaginationControls from '../components/PaginationControls.vue'
import {
  archiveOrganization,
  createOrganization,
  fetchOrganizations,
  restoreOrganization,
  updateOrganization,
} from '../userManagement'

const organizations = ref([])
const organizationCount = ref(0)
const page = ref(1)
const pageSize = 20
const lifecycle = ref('active')
const search = ref('')
const loading = ref(true)
const saving = ref(false)
const showForm = ref(false)
const editingId = ref(null)
const pageError = ref('')
const success = ref('')
const formError = ref('')
const fieldErrors = ref({})

const blankForm = () => ({
  organization_name: '',
  organization_code: '',
  address: '',
  contact_email: '',
  contact_no: '',
})
const form = reactive(blankForm())

function firstError(field) {
  const value = fieldErrors.value[field]
  return Array.isArray(value) ? value[0] : value || ''
}

function resetForm() {
  Object.assign(form, blankForm())
  editingId.value = null
  formError.value = ''
  fieldErrors.value = {}
}

function openCreate() {
  resetForm()
  showForm.value = true
}

function openEdit(organization) {
  resetForm()
  editingId.value = organization.id
  Object.assign(form, {
    organization_name: organization.organization_name,
    organization_code: organization.organization_code,
    address: organization.address,
    contact_email: organization.contact_email,
    contact_no: organization.contact_no,
  })
  showForm.value = true
}

function closeForm() {
  if (!saving.value) showForm.value = false
}

async function loadOrganizations(requestedPage = page.value) {
  loading.value = true
  pageError.value = ''
  try {
    const data = await fetchOrganizations({
      page: requestedPage,
      search: search.value.trim(),
      lifecycle: lifecycle.value,
    })
    organizations.value = data.results
    organizationCount.value = data.count
    page.value = requestedPage
  } catch (error) {
    pageError.value = error.message
  } finally {
    loading.value = false
  }
}

async function saveOrganization() {
  if (saving.value) return
  saving.value = true
  formError.value = ''
  fieldErrors.value = {}
  try {
    editingId.value
      ? await updateOrganization(editingId.value, form)
      : await createOrganization(form)
    success.value = editingId.value ? 'Organization updated.' : 'Organization created.'
    showForm.value = false
    await loadOrganizations(1)
  } catch (error) {
    formError.value = error.message
    fieldErrors.value = error.fields || {}
  } finally {
    saving.value = false
  }
}

async function archiveRecord(organization) {
  if (!window.confirm(`Archive ${organization.organization_name}? Its users will be unable to sign in until it is restored.`)) return
  pageError.value = ''
  success.value = ''
  try {
    await archiveOrganization(organization.id)
    success.value = 'Organization archived.'
    await loadOrganizations(page.value)
  } catch (error) {
    pageError.value = error.message
  }
}

async function restoreRecord(organization) {
  pageError.value = ''
  success.value = ''
  try {
    await restoreOrganization(organization.id)
    success.value = 'Organization restored.'
    await loadOrganizations(page.value)
  } catch (error) {
    pageError.value = error.message
  }
}

let filterTimer = null
watch([search, lifecycle], () => {
  clearTimeout(filterTimer)
  filterTimer = setTimeout(() => loadOrganizations(1), 250)
})

onMounted(loadOrganizations)
onUnmounted(() => clearTimeout(filterTimer))
</script>

<template>
  <AppLayout page-title="Organizations">
    <div class="platform-management-page space-y-6">
      <section class="platform-management-hero page-card">
        <div class="platform-management-hero-copy">
          <h1>Organizations</h1>
          <p>Manage every institution using TAGAD.</p>
          <button type="button" class="btn-primary" @click="openCreate">
            <span class="text-xl leading-none" aria-hidden="true">+</span> Add Organization
          </button>
        </div>
        <img src="/illustrations/organizations.png" alt="" aria-hidden="true" class="platform-management-hero-art">
      </section>

      <p v-if="pageError" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{{ pageError }}</p>
      <p v-if="success" class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">{{ success }}</p>

      <section class="platform-data-panel page-card" aria-label="Organizations">
        <div class="platform-filter-panel platform-organization-filters" role="group" aria-label="Organization filters">
          <label class="platform-filter-field">
            <span>Search</span>
            <span class="platform-search-field">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="11" cy="11" r="7" /><path d="m16 16 4 4" /></svg>
              <input v-model="search" type="search" placeholder="Name or organization code…" />
            </span>
          </label>
          <label class="platform-filter-field">
            <span>Status</span>
            <select v-model="lifecycle">
              <option value="active">Active</option>
              <option value="archived">Archived</option>
              <option value="all">All</option>
            </select>
          </label>
        </div>

        <div v-if="loading" class="p-10 text-center text-sm text-gray-500">Loading organizations…</div>
        <div v-else-if="!organizations.length" class="p-10 text-center text-sm text-gray-500">No organizations match these filters.</div>
        <div v-else class="platform-table-scroll">
          <table class="platform-data-table w-full min-w-[780px] text-left text-sm">
            <thead>
              <tr>
                <th>Organization</th>
                <th>Contact</th>
                <th>Status</th>
                <th class="text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="organization in organizations" :key="organization.id">
                <td>
                  <div class="platform-record-identity">
                    <span class="platform-record-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="m2.5 9 9.5-5 9.5 5-9.5 5-9.5-5Z" /><path d="M6 11v5c3.3 2.8 8.7 2.8 12 0v-5M21.5 9v6" /></svg></span>
                    <span><strong>{{ organization.organization_name }}</strong><small>{{ organization.organization_code }}<template v-if="organization.address"> · {{ organization.address }}</template></small></span>
                  </div>
                </td>
                <td data-label="Contact">
                  <div class="platform-contact-line"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="5" width="18" height="14" rx="2" /><path d="m4 7 8 6 8-6" /></svg><span>{{ organization.contact_email || 'No email set' }}</span></div>
                  <div class="platform-contact-line"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M7 3.5 4 6.5c-1 1 0 5 4 9s8 5 9 4l3-3-4-4-2.5 2.5a16 16 0 0 1-4.5-4.5L11.5 8 7 3.5Z" /></svg><span>{{ organization.contact_no || 'No contact number' }}</span></div>
                </td>
                <td data-label="Status">
                  <span class="platform-status-badge" :class="organization.is_archived ? 'is-inactive' : 'is-active'">
                    {{ organization.is_archived ? 'Archived' : 'Active' }}
                  </span>
                </td>
                <td data-label="Actions">
                  <div class="platform-row-actions">
                    <button v-if="!organization.is_archived" type="button" class="platform-action-button" @click="openEdit(organization)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m4 20 4.5-1 10-10a2.1 2.1 0 0 0-3-3l-10 10L4 20ZM13.5 7.5l3 3" /></svg>Edit</button>
                    <button v-if="!organization.is_archived" type="button" class="platform-action-button is-alert" @click="archiveRecord(organization)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="4" y="8" width="16" height="12" rx="2" /><path d="M3 4h18v4H3zm7 10h4" /></svg>Archive</button>
                    <button v-else type="button" class="platform-action-button" @click="restoreRecord(organization)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 11a8 8 0 1 1 2 6M4 17v-6h6" /></svg>Restore</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <PaginationControls class="platform-pagination" :page="page" :count="organizationCount" :page-size="pageSize" :disabled="loading" @change="loadOrganizations" />
      </section>
    </div>

    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" @click.self="closeForm">
      <form role="dialog" aria-labelledby="organization-form-title" class="platform-management-dialog max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-xl" @submit.prevent="saveOrganization">
        <div class="flex items-center justify-between border-b border-gray-200 px-6 py-4">
          <div>
            <h2 id="organization-form-title" class="text-lg font-bold text-gray-900">{{ editingId ? 'Edit Organization' : 'Add Organization' }}</h2>
            <p class="mt-1 text-xs text-gray-500">Fields marked with * are required.</p>
          </div>
          <button type="button" class="rounded-lg p-2 text-gray-400 hover:bg-gray-100" aria-label="Close" @click="closeForm">✕</button>
        </div>

        <div class="grid gap-4 p-6 sm:grid-cols-2">
          <div v-if="formError" class="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 sm:col-span-2">{{ formError }}</div>
          <label class="text-sm font-medium text-gray-700">Organization name *
            <input v-model.trim="form.organization_name" required maxlength="150" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('organization_name')" class="mt-1 block text-xs text-red-600">{{ firstError('organization_name') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Organization code *
            <input v-model.trim="form.organization_code" required maxlength="20" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 uppercase outline-none focus:border-indigo-500" />
            <span v-if="firstError('organization_code')" class="mt-1 block text-xs text-red-600">{{ firstError('organization_code') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700 sm:col-span-2">Address
            <input v-model.trim="form.address" maxlength="255" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('address')" class="mt-1 block text-xs text-red-600">{{ firstError('address') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Contact email
            <input v-model.trim="form.contact_email" type="email" maxlength="100" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('contact_email')" class="mt-1 block text-xs text-red-600">{{ firstError('contact_email') }}</span>
          </label>
          <label class="text-sm font-medium text-gray-700">Contact number
            <input v-model.trim="form.contact_no" maxlength="20" inputmode="tel" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 outline-none focus:border-indigo-500" />
            <span v-if="firstError('contact_no')" class="mt-1 block text-xs text-red-600">{{ firstError('contact_no') }}</span>
          </label>
        </div>

        <div class="flex justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button type="button" class="rounded-xl border border-gray-300 px-5 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50" :disabled="saving" @click="closeForm">Cancel</button>
          <button type="submit" class="btn-primary" :disabled="saving">{{ saving ? 'Saving…' : (editingId ? 'Save Changes' : 'Create Organization') }}</button>
        </div>
      </form>
    </div>
  </AppLayout>
</template>
