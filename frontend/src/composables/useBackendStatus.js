import { ref, computed } from 'vue'

const isConnected = ref(null) // null = checking, true = ok, false = down
const checking = ref(false)
let checkInterval = null
let initialized = false

async function checkHealth() {
  checking.value = true
  try {
    const response = await fetch('/health', { signal: AbortSignal.timeout(5000) })
    isConnected.value = response.ok
  } catch {
    isConnected.value = false
  } finally {
    checking.value = false
  }
}

function startPolling() {
  if (initialized) return
  initialized = true
  checkHealth()
  checkInterval = setInterval(checkHealth, 15000)
}

function stopPolling() {
  if (checkInterval) {
    clearInterval(checkInterval)
    checkInterval = null
    initialized = false
  }
}

export function useBackendStatus() {
  return {
    isConnected: computed(() => isConnected.value),
    checking: computed(() => checking.value),
    checkHealth,
    startPolling,
    stopPolling,
  }
}
