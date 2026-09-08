<script setup>
import { currentTheme, toggleTheme } from '../theme'
</script>

<template>
  <button
    type="button"
    class="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500"
    :title="currentTheme === 'dark' ? 'Use light mode' : 'Use dark mode'"
    :aria-label="currentTheme === 'dark' ? 'Use light mode' : 'Use dark mode'"
    @click="toggleTheme"
  >
    <svg v-if="currentTheme === 'dark'" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M12 3v1.5m0 15V21m9-9h-1.5M4.5 12H3m15.364 6.364-1.061-1.061M6.697 6.697 5.636 5.636m12.728 0-1.061 1.061M6.697 17.303l-1.061 1.061M15.75 12a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0Z" /></svg>
    <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" /></svg>
  </button>
</template>
