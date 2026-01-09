<template>
  <div class="p-8">
    <div class="mb-8">
      <router-link to="/sources" class="text-blue-400 hover:text-blue-300">
        ← Back to Sources
      </router-link>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-8">
      Loading source details...
    </div>

    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <div v-else>
      <!-- Source Info -->
      <div class="card mb-6">
        <div class="flex items-start justify-between mb-4">
          <div>
            <h1 class="text-3xl font-bold">{{ source.name }}</h1>
            <p class="text-gray-400 text-sm mt-1">{{ source.id }}</p>
          </div>
          <router-link :to="`/sources`" class="btn btn-secondary text-sm">
            Edit Source
          </router-link>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div>
            <span class="text-gray-400 block mb-1">Publisher:</span>
            <span class="font-medium">{{ source.publisher }}</span>
          </div>
          <div>
            <span class="text-gray-400 block mb-1">Type:</span>
            <code class="bg-gray-900 px-2 py-1 rounded text-blue-400 text-xs">
              {{ source.fetcherType.code }}
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

        <!-- Class Path -->
        <div class="mt-4">
          <span class="text-gray-400 text-sm block mb-1">Class Path:</span>
          <code class="block bg-gray-900 p-2 rounded text-green-400 text-xs">
            {{ source.fetcherType.classPath }}
          </code>
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

      <!-- Execute Section -->
      <div class="card mb-6">
        <h2 class="text-xl font-bold mb-4">Live Testing</h2>
        <p class="text-gray-400 text-sm mb-4">
          Execute this source to fetch data from the configured endpoint.
          This will run the full pipeline: fetch → parse → normalize → upsert.
        </p>
        <div class="flex space-x-3">
          <button
            @click="executeTest"
            :disabled="executing"
            class="btn btn-primary"
          >
            {{ executing ? '⟳ Executing...' : '▶ Execute Source Now' }}
          </button>
          <button
            v-if="executionResult"
            @click="clearResults"
            class="btn btn-secondary"
          >
            Clear Results
          </button>
        </div>
      </div>

      <!-- Execution Status -->
      <ExecutionStatus
        v-if="executionStatus !== 'idle'"
        :status="executionStatus"
        :message="executionMessage"
        :timestamp="executionTimestamp"
        :details="executionDetails"
        :on-retry="executeTest"
        class="mb-6"
      />

      <!-- Execution Result with JSON Viewer -->
      <div v-if="executionResult" class="mb-6">
        <JsonViewer
          :data="executionResult"
          title="Execution Result"
          max-height="max-h-[500px]"
        />
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
import { fetchSource, executeSource } from '../api/graphql'
import ExecutionStatus from '../components/ExecutionStatus.vue'
import JsonViewer from '../components/JsonViewer.vue'

const route = useRoute()
const source = ref(null)
const loading = ref(true)
const error = ref(null)
const executing = ref(false)
const executionResult = ref(null)
const executionHistory = ref([])
const selectedHistoryItem = ref(null)
const lastExecutionTime = ref(null)
const lastExecutionSuccess = ref(null)
const lastExecutionMessage = ref(null)
const lastExecutionDetails = ref(null)

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

async function loadSource() {
  try {
    loading.value = true
    error.value = null
    const data = await fetchSource(route.params.id)
    source.value = data.source
  } catch (e) {
    error.value = 'Failed to load source: ' + e.message
  } finally {
    loading.value = false
  }
}

async function executeTest() {
  try {
    executing.value = true
    error.value = null
    lastExecutionTime.value = new Date().toLocaleString()

    const result = await executeSource(route.params.id)
    executionResult.value = result.executeSource

    lastExecutionSuccess.value = result.executeSource.success
    lastExecutionMessage.value = result.executeSource.message
    lastExecutionDetails.value = result.executeSource.sourceId
      ? `Source ID: ${result.executeSource.sourceId}`
      : null

    // Add to history
    executionHistory.value.unshift({
      ...result.executeSource,
      timestamp: lastExecutionTime.value,
      data: result.executeSource
    })

    // Keep only last 20 executions
    if (executionHistory.value.length > 20) {
      executionHistory.value = executionHistory.value.slice(0, 20)
    }
  } catch (e) {
    error.value = 'Failed to execute source: ' + e.message
    lastExecutionSuccess.value = false
    lastExecutionMessage.value = e.message
    lastExecutionDetails.value = e.stack || null
  } finally {
    executing.value = false
  }
}

function clearResults() {
  executionResult.value = null
  lastExecutionSuccess.value = null
  lastExecutionMessage.value = null
  lastExecutionDetails.value = null
}

function clearHistory() {
  executionHistory.value = []
}

function viewHistoryItem(item) {
  selectedHistoryItem.value = item
}

onMounted(() => {
  loadSource()
})
</script>
