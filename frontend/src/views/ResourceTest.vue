<template>
  <div class="p-8">
    <div class="mb-8">
      <router-link to="/resources" class="text-blue-400 hover:text-blue-300">
        ← Back to Resources
      </router-link>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-8">
      Loading resource details...
    </div>

    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <div v-else>
      <!-- Resource Info -->
      <div class="card mb-6">
        <div class="flex items-start justify-between mb-4">
          <div>
            <h1 class="text-3xl font-bold">{{ source.name }}</h1>
            <p class="text-gray-400 text-sm mt-1">{{ source.id }}</p>
          </div>
          <div class="flex space-x-3">
            <button
              @click="fetchPreview"
              :disabled="executing"
              class="btn btn-primary text-sm"
            >
              {{ executing ? '⟳ Executing...' : 'Execute Test' }}
            </button>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-gray-400 block mb-1">Publisher:</span>
            <span class="font-medium">{{ source.publisher }}</span>
          </div>
          <div>
            <span class="text-gray-400 block mb-1">Type:</span>
            <code class="bg-gray-900 px-2 py-1 rounded text-blue-400 text-xs">
              {{ source.fetcher.name }}
            </code>
          </div>
          <div>
            <span class="text-gray-400 block mb-1">Status:</span>
            <span
              :class="source.active ? 'text-green-400' : 'text-red-400'"
              class="font-medium"
            >
              {{ source.active ? 'Active' : 'Inactive' }}
            </span>
          </div>
          <div>
            <span class="text-gray-400 block mb-1">Parameters:</span>
            <span class="font-medium">{{ source.params.length }}</span>
          </div>
        </div>

        <!-- Parameters Detail -->
        <div class="mt-4">
          <h3 class="font-bold mb-2 text-sm">Configuration Parameters:</h3>
          <div class="bg-gray-900 p-4 rounded space-y-2">
            <div v-for="param in source.params" :key="param.id" class="flex items-start">
              <span class="text-blue-400 font-mono text-sm min-w-[150px]">{{ param.key }}:</span>
              <span class="text-gray-300 text-sm break-all">{{ param.value }}</span>
            </div>
            <div v-if="source.params.length === 0" class="text-gray-500 text-sm">
              No parameters configured
            </div>
          </div>
        </div>
      </div>

      <!-- Execution Status -->
      <ExecutionStatus
        v-if="executionStatus !== 'idle'"
        :status="executionStatus"
        :message="executionMessage"
        :timestamp="executionTimestamp"
        :details="executionDetails"
        :on-retry="fetchPreview"
        class="mb-6"
      />

      <!-- Preview Data Section -->
      <div v-if="previewData.length > 0 && hasExecuted" class="mb-6">
        <div class="card">
        <div class="flex items-center justify-between mb-4">
          <div class="flex gap-2">
            <span class="text-sm text-green-400">
              {{ recordCount }} records extracted
            </span>
          </div>
          <button
            @click="togglePreviewFormat"
            class="text-sm text-purple-400 hover:text-purple-300"
          >
            {{ isPrettyFormat ? 'Compact' : 'Pretty' }} Format
          </button>
        </div>

        <div class="bg-gray-900 rounded p-4 overflow-x-auto max-h-[600px] overflow-y-auto">
          <pre class="text-xs text-green-400 font-mono">{{ showRawJson ? JSON.stringify(previewData, null, 2) : formattedPreviewData }}</pre>
        </div>

          <div class="mt-4 p-3 bg-blue-900 border border-blue-700 rounded text-blue-200 text-sm">
            <strong>Note:</strong> This is a temporary preview. Data is NOT saved as a version.
            To save data permanently, use the "Execute Resource Now" button above which runs the full pipeline.
          </div>
        </div>
      </div>

      <!-- Execution History -->
      <div v-if="executionHistory.length > 0" class="card">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-xl font-bold">Execution History</h2>
          <button @click="clearHistory" class="text-sm text-gray-400 hover:text-white">
            Clear History
          </button>
        </div>
        <div class="space-y-2">
          <div
            v-for="(exec, index) in executionHistory"
            :key="index"
            class="p-4 bg-gray-700 rounded hover:bg-gray-650 transition-colors"
          >
            <div class="flex items-start justify-between">
              <div class="flex-1">
                <div class="flex items-center space-x-2">
                  <span
                    :class="exec.success ? 'text-green-400' : 'text-red-400'"
                    class="font-bold text-lg"
                  >
                    {{ exec.success ? '✓' : '✗' }}
                  </span>
                  <span class="font-medium">{{ exec.success ? 'Success' : 'Failed' }}</span>
                </div>
                <p class="text-sm text-gray-300 mt-1">{{ exec.message }}</p>
              </div>
              <div class="text-right">
                <div class="text-xs text-gray-400">{{ exec.timestamp }}</div>
                <button
                  v-if="exec.data"
                  @click="viewHistoryItem(exec)"
                  class="text-xs text-blue-400 hover:text-blue-300 mt-1"
                >
                  View Details
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- History Detail Modal -->
    <div
      v-if="selectedHistoryItem"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="selectedHistoryItem = null"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-start justify-between mb-4">
          <div>
            <h2 class="text-2xl font-bold">Execution Details</h2>
            <p class="text-sm text-gray-400 mt-1">{{ selectedHistoryItem.timestamp }}</p>
          </div>
          <button @click="selectedHistoryItem = null" class="text-gray-400 hover:text-white text-2xl">
            ×
          </button>
        </div>
        <JsonViewer
          :data="selectedHistoryItem.data"
          title="Result Data"
          max-height="max-h-[600px]"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import { fetchResource, previewResourceData } from '../api/graphql'
import ExecutionStatus from '../components/ExecutionStatus.vue'
import JsonViewer from '../components/JsonViewer.vue'

const route = useRoute()
const source = ref(null)
const loading = ref(true)
const error = ref(null)
const executing = ref(false)
const executionHistory = ref([])
const selectedHistoryItem = ref(null)
const lastExecutionTime = ref(null)
const lastExecutionSuccess = ref(null)
const lastExecutionMessage = ref(null)
const lastExecutionDetails = ref(null)
const previewData = ref([])
const recordCount = ref(0)
const isPrettyFormat = ref(false)
const showRawJson = ref(false)
const hasExecuted = ref(false)

const executionStatus = computed(() => {
  if (executing.value) return 'loading'
  if (lastExecutionSuccess.value === true) return 'success'
  if (lastExecutionSuccess.value === false) return 'error'
  return 'idle'
})

const executionMessage = computed(() => {
  return lastExecutionMessage.value || 'Ready to execute'
})

const executionTimestamp = computed(() => {
  return lastExecutionTime.value
})

const executionDetails = computed(() => {
  return lastExecutionDetails.value
})

const formattedPreviewData = computed(() => {
  if (previewData.value.length === 0) return ''

  if (isPrettyFormat.value) {
    return previewData.value.map(item => JSON.stringify(item, null, 2)).join('\n\n')
  }
  return previewData.value.map(item => JSON.stringify(item)).join('\n')
})

async function loadSource() {
  try {
    loading.value = true
    error.value = null
    const data = await fetchResource(route.params.id)
    source.value = data.resource
  } catch (e) {
    error.value = 'Failed to load resource: ' + e.message
  } finally {
    loading.value = false
  }
}

async function fetchPreview() {
  try {
    executing.value = true
    error.value = null
    lastExecutionTime.value = new Date().toLocaleString()

    const result = await previewResourceData(route.params.id, 100)
    console.log('Preview response:', result) // Debug
    
    // Asignar datos primero
    const fetchedData = result.previewResourceData || []
    previewData.value = fetchedData
    
    console.log('Preview data length:', previewData.value.length) // Debug

    lastExecutionSuccess.value = true
    recordCount.value = previewData.value.length
    lastExecutionMessage.value = `Fetched ${previewData.value.length} records successfully`
    lastExecutionDetails.value = `Preview data loaded (not saved)`
    hasExecuted.value = true

    // Don't add previews to history - only actual executions
    // executionHistory.value.unshift({
    //   success: true,
    //   message: `Preview: ${previewData.value.length} records`,
    //   timestamp: lastExecutionTime.value,
    //   data: previewData.value.slice(0, 10) // Only store first 10 in history
    // })

    // Keep only last 20 executions
    if (executionHistory.value.length > 20) {
      executionHistory.value = executionHistory.value.slice(0, 20)
    }
  } catch (e) {
    error.value = 'Failed to fetch preview: ' + e.message
    lastExecutionSuccess.value = false
    lastExecutionMessage.value = e.message
    lastExecutionDetails.value = e.stack || null
  } finally {
    executing.value = false
  }
}

function clearPreview() {
  previewData.value = []
  lastExecutionSuccess.value = null
  lastExecutionMessage.value = null
  lastExecutionDetails.value = null
}

function togglePreviewFormat() {
  isPrettyFormat.value = !isPrettyFormat.value
}

function toggleJsonView() {
  showRawJson.value = !showRawJson.value
}

function clearHistory() {
  executionHistory.value = []
}

function viewHistoryItem(item) {
  selectedHistoryItem.value = item
}

onMounted(async () => {
  await loadSource()
})
</script>
