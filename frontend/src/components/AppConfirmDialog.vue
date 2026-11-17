<script setup>
import AppDialog from './AppDialog.vue'

defineProps({
  open: Boolean,
  title: { type: String, default: 'Confirm action' },
  description: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirm' },
  cancelLabel: { type: String, default: 'Cancel' },
  tone: { type: String, default: 'danger' },
  busy: Boolean,
})
const emit = defineEmits(['confirm', 'cancel'])
</script>

<template>
  <AppDialog
    :open="open"
    labelledby="app-confirm-title"
    describedby="app-confirm-description"
    panel-class="app-confirm-dialog"
    :busy="busy"
    initial-focus="[data-confirm-cancel]"
    @close="emit('cancel')"
  >
    <h2 id="app-confirm-title" class="text-xl font-semibold text-navy">{{ title }}</h2>
    <p id="app-confirm-description" class="mt-3 text-sm leading-6 text-gray-600">{{ description }}</p>
    <div class="mt-6 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
      <button data-confirm-cancel type="button" class="btn-secondary justify-center" :disabled="busy" @click="emit('cancel')">
        {{ cancelLabel }}
      </button>
      <button
        type="button"
        :class="tone === 'danger' ? 'btn-danger' : 'btn-primary'"
        class="justify-center"
        :disabled="busy"
        @click="emit('confirm')"
      >
        {{ busy ? 'Working…' : confirmLabel }}
      </button>
    </div>
  </AppDialog>
</template>
