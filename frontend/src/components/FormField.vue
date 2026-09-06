<template>
  <div>
    <label :for="name" class="block text-sm font-semibold mb-2 text-navy">{{ label }}</label>
    <input
      :id="name"
      :name="name"
      :type="type"
      :value="modelValue"
      :autocomplete="autocomplete"
      required
      class="w-full rounded-xl border px-4 py-3 text-sm outline-none transition-all text-navy"
      :class="error ? 'border-red-400' : 'border-gray-200 focus:border-indigo-500'"
      :aria-invalid="Boolean(error)"
      :aria-describedby="error ? `${name}-error` : undefined"
      @input="$emit('update:modelValue', $event.target.value)"
    />
    <p v-if="error" :id="`${name}-error`" class="mt-1 text-xs text-red-600">{{ error }}</p>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: '' },
  label: { type: String, required: true },
  name: { type: String, required: true },
  type: { type: String, default: 'text' },
  autocomplete: { type: String, default: 'off' },
  error: { type: String, default: '' },
})

defineEmits(['update:modelValue'])
</script>
