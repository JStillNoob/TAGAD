<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const props = defineProps({
  pageTitle: String,
  focusMode: { type: Boolean, default: false },
})

const route = useRoute()
const sidebarOpen = ref(true)

watch(() => props.focusMode, (val) => {
  // Collapse sidebar when session goes live; restore when it ends
  sidebarOpen.value = !val
})

const isActive = (path) => route.path === path
</script>

<template>
  <div class="min-h-screen flex bg-bg-main overflow-x-hidden">

    <!-- ── Sidebar (hidden in focus mode via transform) ── -->
    <aside
      class="fixed top-0 left-0 h-full w-64 flex flex-col z-30 bg-white border-r border-gray-200 transition-transform duration-500 ease-in-out"
      :class="sidebarOpen && !focusMode ? 'translate-x-0' : '-translate-x-full'">

      <!-- Logo -->
      <div class="flex items-center gap-3 px-5 h-16 border-b border-gray-100 flex-shrink-0">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0" style="background:#465FF1;">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M9.5 4.5c-1.7 0-3 1.3-3 3 0 .4.1.8.2 1.1C5.6 9 5 10 5 11.2c0 .9.4 1.7 1 2.3-.5.5-.8 1.2-.8 2 0 1.5 1.2 2.7 2.7 2.8.2 1.3 1.3 2.2 2.6 2.2.7 0 1.4-.3 1.9-.8.5.5 1.2.8 1.9.8 1.3 0 2.4-.9 2.6-2.2 1.5-.1 2.7-1.3 2.7-2.8 0-.8-.3-1.5-.8-2 .6-.6 1-1.4 1-2.3 0-1.2-.6-2.2-1.7-2.6.1-.3.2-.7.2-1.1 0-1.7-1.3-3-3-3-.6 0-1.2.2-1.7.5-.4-.9-1.3-1.5-2.3-1.5s-1.9.6-2.3 1.5c-.5-.3-1.1-.5-1.7-.5Z" />
          </svg>
        </div>
        <div>
          <div class="font-bold text-gray-900 text-base leading-none">TAGAD</div>
          <div class="text-gray-400 text-xs mt-0.5">AI Monitoring</div>
        </div>
      </div>

      <!-- Nav -->
      <nav class="flex-1 px-4 py-5 overflow-y-auto space-y-0.5">
        <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest px-2 mb-3">MENU</p>

        <RouterLink to="/dashboard" :class="['nav-link', isActive('/dashboard') ? 'active' : '']">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
          </svg>
          Dashboard
        </RouterLink>

        <RouterLink to="/session" :class="['nav-link', isActive('/session') ? 'active' : '']">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 10.5l4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
          Live Session
        </RouterLink>

        <RouterLink to="/analytics" :class="['nav-link', isActive('/analytics') ? 'active' : '']">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
          </svg>
          Analytics
        </RouterLink>

        <RouterLink to="/students" :class="['nav-link', isActive('/students') ? 'active' : '']">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
            <path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
          </svg>
          Classes
        </RouterLink>

        <div class="pt-4 mt-3 border-t border-gray-100 space-y-0.5">
          <p class="text-xs font-semibold text-gray-400 uppercase tracking-widest px-2 mb-3">OTHERS</p>
          <a href="#" class="nav-link">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.325.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.241-.438.613-.43.992a7.723 7.723 0 0 1 0 .255c-.008.378.137.75.43.991l1.004.827c.424.35.534.955.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.47 6.47 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.281c-.09.543-.56.94-1.11.94h-2.594c-.55 0-1.019-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.991a6.932 6.932 0 0 1 0-.255c.007-.38-.138-.751-.43-.992l-1.004-.827a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.086.22-.128.332-.183.582-.495.644-.869l.214-1.28Z" />
              <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
            </svg>
            Settings
          </a>
        </div>
      </nav>
    </aside>

    <!-- ── Main area ── -->
    <div
      class="flex-1 flex flex-col min-h-screen transition-all duration-500 ease-in-out"
      :class="sidebarOpen && !focusMode ? 'ml-64' : 'ml-0'">

      <!-- Topbar — slides up and out in focus mode -->
      <header
        class="bg-white border-b border-gray-200 flex items-center px-6 gap-4 sticky top-0 z-20 flex-shrink-0 overflow-hidden transition-all duration-500 ease-in-out"
        :class="focusMode ? 'h-0 opacity-0 border-0 pointer-events-none' : 'h-16 opacity-100'">

        <!-- Hamburger -->
        <button
          class="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-gray-500 flex-shrink-0"
          @click="sidebarOpen = !sidebarOpen"
          :title="sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'">
          <svg v-if="!sidebarOpen" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
          </svg>
        </button>

        <!-- Search -->
        <div class="flex-1 max-w-xs">
          <div class="relative">
            <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
              </svg>
            </span>
            <label for="topbar-search" class="sr-only">Search</label>
            <input id="topbar-search" type="text" placeholder="Search or type command..."
              class="w-full pl-9 pr-12 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg outline-none text-gray-600 placeholder-gray-400 focus:border-brand focus:bg-white transition-colors">
            <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
              <kbd class="text-xs text-gray-400 font-medium bg-gray-100 border border-gray-200 px-1.5 py-0.5 rounded">⌘K</kbd>
            </div>
          </div>
        </div>

        <div class="flex-1"></div>

        <!-- Right actions -->
        <div class="flex items-center gap-1">
          <button class="p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M21.752 15.002A9.72 9.72 0 0 1 18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998Z" />
            </svg>
          </button>

          <button class="relative p-2 rounded-lg hover:bg-gray-100 transition-colors text-gray-500">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
              <path stroke-linecap="round" stroke-linejoin="round" d="M14.857 17.082a23.848 23.848 0 0 0 5.454-1.31A8.967 8.967 0 0 1 18 9.75V9A6 6 0 0 0 6 9v.75a8.967 8.967 0 0 1-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 0 1-5.714 0m5.714 0a3 3 0 1 1-5.714 0" />
            </svg>
            <span class="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-danger"></span>
          </button>

          <div class="w-px h-6 bg-gray-200 mx-2"></div>

          <div class="flex items-center gap-2.5 cursor-pointer">
            <div class="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-bold flex-shrink-0" style="background:#465FF1;">RS</div>
            <div class="hidden md:block">
              <div class="text-sm font-semibold text-gray-800 leading-none">Dr. Santos</div>
              <div class="text-xs text-gray-400 mt-0.5">Admin</div>
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
            </svg>
          </div>
        </div>
      </header>

      <!-- Page content — no padding in focus mode so session fills the screen -->
      <main :class="focusMode ? 'flex-1 bg-bg-main p-6 lg:p-8 flex flex-col' : 'flex-1 p-6 lg:p-8 bg-bg-main'">
        <slot />
      </main>
    </div>
  </div>
</template>
