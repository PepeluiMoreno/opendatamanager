<template>
  <div
    v-if="showError"
    class="fixed top-4 right-4 z-50 max-w-md animate-slide-in"
  >
    <div class="bg-red-900 border border-red-700 rounded-lg p-4 shadow-lg">
      <div class="flex items-start">
        <span class="text-2xl mr-3">⚠</span>
        <div class="flex-1">
          <h3 class="font-bold text-red-100 mb-1">Backend Connection Error</h3>
          <p class="text-sm text-red-200 mb-3">
            Unable to connect to the backend server.
          </p>
          <div class="text-xs text-red-200">
            <p>Please check that the backend is running.</p>
          </div>
          <button
            @click="retry"
            :disabled="checking"
            class="mt-3 px-3 py-1 bg-red-800 hover:bg-red-700 rounded text-sm transition-colors disabled:opacity-50"
          >
            {{ checking ? 'Checking...' : 'Retry' }}
          </button>
        </div>
        <button
          @click="dismiss"
          class="text-red-300 hover:text-white ml-2 text-xl"
        >
          ×
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { client } from '../api/graphql'

const isConnected = ref(true)
const checking = ref(false)
const dismissed = ref(false)
const consecutiveFailures = ref(0)
let checkInterval = null

const showError = computed(() => {
  return !isConnected.value && !dismissed.value && consecutiveFailures.value >= 2
})

async function checkConnection() {
  if (dismissed.value) return

  checking.value = true
  try {
    // Use raw fetch instead of GraphQL client for more control
    const response = await fetch('http://localhost:8040/graphql', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query: '{ __typename }'
      })
    })

    // If we got any response, the backend is running
    if (response) {
      isConnected.value = true
      consecutiveFailures.value = 0
      dismissed.value = false
    }
  } catch (error) {
    // Only fetch errors mean the backend is truly down
    consecutiveFailures.value++
    if (consecutiveFailures.value >= 2) {
      isConnected.value = false
    }
  } finally {
    checking.value = false
  }
}

function retry() {
  consecutiveFailures.value = 0
  checkConnection()
}

function dismiss() {
  dismissed.value = true
  consecutiveFailures.value = 0
}

onMounted(() => {
  // Check immediately
  checkConnection()

  // Then check every 15 seconds
  checkInterval = setInterval(checkConnection, 15000)
})

onUnmounted(() => {
  if (checkInterval) {
    clearInterval(checkInterval)
  }
})
</script>

<style scoped>
@keyframes slide-in {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

.animate-slide-in {
  animation: slide-in 0.3s ease-out;
}
</style>
