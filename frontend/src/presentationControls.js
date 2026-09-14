export function presentationDirectionForKey(event, hasActiveSession) {
  if (!hasActiveSession) return 0
  if (event.defaultPrevented || event.altKey || event.ctrlKey || event.metaKey) return 0
  const target = event.target
  const tagName = target?.tagName?.toUpperCase()
  if (target?.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(tagName)) return 0
  if (event.key === 'ArrowLeft') return -1
  if (event.key === 'ArrowRight') return 1
  return 0
}

export function createUploadRequestId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID()
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (character) => {
    const random = Math.floor(Math.random() * 16)
    const value = character === 'x' ? random : ((random & 0x3) | 0x8)
    return value.toString(16)
  })
}
