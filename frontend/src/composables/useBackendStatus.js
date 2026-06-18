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

// Propagación inmediata del estado, llamada por la capa de API: un fallo de red /
// 5xx marca el backend caído sin esperar al poll de 15s; una respuesta válida lo
// confirma vivo. Al ser `isConnected` un singleton reactivo, todos los componentes
// que lo consumen reaccionan a la vez (no hay que avisar a cada uno).
export function notifyBackendDown() {
  if (isConnected.value !== false) isConnected.value = false
}
export function notifyBackendUp() {
  if (isConnected.value !== true) isConnected.value = true
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
