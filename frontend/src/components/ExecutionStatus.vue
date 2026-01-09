<template>
  <div
    class="execution-status p-4 rounded border"
    :class="statusClass"
  >
    <div class="flex items-start justify-between">
      <div class="flex-1">
        <div class="flex items-center space-x-2 mb-2">
          <span class="text-2xl">{{ statusIcon }}</span>
          <span class="font-bold text-lg">{{ statusTitle }}</span>
        </div>
        <p class="text-sm">{{ message }}</p>
        <div v-if="timestamp" class="text-xs mt-2 opacity-75">
          {{ timestamp }}
        </div>
      </div>
      <button
        v-if="onRetry"
        @click="onRetry"
        class="btn btn-secondary text-xs py-1 px-3"
      >
        Retry
      </button>
    </div>

    <div v-if="details" class="mt-4 pt-4 border-t border-current/20">
      <details>
        <summary class="cursor-pointer text-sm font-medium mb-2">
          View Details
        </summary>
        <div class="text-xs bg-black/20 p-3 rounded mt-2">
          <pre>{{ details }}</pre>
        </div>
      </details>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    required: true,
    validator: (value) => ['success', 'error', 'loading', 'idle'].includes(value)
  },
  message: {
    type: String,
    required: true
  },
  timestamp: {
    type: String,
    default: null
  },
  details: {
    type: String,
    default: null
  },
  onRetry: {
    type: Function,
    default: null
  }
})

const statusClass = computed(() => {
  const classes = {
    success: 'bg-green-900 border-green-700 text-green-100',
    error: 'bg-red-900 border-red-700 text-red-100',
    loading: 'bg-blue-900 border-blue-700 text-blue-100',
    idle: 'bg-gray-800 border-gray-700 text-gray-300'
  }
  return classes[props.status]
})

const statusIcon = computed(() => {
  const icons = {
    success: '✓',
    error: '✗',
    loading: '⟳',
    idle: '○'
  }
  return icons[props.status]
})

const statusTitle = computed(() => {
  const titles = {
    success: 'Success',
    error: 'Error',
    loading: 'Executing...',
    idle: 'Ready'
  }
  return titles[props.status]
})
</script>
