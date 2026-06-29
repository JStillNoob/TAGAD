<template>
  <div class="min-h-screen grid md:grid-cols-2">

    <!-- Left panel -->
    <div class="hidden md:flex flex-col items-center justify-center text-center px-12"
      style="background: linear-gradient(135deg, #0f2440 0%, #1E3A5F 60%, #1a4a6e 100%);">
      <img src="/tagad_logo.png" alt="TAGAD Logo" class="w-64 mb-6 drop-shadow-xl" />
      <h1 class="text-4xl font-bold text-white tracking-widest mb-4">TAGAD</h1>
      <p class="text-xl font-medium mb-3" style="color:#7B92F5;">AI Classroom Monitoring System</p>
      <p class="text-sm leading-relaxed max-w-sm" style="color:rgba(255,255,255,0.5);">
        Real-time multimodal descriptive analytics for monitoring classroom engagement
      </p>
    </div>

    <!-- Right panel -->
    <div class="flex items-center justify-center px-6 py-12" style="background:#F5F7FA;">
      <div class="w-full max-w-md">
        <div class="bg-white rounded-2xl shadow-sm p-10">
          <div class="mb-8">
            <h2 class="text-2xl font-bold mb-1 text-navy">Welcome Back</h2>
            <p class="text-sm text-gray-400">Sign in to start monitoring your classroom</p>
          </div>

          <div class="mb-5">
            <label class="block text-sm font-semibold mb-2 text-navy">Email Address</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.25 6.75c0-.83.67-1.5 1.5-1.5h16.5c.83 0 1.5.67 1.5 1.5v10.5c0 .83-.67 1.5-1.5 1.5H3.75a1.5 1.5 0 0 1-1.5-1.5V6.75Z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="m3 7 7.5 6 7.5-6" />
                </svg>
              </span>
              <input v-model="email" type="email" placeholder="teacher@university.edu"
                class="w-full rounded-xl border pl-12 pr-4 py-3 text-sm outline-none transition-all text-navy"
                :style="emailFocused ? 'border-color:#465FF1; box-shadow:0 0 0 3px rgba(70,95,241,0.12)' : 'border-color:#e2e8f0'"
                @focus="emailFocused=true" @blur="emailFocused=false">
            </div>
          </div>

          <div class="mb-7">
            <label class="block text-sm font-semibold mb-2 text-navy">Password</label>
            <div class="relative">
              <span class="absolute inset-y-0 left-0 flex items-center pl-4 text-gray-400">
                <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 9.75h10.5a1.5 1.5 0 0 0 1.5-1.5v-6.75a1.5 1.5 0 0 0-1.5-1.5H6.75a1.5 1.5 0 0 0-1.5 1.5v6.75a1.5 1.5 0 0 0 1.5 1.5Z" />
                </svg>
              </span>
              <input v-model="password" type="password" placeholder="••••••••"
                class="w-full rounded-xl border pl-12 pr-4 py-3 text-sm outline-none transition-all text-navy"
                :style="passFocused ? 'border-color:#465FF1; box-shadow:0 0 0 3px rgba(70,95,241,0.12)' : 'border-color:#e2e8f0'"
                @focus="passFocused=true" @blur="passFocused=false">
            </div>
          </div>

          <RouterLink to="/dashboard" class="btn-primary w-full justify-center">
            Start Session
          </RouterLink>

          <div class="text-center mt-5">
            <a href="#" class="text-sm font-medium" style="color:#465FF1;">Forgot password?</a>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
const email = ref('')
const password = ref('')
const emailFocused = ref(false)
const passFocused = ref(false)
</script>
