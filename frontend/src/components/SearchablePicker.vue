<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  loader: { type: Function, required: true },
  placeholder: { type: String, default: 'Select an option' },
  selectLabel: { type: String, default: 'Options' },
  searchLabel: { type: String, default: 'Search options' },
  searchPlaceholder: { type: String, default: 'Search…' },
  required: Boolean,
  disabled: Boolean,
  refreshKey: { type: [String, Number, Boolean], default: '' },
})

const emit = defineEmits(['update:modelValue', 'selected'])
const options = ref([])
const selectedOption = ref(null)
const search = ref('')
const page = ref(1)
const count = ref(0)
const loading = ref(false)
const error = ref('')
const pageSize = 20
let searchTimer = null
let requestNumber = 0

const pages = computed(() => Math.max(1, Math.ceil(count.value / pageSize)))
const displayedOptions = computed(() => {
  if (!selectedOption.value || options.value.some((item) => item.id === selectedOption.value.id)) {
    return options.value
  }
  return [selectedOption.value, ...options.value]
})

async function loadOptions() {
  const currentRequest = ++requestNumber
  loading.value = true
  error.value = ''
  try {
    const response = await props.loader({
      page: page.value,
      search: search.value.trim(),
      selected: search.value.trim() ? '' : props.modelValue,
    })
    if (currentRequest !== requestNumber) return
    options.value = response.results
    count.value = response.count
    const match = response.results.find((item) => item.id === Number(props.modelValue))
    if (match) {
      selectedOption.value = match
      emit('selected', match)
    }
  } catch (requestError) {
    if (currentRequest === requestNumber) error.value = requestError.message
  } finally {
    if (currentRequest === requestNumber) loading.value = false
  }
}

function choose(event) {
  const value = event.target.value
  const normalized = value === '' ? '' : Number(value)
  emit('update:modelValue', normalized)
  const match = displayedOptions.value.find((item) => item.id === normalized) || null
  selectedOption.value = match
  emit('selected', match)
}

function changePage(nextPage) {
  page.value = nextPage
  loadOptions()
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadOptions()
  }, 250)
})

watch(() => props.modelValue, (value) => {
  if (!value) selectedOption.value = null
  if (value && !displayedOptions.value.some((item) => item.id === Number(value))) {
    page.value = 1
    loadOptions()
  }
})

watch(() => props.refreshKey, () => {
  search.value = ''
  page.value = 1
  selectedOption.value = null
  loadOptions()
})

onMounted(loadOptions)
onUnmounted(() => {
  clearTimeout(searchTimer)
  requestNumber += 1
})
</script>

<template>
  <div class="mt-1.5 space-y-2">
    <input
      v-model="search"
      type="search"
      :aria-label="searchLabel"
      :placeholder="searchPlaceholder"
      :disabled="disabled"
      class="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-indigo-500 disabled:bg-gray-100"
    >
    <select
      :value="modelValue"
      :aria-label="selectLabel"
      :required="required"
      :disabled="disabled || loading"
      class="w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 disabled:bg-gray-100"
      @change="choose"
    >
      <option value="">{{ loading ? 'Loading…' : placeholder }}</option>
      <option v-for="option in displayedOptions" :key="option.id" :value="option.id">
        {{ option.label }}
      </option>
    </select>
    <p v-if="error" class="text-xs text-red-600">{{ error }}</p>
    <div v-else class="flex items-center justify-between gap-3 text-xs text-gray-400">
      <span>{{ count }} result{{ count === 1 ? '' : 's' }} · Page {{ page }} of {{ pages }}</span>
      <span class="flex gap-2">
        <button type="button" class="rounded border px-2 py-1 disabled:opacity-40" :disabled="loading || page <= 1" @click="changePage(page - 1)">Previous</button>
        <button type="button" class="rounded border px-2 py-1 disabled:opacity-40" :disabled="loading || page >= pages" @click="changePage(page + 1)">Next</button>
      </span>
    </div>
  </div>
</template>
