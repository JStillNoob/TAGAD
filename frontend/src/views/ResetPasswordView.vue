<template>
  <div class="min-h-screen grid md:grid-cols-2">
    <ThemeToggle class="fixed right-5 top-5 z-20 bg-white shadow-sm" />
    <div class="hidden md:flex flex-col items-center justify-center text-center px-12" style="background:linear-gradient(135deg,#0f2440 0%,#1E3A5F 60%,#1a4a6e 100%);">
      <img src="/tagad_logo.png" alt="TAGAD Logo" class="w-64 mb-6 drop-shadow-xl">
      <h1 class="text-4xl font-bold text-white tracking-widest mb-4">TAGAD</h1>
      <p class="text-xl font-medium mb-3" style="color:#7B92F5">Choose a secure password</p>
      <p class="text-sm leading-relaxed max-w-sm" style="color:rgba(255,255,255,.5)">Complete every requirement to protect your account.</p>
    </div>

    <div class="auth-content flex items-center justify-center px-6 py-10">
      <div class="w-full max-w-md bg-white rounded-2xl shadow-sm p-9">
        <div v-if="checking" class="py-12 text-center text-sm text-gray-400">Checking reset link…</div>
        <div v-else-if="invalid" class="text-center py-5">
          <div class="w-12 h-12 mx-auto rounded-full bg-red-50 text-red-600 flex items-center justify-center mb-5">!</div>
          <h2 class="text-2xl font-bold text-navy">Reset link unavailable</h2>
          <p class="text-sm text-gray-500 mt-3">{{ error }}</p>
          <RouterLink to="/forgot-password" class="btn-primary w-full justify-center mt-7">Request a new link</RouterLink>
        </div>

        <form v-else @submit.prevent="handleSubmit">
          <h2 class="text-2xl font-bold text-navy">Reset password</h2>
          <p class="text-sm text-gray-400 mt-1 mb-6">Enter and confirm your new password.</p>
          <div class="space-y-4">
            <label class="block text-sm font-semibold text-navy">New password
              <input v-model="form.new_password" type="password" autocomplete="new-password" required class="mt-2 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-navy outline-none focus:border-brand">
            </label>
            <label class="block text-sm font-semibold text-navy">Confirm new password
              <input v-model="form.password_confirmation" type="password" autocomplete="new-password" required class="mt-2 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-navy outline-none focus:border-brand">
            </label>
          </div>

          <div class="rounded-xl bg-gray-50 p-4 mt-5">
            <p class="text-xs font-semibold text-gray-700 mb-3">Password requirements</p>
            <ul class="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <li v-for="check in passwordChecks" :key="check.label" class="flex items-center gap-2 text-xs" :class="check.met ? 'text-emerald-600' : 'text-gray-400'">
                <span class="w-4 h-4 rounded-full flex items-center justify-center text-[10px]" :class="check.met ? 'bg-emerald-100' : 'bg-gray-200'">{{ check.met ? '✓' : '·' }}</span>{{ check.label }}
              </li>
            </ul>
            <p class="text-xs text-gray-400 mt-3">Django will also reject common passwords or passwords too similar to your personal details.</p>
          </div>

          <p v-if="error" class="mt-4 text-sm text-red-600" role="alert">{{ error }}</p>
          <button type="submit" class="btn-primary w-full justify-center mt-6 disabled:opacity-50" :disabled="submitting || !passwordReady">{{ submitting ? 'Resetting…' : 'Reset password' }}</button>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { confirmPasswordReset, validatePasswordReset } from '../passwordRecovery'
import ThemeToggle from '../components/ThemeToggle.vue'

const route = useRoute()
const router = useRouter()
const checking = ref(true)
const invalid = ref(false)
const submitting = ref(false)
const error = ref('')
const form = reactive({ new_password: '', password_confirmation: '' })

const passwordChecks = computed(() => {
  const password = form.new_password
  return [
    { label: 'At least 12 characters', met: password.length >= 12 },
    { label: 'One uppercase letter', met: /[A-Z]/.test(password) },
    { label: 'One lowercase letter', met: /[a-z]/.test(password) },
    { label: 'One number', met: /[0-9]/.test(password) },
    { label: 'One symbol', met: /[^A-Za-z0-9]/.test(password) },
    { label: 'Passwords match', met: Boolean(password) && password === form.password_confirmation },
  ]
})
const passwordReady = computed(() => passwordChecks.value.every(check => check.met))

function tokenData() {
  return { uid: route.params.uid, token: route.params.token }
}

function requestErrorMessage(requestError) {
  const fieldError = Object.values(requestError.fields || {}).flat()[0]
  return fieldError || requestError.message || 'Unable to reset the password.'
}

async function checkToken() {
  try {
    await validatePasswordReset(route.params.uid, route.params.token)
  } catch (requestError) {
    invalid.value = true
    error.value = requestErrorMessage(requestError)
  } finally {
    checking.value = false
  }
}

async function handleSubmit() {
  submitting.value = true
  error.value = ''
  try {
    await confirmPasswordReset({ ...tokenData(), ...form })
    await router.replace({ path: '/', query: { reset: '1' } })
  } catch (requestError) {
    error.value = requestErrorMessage(requestError)
    if (requestError.status === 400 && requestError.fields?.detail) invalid.value = true
  } finally {
    submitting.value = false
  }
}

onMounted(checkToken)
</script>
