<script setup>
import { onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { fetchGlobalSearch } from '../globalSearch'

const router = useRouter()
const route = useRoute()
const container = ref(null)
const input = ref(null)
const query = ref('')
const results = ref([])
const loading = ref(false)
const error = ref('')
const open = ref(false)
const activeIndex = ref(0)
let debounceTimer = null
let requestNumber = 0

const typeLabels = {
  user: 'User',
  classroom: 'Class',
  subject: 'Subject',
  session: 'Session',
  presentation: 'Presentation',
}

watch(query, (value) => {
  clearTimeout(debounceTimer)
  requestNumber += 1
  const trimmed = value.trim()
  results.value = []
  error.value = ''
  activeIndex.value = 0
  if (trimmed.length < 2) {
    loading.value = false
    return
  }
  const currentRequest = requestNumber
  loading.value = true
  debounceTimer = setTimeout(async () => {
    try {
      const response = await fetchGlobalSearch(trimmed)
      if (currentRequest === requestNumber) results.value = response.results
    } catch (requestError) {
      if (currentRequest === requestNumber) {
        error.value = requestError.message || 'Unable to search right now.'
      }
    } finally {
      if (currentRequest === requestNumber) loading.value = false
    }
  }, 250)
})

watch(() => route.fullPath, () => closeSearch())

function focusSearch() {
  open.value = true
  input.value?.focus()
}

function closeSearch() {
  open.value = false
  activeIndex.value = 0
}

async function chooseResult(result) {
  closeSearch()
  query.value = ''
  await router.push(result.url)
}

function handleInputKey(event) {
  if (event.key === 'Escape') {
    closeSearch()
    input.value?.blur()
  } else if (event.key === 'ArrowDown' && results.value.length) {
    event.preventDefault()
    activeIndex.value = (activeIndex.value + 1) % results.value.length
  } else if (event.key === 'ArrowUp' && results.value.length) {
    event.preventDefault()
    activeIndex.value = (activeIndex.value - 1 + results.value.length) % results.value.length
  } else if (event.key === 'Enter' && results.value[activeIndex.value]) {
    event.preventDefault()
    chooseResult(results.value[activeIndex.value])
  }
}

function handleGlobalKey(event) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
    event.preventDefault()
    focusSearch()
  }
}

function handleOutsidePointer(event) {
  if (container.value && !container.value.contains(event.target)) closeSearch()
}

onMounted(() => {
  document.addEventListener('keydown', handleGlobalKey)
  document.addEventListener('pointerdown', handleOutsidePointer)
})
onUnmounted(() => {
  clearTimeout(debounceTimer)
  document.removeEventListener('keydown', handleGlobalKey)
  document.removeEventListener('pointerdown', handleOutsidePointer)
})
</script>

<template>
  <div ref="container" class="relative flex-1 max-w-md">
    <div class="relative">
      <span class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
      </span>
      <label for="topbar-search" class="sr-only">Search users, classes, subjects, sessions, and presentations</label>
      <input
        id="topbar-search"
        ref="input"
        v-model="query"
        type="search"
        autocomplete="off"
        placeholder="Search users, classes, sessions…"
        class="w-full pl-9 pr-16 py-2 text-sm bg-gray-50 border border-gray-200 rounded-lg outline-none text-gray-600 placeholder-gray-400 focus:border-brand focus:bg-white transition-colors"
        role="combobox"
        :aria-expanded="open"
        aria-controls="global-search-results"
        @focus="open = true"
        @keydown="handleInputKey"
      >
      <div class="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none"><kbd class="text-[10px] text-gray-400 font-medium bg-gray-100 border border-gray-200 px-1.5 py-0.5 rounded">Ctrl K</kbd></div>
    </div>

    <div
      v-if="open && query.trim().length >= 2"
      id="global-search-results"
      class="absolute left-0 top-full z-50 mt-2 w-[440px] max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-gray-200 bg-white shadow-xl"
      role="listbox"
    >
      <div v-if="loading" class="px-4 py-7 text-center text-sm text-gray-400">Searching…</div>
      <div v-else-if="error" class="px-4 py-7 text-center text-sm text-red-600" role="alert">{{ error }}</div>
      <div v-else-if="!results.length" class="px-4 py-7 text-center"><p class="text-sm font-medium text-navy">No results found</p><p class="text-xs text-gray-400 mt-1">Try a name, code, room, or presentation title.</p></div>
      <div v-else class="max-h-96 overflow-y-auto p-2">
        <button
          v-for="(result, index) in results"
          :key="`${result.type}-${result.id}`"
          type="button"
          role="option"
          :aria-selected="index === activeIndex"
          class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition-colors"
          :class="index === activeIndex ? 'bg-brand-light' : 'hover:bg-gray-50'"
          @mouseenter="activeIndex = index"
          @mousedown.prevent="chooseResult(result)"
        >
          <span class="w-9 h-9 flex-shrink-0 rounded-lg bg-gray-100 text-brand flex items-center justify-center text-xs font-bold">{{ typeLabels[result.type].slice(0, 2).toUpperCase() }}</span>
          <span class="min-w-0 flex-1"><span class="block truncate text-sm font-medium text-navy">{{ result.title }}</span><span class="block truncate text-xs text-gray-400 mt-0.5">{{ result.subtitle }}</span></span>
          <span class="rounded-full border border-gray-200 px-2 py-0.5 text-[10px] font-medium text-gray-500">{{ typeLabels[result.type] }}</span>
        </button>
      </div>
    </div>
  </div>
</template>
