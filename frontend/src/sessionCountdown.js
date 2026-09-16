export function createSessionCountdown({
  seconds = 5,
  onTick,
  onComplete,
  schedule = setTimeout,
  cancelScheduled = clearTimeout,
}) {
  const duration = Math.max(1, Math.floor(Number(seconds) || 5))
  let running = false
  let remaining = duration
  let timer = null

  function queueNextTick() {
    timer = schedule(() => {
      if (!running) return
      remaining -= 1
      onTick(remaining)
      if (remaining === 0) {
        running = false
        timer = null
        onComplete()
        return
      }
      queueNextTick()
    }, 1000)
  }

  function start() {
    if (running) return false
    running = true
    remaining = duration
    onTick(remaining)
    queueNextTick()
    return true
  }

  function cancel() {
    if (!running) return false
    running = false
    if (timer !== null) cancelScheduled(timer)
    timer = null
    return true
  }

  return {
    start,
    cancel,
    get active() {
      return running
    },
  }
}
