<script setup>
import { computed } from 'vue'
import { currentUser } from '../auth'
import ThemeToggle from '../components/ThemeToggle.vue'

const destination = computed(() => currentUser.value ? '/dashboard' : '/')
</script>

<template>
  <main class="auth-content min-h-screen flex items-center justify-center p-8">
    <ThemeToggle class="fixed right-5 top-5 z-20 bg-white shadow-sm" />
    <section class="page-card max-w-lg p-10 text-center">
      <p class="text-sm font-semibold uppercase tracking-widest text-brand">404</p>
      <h1 class="mt-3 text-3xl font-bold text-navy">Page not found</h1>
      <p class="mt-3 text-sm text-gray-500">The address may be incorrect, or the page may have moved.</p>
      <RouterLink :to="destination" class="btn-primary mt-7 justify-center">
        {{ currentUser ? 'Return to dashboard' : 'Return to sign in' }}
      </RouterLink>
    </section>
  </main>
</template>
