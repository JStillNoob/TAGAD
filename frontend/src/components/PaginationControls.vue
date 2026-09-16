<script setup>
import { computed } from 'vue'

const props = defineProps({
  page: { type: Number, required: true },
  count: { type: Number, required: true },
  pageSize: { type: Number, default: 20 },
  disabled: Boolean,
})
const emit = defineEmits(['change'])
const pages = computed(() => Math.max(1, Math.ceil(props.count / props.pageSize)))
</script>

<template>
  <div class="flex items-center justify-between gap-4 border-t border-gray-100 px-5 py-3">
    <p class="text-xs text-gray-400">{{ count }} result{{ count === 1 ? '' : 's' }} · Page {{ page }} of {{ pages }}</p>
    <div class="flex gap-2">
      <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 disabled:opacity-40" :disabled="disabled || page <= 1" @click="emit('change', page - 1)">Previous</button>
      <button type="button" class="rounded-lg border border-gray-200 px-3 py-1.5 text-sm text-gray-600 disabled:opacity-40" :disabled="disabled || page >= pages" @click="emit('change', page + 1)">Next</button>
    </div>
  </div>
</template>
