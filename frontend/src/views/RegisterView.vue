<template>
  <div class="min-h-screen grid md:grid-cols-2">
    <div
      class="hidden md:flex flex-col items-center justify-center text-center px-12"
      style="background: linear-gradient(135deg, #0f2440 0%, #1E3A5F 60%, #1a4a6e 100%);"
    >
      <img src="/tagad_logo.png" alt="TAGAD Logo" class="w-64 mb-6 drop-shadow-xl" />
      <h1 class="text-4xl font-bold text-white tracking-widest mb-4">TAGAD</h1>
      <p class="text-xl font-medium mb-3" style="color:#7B92F5;">Create your teacher account</p>
      <p class="text-sm leading-relaxed max-w-sm" style="color:rgba(255,255,255,0.5);">
        Join your organization using the code provided by your administrator.
      </p>
    </div>

    <div class="flex items-center justify-center px-6 py-10" style="background:#F5F7FA;">
      <div class="w-full max-w-xl">
        <form class="bg-white rounded-2xl shadow-sm p-8" @submit.prevent="handleSubmit">
          <div class="mb-6">
            <h2 class="text-2xl font-bold mb-1 text-navy">Create Account</h2>
            <p class="text-sm text-gray-400">All fields are required.</p>
          </div>

          <div class="grid sm:grid-cols-2 gap-4">
            <FormField v-model="form.first_name" label="First Name" name="first_name" autocomplete="given-name" :error="errorFor('first_name')" />
            <FormField v-model="form.last_name" label="Last Name" name="last_name" autocomplete="family-name" :error="errorFor('last_name')" />
            <FormField v-model="form.username" label="Username" name="username" autocomplete="username" :error="errorFor('username')" />
            <FormField v-model="form.email" label="Email Address" name="email" type="email" autocomplete="email" :error="errorFor('email')" />
          </div>

          <div class="mt-4">
            <FormField v-model="form.organization_code" label="Organization Code" name="organization_code" autocomplete="off" :error="errorFor('organization_code')" />
          </div>

          <div class="grid sm:grid-cols-2 gap-4 mt-4">
            <FormField v-model="form.password" label="Password" name="password" type="password" autocomplete="new-password" :error="errorFor('password')" />
            <FormField v-model="form.password_confirmation" label="Confirm Password" name="password_confirmation" type="password" autocomplete="new-password" :error="errorFor('password_confirmation')" />
          </div>
          <p class="mt-2 text-xs text-gray-400">
            Use at least 12 characters. Avoid common, numeric-only, or personal passwords.
          </p>

          <p v-if="errorMessage" class="mt-4 text-sm text-red-600" role="alert">
            {{ errorMessage }}
          </p>

          <button type="submit" class="btn-primary w-full justify-center mt-6" :disabled="submitting">
            {{ submitting ? 'Creating account…' : 'Create Account' }}
          </button>

          <div class="text-center mt-5 text-sm text-gray-500">
            Already have an account?
            <RouterLink to="/" class="font-medium" style="color:#465FF1;">Sign in</RouterLink>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import FormField from '../components/FormField.vue'
import { register } from '../auth'

const router = useRouter()
const form = reactive({
  first_name: '',
  last_name: '',
  username: '',
  email: '',
  organization_code: '',
  password: '',
  password_confirmation: '',
})
const submitting = ref(false)
const errorMessage = ref('')
const fieldErrors = ref({})

function errorFor(field) {
  const error = fieldErrors.value[field]
  return Array.isArray(error) ? error.join(' ') : error || ''
}

async function handleSubmit() {
  submitting.value = true
  errorMessage.value = ''
  fieldErrors.value = {}
  try {
    await register(form)
    await router.replace({ path: '/', query: { registered: '1' } })
  } catch (error) {
    fieldErrors.value = error.fields || {}
    errorMessage.value = error.message
  } finally {
    submitting.value = false
  }
}
</script>
