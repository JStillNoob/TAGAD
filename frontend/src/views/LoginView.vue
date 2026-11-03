<template>
  <div class="login-page">
    <ThemeToggle class="login-theme-toggle" />
    <div class="login-frame">
      <section class="login-brand-panel" aria-labelledby="login-brand-title">
        <div class="login-brand-content">
          <img src="/illustrations/login-classroom.svg" alt="" aria-hidden="true" class="login-illustration">
          <h1 id="login-brand-title" class="login-brand-title">TAGAD</h1>
          <p class="login-brand-accent">AI Classroom Monitoring System</p>
          <p class="login-brand-copy">Real-time multimodal descriptive analytics for monitoring classroom engagement.</p>
          <div class="login-brand-dots" aria-hidden="true"><span></span><span></span><span></span></div>
        </div>
      </section>

      <main class="auth-content login-content">
        <div class="login-card-wrap">
          <div class="login-logo-lockup"><img src="/tagad_logo.svg" alt=""><span>TAGAD</span></div>
          <form class="login-card" @submit.prevent="handleSubmit">
            <div class="login-card-heading">
              <h2>Welcome Back</h2>
              <p>Sign in to start monitoring your classroom.</p>
            </div>

            <p v-if="route.query.registered === '1'" class="mb-5 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700" role="status">
              Account created successfully. You can sign in now.
            </p>
            <p v-if="route.query.reset === '1'" class="mb-5 rounded-lg bg-green-50 px-4 py-3 text-sm text-green-700" role="status">
              Password reset successfully. Sign in with your new password.
            </p>

            <div class="login-field">
              <label for="login-identity">Email or Username</label>
              <div class="login-input-wrap">
                <span class="login-field-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="2.5" y="5" width="19" height="14" rx="2" /><path d="m3 7 9 7 9-7" /></svg></span>
                <input id="login-identity" v-model="identity" class="login-input" type="text" placeholder="teacher@university.edu" autocomplete="username" required>
              </div>
            </div>

            <div class="login-field login-password-field">
              <label for="login-password">Password</label>
              <div class="login-input-wrap">
                <span class="login-field-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 1 1 8 0v3" /></svg></span>
                <input id="login-password" v-model="password" class="login-input login-password-input" :type="showPassword ? 'text' : 'password'" placeholder="••••••••" autocomplete="current-password" required>
                <button type="button" class="login-password-toggle" :aria-label="showPassword ? 'Hide password' : 'Show password'" :aria-pressed="showPassword" @click="showPassword = !showPassword">
                  <svg v-if="showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></svg>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 3 21 21M9.9 5.2A11.7 11.7 0 0 1 12 5c6.5 0 10 7 10 7a14 14 0 0 1-3.1 3.7M6.2 6.2C3.5 8.1 2 12 2 12s3.5 7 10 7c1.6 0 3-.4 4.2-1" /><path d="M10 10a3 3 0 0 0 4 4" /></svg>
                </button>
              </div>
            </div>

            <p v-if="errorMessage" class="mb-4 text-sm text-red-600" role="alert">{{ errorMessage }}</p>
            <button type="submit" class="btn-primary login-submit" :disabled="submitting">{{ submitting ? 'Signing in…' : 'Start Session' }}</button>
            <div class="login-support-link"><RouterLink to="/forgot-password">Forgot password?</RouterLink></div>
            <div class="login-register-link">Need an account? <RouterLink to="/register">Register</RouterLink></div>
          </form>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { login } from '../auth'
import ThemeToggle from '../components/ThemeToggle.vue'

const route = useRoute()
const router = useRouter()
const identity = ref('')
const password = ref('')
const showPassword = ref(false)
const submitting = ref(false)
const errorMessage = ref('')

async function handleSubmit() {
  if (submitting.value) return
  submitting.value = true
  errorMessage.value = ''
  try {
    await login(identity.value, password.value)
    const requestedPath = route.query.redirect
    const destination = typeof requestedPath === 'string'
      && requestedPath.startsWith('/')
      && !requestedPath.startsWith('//')
      ? requestedPath
      : '/dashboard'
    await router.replace(destination)
  } catch (error) {
    errorMessage.value = error.message
  } finally {
    submitting.value = false
  }
}
</script>
