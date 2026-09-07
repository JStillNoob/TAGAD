<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import AppLayout from '../layouts/AppLayout.vue'
import { fetchCurrentUser } from '../auth'
import { changePassword, fetchSettings, updateOrganization, updateProfile } from '../settings'

const loading = ref(true)
const loadError = ref('')
const user = ref(null)
const organization = ref(null)
const canEditOrganization = ref(false)
const editingProfile = ref(false)
const editingOrganization = ref(false)
const profilePending = ref(false)
const organizationPending = ref(false)
const passwordPending = ref(false)
const profileMessage = ref('')
const organizationMessage = ref('')
const passwordMessage = ref('')
const profileErrors = ref({})
const organizationErrors = ref({})
const passwordErrors = ref({})

const profileForm = reactive({ first_name: '', middle_name: '', last_name: '', email: '', contact_no: '' })
const organizationForm = reactive({ address: '', contact_email: '', contact_no: '' })
const passwordForm = reactive({ current_password: '', new_password: '', password_confirmation: '' })

const displayName = computed(() => {
  if (!user.value) return 'User'
  return [user.value.first_name, user.value.last_name].filter(Boolean).join(' ') || user.value.username
})
const initials = computed(() => displayName.value.split(' ').map(part => part[0]).join('').slice(0, 2).toUpperCase())
const passwordChecks = computed(() => {
  const password = passwordForm.new_password
  return [
    { label: 'At least 12 characters', met: password.length >= 12 },
    { label: 'One uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'One lowercase letter', met: /[a-z]/.test(password) },
    { label: 'One number', met: /[0-9]/.test(password) },
    { label: 'One symbol', met: /[^A-Za-z0-9]/.test(password) },
    { label: 'Passwords match', met: Boolean(password) && password === passwordForm.password_confirmation },
  ]
})
const passwordReady = computed(() => Boolean(passwordForm.current_password) && passwordChecks.value.every(check => check.met))

function firstError(errors, field) {
  const value = errors.value?.[field]
  return Array.isArray(value) ? value[0] : value || ''
}

function fillProfileForm() {
  if (!user.value) return
  for (const field of Object.keys(profileForm)) profileForm[field] = user.value[field] || ''
}

function fillOrganizationForm() {
  if (!organization.value) return
  for (const field of Object.keys(organizationForm)) organizationForm[field] = organization.value[field] || ''
}

function formatDate(value) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value)) : '—'
}

async function loadSettings() {
  loading.value = true
  loadError.value = ''
  try {
    const response = await fetchSettings()
    user.value = response.user
    organization.value = response.organization
    canEditOrganization.value = response.can_edit_organization
    fillProfileForm()
    fillOrganizationForm()
  } catch (error) {
    loadError.value = error.message || 'Unable to load settings.'
  } finally {
    loading.value = false
  }
}

function cancelProfile() {
  fillProfileForm()
  profileErrors.value = {}
  profileMessage.value = ''
  editingProfile.value = false
}

async function saveProfile() {
  profilePending.value = true
  profileErrors.value = {}
  profileMessage.value = ''
  try {
    user.value = await updateProfile(profileForm)
    await fetchCurrentUser({ force: true })
    profileMessage.value = 'Profile updated successfully.'
    editingProfile.value = false
  } catch (error) {
    profileErrors.value = error.fields || {}
  } finally {
    profilePending.value = false
  }
}

function cancelOrganization() {
  fillOrganizationForm()
  organizationErrors.value = {}
  organizationMessage.value = ''
  editingOrganization.value = false
}

async function saveOrganization() {
  organizationPending.value = true
  organizationErrors.value = {}
  organizationMessage.value = ''
  try {
    organization.value = await updateOrganization(organizationForm)
    organizationMessage.value = 'Organization details updated successfully.'
    editingOrganization.value = false
  } catch (error) {
    organizationErrors.value = error.fields || {}
  } finally {
    organizationPending.value = false
  }
}

async function savePassword() {
  passwordPending.value = true
  passwordErrors.value = {}
  passwordMessage.value = ''
  try {
    await changePassword(passwordForm)
    passwordForm.current_password = ''
    passwordForm.new_password = ''
    passwordForm.password_confirmation = ''
    passwordMessage.value = 'Password changed successfully. You remain signed in.'
  } catch (error) {
    passwordErrors.value = error.fields || {}
  } finally {
    passwordPending.value = false
  }
}

onMounted(loadSettings)
</script>

<template>
  <AppLayout page-title="Settings">
    <div v-if="loading" class="page-card p-10 text-center text-sm text-gray-400">Loading settings…</div>
    <div v-else-if="loadError" class="page-card p-10 text-center">
      <p class="text-sm text-red-600">{{ loadError }}</p>
      <button class="mt-4 px-4 py-2 rounded-lg bg-brand text-white text-sm" @click="loadSettings">Try again</button>
    </div>

    <div v-else class="space-y-6">
      <div class="grid grid-cols-1 xl:grid-cols-2 gap-6">
        <section class="page-card p-6">
          <div class="flex items-center justify-between gap-3 mb-5">
            <div>
              <h3 class="text-sm font-semibold text-navy">User Profile</h3>
              <p class="text-xs text-gray-400 mt-1">Your personal account information</p>
            </div>
            <button v-if="!editingProfile" class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-brand hover:bg-brand-light" @click="editingProfile = true; profileMessage = ''">Edit profile</button>
          </div>

          <div class="flex items-center gap-3 mb-5">
            <div class="w-12 h-12 rounded-full flex items-center justify-center text-white text-sm font-bold bg-brand">{{ initials }}</div>
            <div>
              <p class="text-sm font-semibold text-navy">{{ displayName }}</p>
              <p class="text-xs text-gray-400">{{ user.role_label }} · @{{ user.username }}</p>
            </div>
            <span class="badge-engaged ml-auto">{{ user.status_label }}</span>
          </div>

          <form class="grid grid-cols-1 sm:grid-cols-2 gap-4" @submit.prevent="saveProfile">
            <label v-for="field in [
              ['first_name', 'First name'], ['middle_name', 'Middle name'], ['last_name', 'Last name'],
              ['email', 'Email address'], ['contact_no', 'Contact number'],
            ]" :key="field[0]" class="text-xs font-medium text-gray-600" :class="field[0] === 'email' ? 'sm:col-span-2' : ''">
              {{ field[1] }}
              <input v-model.trim="profileForm[field[0]]" :type="field[0] === 'email' ? 'email' : 'text'" :disabled="!editingProfile" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm disabled:bg-gray-50 disabled:text-gray-500 outline-none focus:border-brand">
              <span v-if="firstError(profileErrors, field[0])" class="block mt-1 text-xs text-red-600">{{ firstError(profileErrors, field[0]) }}</span>
            </label>
            <div v-if="editingProfile" class="sm:col-span-2 flex justify-end gap-2 pt-2">
              <button type="button" class="px-4 py-2 rounded-lg border border-gray-200 text-sm" :disabled="profilePending" @click="cancelProfile">Cancel</button>
              <button type="submit" class="px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium disabled:opacity-50" :disabled="profilePending">{{ profilePending ? 'Saving…' : 'Save profile' }}</button>
            </div>
          </form>
          <p v-if="profileMessage" class="mt-4 text-sm text-emerald-600" role="status">{{ profileMessage }}</p>
        </section>

        <section class="page-card p-6">
          <div class="flex items-center justify-between gap-3 mb-5">
            <div>
              <h3 class="text-sm font-semibold text-navy">Organization Profile</h3>
              <p class="text-xs text-gray-400 mt-1">Organization identity and contact details</p>
            </div>
            <button v-if="organization && canEditOrganization && !editingOrganization" class="px-3 py-1.5 rounded-lg border border-gray-200 text-sm text-brand hover:bg-brand-light" @click="editingOrganization = true; organizationMessage = ''">Edit organization</button>
          </div>

          <div v-if="!organization" class="py-14 text-center text-sm text-gray-400">No organization assigned to this account.</div>
          <template v-else>
            <div class="flex items-center justify-between gap-3 mb-5">
              <div>
                <p class="text-sm font-semibold text-navy">{{ organization.organization_name }}</p>
                <p class="text-xs text-gray-400 mt-1">{{ organization.organization_code }} · Registered {{ formatDate(organization.created_at) }}</p>
              </div>
              <span class="badge-engaged">{{ organization.status_label }}</span>
            </div>
            <form class="space-y-4" @submit.prevent="saveOrganization">
              <label v-for="field in [['address', 'Address'], ['contact_email', 'Contact email'], ['contact_no', 'Contact number']]" :key="field[0]" class="block text-xs font-medium text-gray-600">
                {{ field[1] }}
                <input v-model.trim="organizationForm[field[0]]" :type="field[0] === 'contact_email' ? 'email' : 'text'" :disabled="!editingOrganization" class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm disabled:bg-gray-50 disabled:text-gray-500 outline-none focus:border-brand">
                <span v-if="firstError(organizationErrors, field[0])" class="block mt-1 text-xs text-red-600">{{ firstError(organizationErrors, field[0]) }}</span>
              </label>
              <p v-if="!canEditOrganization" class="text-xs text-gray-400">Only an organization administrator can edit these details.</p>
              <div v-if="editingOrganization" class="flex justify-end gap-2 pt-2">
                <button type="button" class="px-4 py-2 rounded-lg border border-gray-200 text-sm" :disabled="organizationPending" @click="cancelOrganization">Cancel</button>
                <button type="submit" class="px-4 py-2 rounded-lg bg-brand text-white text-sm font-medium disabled:opacity-50" :disabled="organizationPending">{{ organizationPending ? 'Saving…' : 'Save organization' }}</button>
              </div>
            </form>
            <p v-if="organizationMessage" class="mt-4 text-sm text-emerald-600" role="status">{{ organizationMessage }}</p>
          </template>
        </section>
      </div>

      <section class="page-card p-6">
        <div class="mb-5">
          <h3 class="text-sm font-semibold text-navy">Change Password</h3>
          <p class="text-xs text-gray-400 mt-1">Confirm your current password and meet every requirement below</p>
        </div>
        <form class="grid grid-cols-1 lg:grid-cols-2 gap-6" @submit.prevent="savePassword">
          <div class="space-y-4">
            <label class="block text-xs font-medium text-gray-600">Current password
              <input v-model="passwordForm.current_password" type="password" autocomplete="current-password" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-brand">
              <span v-if="firstError(passwordErrors, 'current_password')" class="block mt-1 text-xs text-red-600">{{ firstError(passwordErrors, 'current_password') }}</span>
            </label>
            <label class="block text-xs font-medium text-gray-600">New password
              <input v-model="passwordForm.new_password" type="password" autocomplete="new-password" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-brand">
              <span v-if="firstError(passwordErrors, 'new_password')" class="block mt-1 text-xs text-red-600">{{ firstError(passwordErrors, 'new_password') }}</span>
            </label>
            <label class="block text-xs font-medium text-gray-600">Confirm new password
              <input v-model="passwordForm.password_confirmation" type="password" autocomplete="new-password" required class="mt-1.5 w-full rounded-lg border border-gray-300 px-3 py-2.5 text-sm outline-none focus:border-brand">
              <span v-if="firstError(passwordErrors, 'password_confirmation')" class="block mt-1 text-xs text-red-600">{{ firstError(passwordErrors, 'password_confirmation') }}</span>
            </label>
          </div>

          <div class="rounded-xl bg-gray-50 p-5">
            <p class="text-xs font-semibold text-gray-700 mb-3">Password requirements</p>
            <ul class="space-y-2">
              <li v-for="check in passwordChecks" :key="check.label" class="flex items-center gap-2 text-sm" :class="check.met ? 'text-emerald-600' : 'text-gray-400'">
                <span class="w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold" :class="check.met ? 'bg-emerald-100' : 'bg-gray-200'">{{ check.met ? '✓' : '·' }}</span>
                {{ check.label }}
              </li>
            </ul>
            <p class="mt-3 text-xs text-gray-400">Django will also reject common passwords or passwords too similar to your personal details.</p>
            <button type="submit" class="mt-5 w-full px-4 py-2.5 rounded-lg bg-brand text-white text-sm font-medium disabled:opacity-50" :disabled="passwordPending || !passwordReady">{{ passwordPending ? 'Changing…' : 'Change password' }}</button>
            <p v-if="passwordMessage" class="mt-3 text-sm text-emerald-600" role="status">{{ passwordMessage }}</p>
          </div>
        </form>
      </section>
    </div>
  </AppLayout>
</template>
