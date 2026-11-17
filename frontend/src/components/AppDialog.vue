<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  open: Boolean,
  labelledby: { type: String, required: true },
  describedby: { type: String, default: '' },
  panelClass: { type: String, default: '' },
  busy: Boolean,
  initialFocus: { type: String, default: '' },
})
const emit = defineEmits(['close'])
const dialog = ref(null)
let opener = null

async function focusInitialControl() {
  await nextTick()
  const preferred = props.initialFocus
    ? dialog.value?.querySelector(props.initialFocus)
    : null
  const fallback = dialog.value?.querySelector(
    '[autofocus], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), a[href]',
  )
  ;(preferred || fallback)?.focus()
}

watch(
  () => props.open,
  async (open) => {
    if (!open) {
      if (dialog.value?.open) dialog.value.close()
      return
    }
    await nextTick()
    if (!dialog.value) return
    if (!dialog.value.open) {
      opener = document.activeElement
      dialog.value.showModal()
      await focusInitialControl()
    }
  },
  { immediate: true },
)

function requestClose() {
  if (!props.busy) emit('close')
}

function handleBackdrop(event) {
  if (event.target === dialog.value) requestClose()
}

function handleClosed() {
  if (props.open) emit('close')
  if (opener?.isConnected) opener.focus()
  opener = null
}

onBeforeUnmount(() => {
  if (dialog.value?.open) dialog.value.close()
  if (opener?.isConnected) opener.focus()
})
</script>

<template>
  <dialog
    ref="dialog"
    class="app-dialog"
    :aria-labelledby="labelledby"
    :aria-describedby="describedby || undefined"
    :aria-busy="busy || undefined"
    @cancel.prevent="requestClose"
    @click="handleBackdrop"
    @close="handleClosed"
  >
    <div v-if="open" class="app-dialog-panel" :class="panelClass">
      <slot />
    </div>
  </dialog>
</template>
