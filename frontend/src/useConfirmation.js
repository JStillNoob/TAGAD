import { ref } from 'vue'

export function useConfirmation() {
  const confirmation = ref(null)
  let resolver = null

  function requestConfirmation(options) {
    if (resolver) resolver(false)
    confirmation.value = {
      title: options.title,
      description: options.description,
      confirmLabel: options.confirmLabel || 'Confirm',
      cancelLabel: options.cancelLabel || 'Cancel',
      tone: options.tone || 'danger',
    }
    return new Promise((resolve) => {
      resolver = resolve
    })
  }

  function settle(value) {
    const resolve = resolver
    resolver = null
    confirmation.value = null
    resolve?.(value)
  }

  return {
    confirmation,
    requestConfirmation,
    acceptConfirmation: () => settle(true),
    cancelConfirmation: () => settle(false),
  }
}
