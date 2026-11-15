<script setup>
import { computed, nextTick, ref, watch } from 'vue'

const props = defineProps({
  open: Boolean,
  canSave: Boolean,
  savedLesson: Boolean,
  title: { type: String, default: '' },
  progress: { type: String, default: '' },
  busyAction: { type: String, default: '' },
  pending: Boolean,
  error: { type: String, default: '' },
})
const emit = defineEmits(['close', 'choose', 'recover'])
const dialog = ref(null)
const confirmFinish = ref(false)
const locked = computed(() => Boolean(props.busyAction) || props.pending)

watch(() => props.open, async (open) => {
  await nextTick()
  if (!dialog.value) return
  if (open) {
    confirmFinish.value = props.savedLesson
    if (!dialog.value.open) dialog.value.showModal()
  } else if (dialog.value.open) {
    dialog.value.close()
  }
})

function close() {
  if (!locked.value) emit('close')
}
</script>

<template>
  <dialog ref="dialog" class="session-end-dialog" aria-modal="true" aria-labelledby="end-class-title" aria-describedby="end-class-description" @cancel.prevent="close">
    <h2 id="end-class-title" class="text-xl font-semibold">{{ confirmFinish ? 'Finish this lesson?' : 'End this class?' }}</h2>
    <p class="mt-2 font-semibold">{{ title }}</p>
    <p v-if="progress" class="mt-1 text-sm text-gray-500">{{ progress }}</p>
    <p id="end-class-description" class="mt-4 text-sm leading-6 text-gray-600">
      {{ confirmFinish ? 'Finishing marks this lesson complete. Its class history, analytics, and reports stay available.' : 'Save your progress to continue during another class, or finish the lesson when you are done.' }}
    </p>
    <p v-if="error" class="session-dialog-error mt-4" role="alert">{{ error }}</p>
    <div v-if="pending" class="mt-5 space-y-3" role="status">
      <p class="text-sm">The result is still unconfirmed. Reconnect and check the saved status.</p>
      <button type="button" class="btn-primary w-full justify-center" :disabled="Boolean(busyAction)" @click="emit('recover')">{{ busyAction ? 'Checking status…' : 'Check status' }}</button>
      <a href="/" class="block text-center text-sm font-semibold text-brand">Sign in again</a>
    </div>
    <div v-else class="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
      <button v-if="canSave && !confirmFinish" type="button" class="btn-primary justify-center" :disabled="locked" @click="emit('choose', 'save')">{{ busyAction === 'save' ? 'Saving…' : 'Save & Continue Later' }}</button>
      <button type="button" :class="confirmFinish ? 'btn-primary' : 'btn-secondary'" class="justify-center" :disabled="locked" @click="confirmFinish ? emit('choose', 'finish') : confirmFinish = true">{{ busyAction === 'finish' ? 'Finishing…' : 'Finish Lesson' }}</button>
      <button v-if="confirmFinish && !savedLesson" type="button" class="btn-secondary justify-center" :disabled="locked" @click="confirmFinish = false">Back</button>
      <button type="button" class="btn-secondary justify-center" :disabled="locked" @click="close">{{ savedLesson ? 'Keep Saved' : 'Keep Teaching' }}</button>
    </div>
  </dialog>
</template>

<style scoped>
.session-end-dialog {
  width: min(580px, calc(100vw - 32px));
  max-height: calc(100dvh - 32px);
  overflow-y: auto;
  padding: 28px;
  color: var(--text);
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
}
.session-end-dialog::backdrop { background: rgb(8 17 47 / 60%); }
.session-dialog-error { padding: 12px; border-radius: 12px; background: var(--alert-tint); color: var(--alert); }
</style>
