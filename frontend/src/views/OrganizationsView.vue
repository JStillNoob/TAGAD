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
    <div class="mx-auto max-w-7xl space-y-6">
      <div class="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">Organizations</h1>
          <p class="mt-1 text-sm text-gray-500">Manage every institution using TAGAD.</p>
        </div>
        <button type="button" class="btn-primary justify-center" @click="openCreate">
          <span class="text-lg leading-none">+</span> Add Organization
        </button>
      </div>

      <p v-if="pageError" class="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700" role="alert">{{ pageError }}</p>
      <p v-if="success" class="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700" role="status">{{ success }}</p>

      <section class="page-card overflow-hidden">
        <div class="grid gap-3 border-b border-gray-200 p-5 md:grid-cols-[1fr_180px] md:items-end">
          <label class="text-xs font-semibold text-gray-600">Search
            <input v-model="search" type="search" placeholder="Name or organization code…" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2 text-sm font-normal outline-none focus:border-indigo-500" />
          </label>
          <label class="text-xs font-semibold text-gray-600">Records
            <select v-model="lifecycle" class="mt-1.5 w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm font-normal">
              <option value="active">Active</option>
              <option value="archived">Archived</option>
              <option value="all">All</option>
            </select>
          </label>
        </div>

        <div v-if="loading" class="p-10 text-center text-sm text-gray-500">Loading organizations…</div>
        <div v-else-if="!organizations.length" class="p-10 text-center text-sm text-gray-500">No organizations match these filters.</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full min-w-[780px] text-left text-sm">
            <thead class="bg-gray-50 text-xs uppercase tracking-wide text-gray-500">
              <tr>
                <th class="px-5 py-3 font-semibold">Organization</th>
                <th class="px-5 py-3 font-semibold">Contact</th>
                <th class="px-5 py-3 font-semibold">Status</th>
                <th class="px-5 py-3 text-right font-semibold">Actions</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-100">
              <tr v-for="organization in organizations" :key="organization.id" class="hover:bg-gray-50">
                <td class="px-5 py-4">
                  <p class="font-semibold text-gray-900">{{ organization.organization_name }}</p>
                  <p class="mt-0.5 text-xs text-gray-500">{{ organization.organization_code }}<template v-if="organization.address"> · {{ organization.address }}</template></p>
                </td>
                <td class="px-5 py-4 text-gray-600">
                  <p>{{ organization.contact_email || 'No email set' }}</p>
                  <p class="mt-0.5 text-xs text-gray-400">{{ organization.contact_no || 'No contact number' }}</p>
                </td>
                <td class="px-5 py-4">
                  <span class="rounded-full px-2.5 py-1 text-xs font-semibold" :class="organization.is_archived ? 'bg-gray-100 text-gray-600' : 'bg-emerald-50 text-emerald-700'">
                    {{ organization.is_archived ? 'Archived' : 'Active' }}
                  </span>
                </td>
                <td class="px-5 py-4">
                  <div class="flex justify-end gap-2">
                    <button v-if="!organization.is_archived" type="button" class="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-gray-700 hover:bg-gray-50" @click="openEdit(organization)">Edit</button>
                    <button v-if="!organization.is_archived" type="button" class="rounded-lg border border-amber-200 px-3 py-1.5 text-xs font-semibold text-amber-700 hover:bg-amber-50" @click="archiveRecord(organization)">Archive</button>
                    <button v-else type="button" class="rounded-lg border border-emerald-200 px-3 py-1.5 text-xs font-semibold text-emerald-700 hover:bg-emerald-50" @click="restoreRecord(organization)">Restore</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <PaginationControls :page="page" :count="organizationCount" :page-size="pageSize" :disabled="loading" @change="loadOrganizations" />
      </section>
    </div>

    <div v-if="showForm" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-4" @click.self="closeForm">
      <form role="dialog" aria-labelledby="organization-form-title" class="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white shadow-xl" @submit.prevent="saveOrganization">
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
