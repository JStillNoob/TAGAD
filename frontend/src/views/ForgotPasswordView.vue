<template>
  <AuthShell accent="Secure account recovery" description="Request a time-limited link to choose a new password.">
      <div class="login-card">
        <div v-if="sent" role="status">
          <div class="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mb-5">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5" /></svg>
          </div>
          <h2 class="text-2xl font-bold text-navy">Check your email</h2>
          <p class="text-sm text-gray-500 mt-3 leading-relaxed">If an active account matches that email, a password reset link has been sent. In development, check the Django terminal for the email.</p>
          <RouterLink to="/" class="btn-primary w-full justify-center mt-7">Return to sign in</RouterLink>
        </div>

        <form v-else @submit.prevent="handleSubmit">
          <h2 class="text-2xl font-bold text-navy">Forgot your password?</h2>
          <p class="text-sm text-gray-400 mt-1 mb-7">Enter the email address connected to your account.</p>
          <label class="block text-sm font-semibold text-navy">Email address
            <input v-model.trim="email" type="email" autocomplete="email" required placeholder="teacher@university.edu" class="mt-2 w-full rounded-xl border border-gray-200 px-4 py-3 text-sm text-navy outline-none focus:border-brand">
          </label>
          <p v-if="error" class="mt-4 text-sm text-red-600" role="alert">{{ error }}</p>
          <button type="submit" class="btn-primary w-full justify-center mt-6 disabled:opacity-50" :disabled="submitting">{{ submitting ? 'Sending…' : 'Send reset link' }}</button>
          <div class="auth-footer-link text-center mt-5"><RouterLink to="/" class="text-sm font-medium text-brand">Back to sign in</RouterLink></div>
        </form>
      </div>
  </AuthShell>
</template>

<script setup>
import { ref } from 'vue'
import { requestPasswordReset } from '../passwordRecovery'
import AuthShell from '../components/AuthShell.vue'

const email = ref('')
const submitting = ref(false)
const sent = ref(false)
const error = ref('')

async function handleSubmit() {
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    await requestPasswordReset(email.value)
    sent.value = true
  } catch (requestError) {
    const fieldError = Object.values(requestError.fields || {}).flat()[0]
    error.value = fieldError || requestError.message || 'Unable to request a reset link.'
  } finally {
    submitting.value = false
  }
}
</script>
