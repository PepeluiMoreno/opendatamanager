<template>
  <div
    v-if="show"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click.self="$emit('close')"
  >
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-6xl max-h-[90vh] overflow-y-auto">
      <div class="flex justify-between items-center mb-4">
        <div>
          <h2 class="text-2xl font-bold">Dataset Preview</h2>
          <p class="text-sm text-gray-400 mt-1">{{ resourceName }} - v{{ version }}</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-white text-2xl">
          ×
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="text-center py-8">
        <div class="text-gray-400">Loading data...</div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
        {{ error }}
      </div>

      <!-- Data Preview -->
      <div v-else class="bg-gray-900 rounded p-4 overflow-x-auto">
        <div class="flex justify-between items-center mb-2">
          <div class="text-xs text-gray-400">
            Showing {{ displayedLines }} of {{ totalLines }} records
          </div>
          <div class="flex gap-2">
            <button
              v-if="displayedLines < totalLines"
              @click="loadMore"
              class="btn btn-secondary text-xs"
            >
              Load More ({{ Math.min(linesPerPage, totalLines - displayedLines) }} more)
            </button>
            <button
              @click="toggleFormat"
              class="btn btn-secondary text-xs"
            >
              {{ isPretty ? 'Compact' : 'Pretty' }} Format
            </button>
          </div>
        </div>

        <!-- JSONL Data Display -->
        <pre class="text-xs text-green-400 font-mono overflow-x-auto">{{ formattedData }}</pre>
      </div>

      <!-- Info about JSONL Format -->
      <div class="mt-4 p-3 bg-blue-900 border border-blue-700 rounded text-blue-200 text-sm">
        <strong>Why JSONL?</strong> JSONL (JSON Lines) stores each record as a separate JSON object on its own line,
        making it ideal for streaming large datasets, line-by-line processing, and appending new data without parsing the entire file.
        Unlike JSON arrays, JSONL files can be processed incrementally and are more efficient for big data workflows.
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  show: {
    type: Boolean,
    required: true
  },
  datasetId: {
    type: String,
    required: true
  },
  resourceName: {
    type: String,
    required: true
  },
  version: {
    type: String,
    required: true
  }
})

const emit = defineEmits(['close'])

const loading = ref(false)
const error = ref(null)
const rawData = ref([])
const displayedLines = ref(10)
const linesPerPage = ref(50)
const isPretty = ref(false)

const totalLines = computed(() => rawData.value.length)

const formattedData = computed(() => {
  const linesToShow = rawData.value.slice(0, displayedLines.value)
  if (isPretty.value) {
    return linesToShow.map(line => JSON.stringify(JSON.parse(line), null, 2)).join('\n\n')
  }
  return linesToShow.join('\n')
})

function loadMore() {
  displayedLines.value = Math.min(displayedLines.value + linesPerPage.value, totalLines.value)
}

function toggleFormat() {
  isPretty.value = !isPretty.value
}

async function loadData() {
  try {
    loading.value = true
    error.value = null

    // Fetch the JSONL data from the API
    const response = await fetch(`http://localhost:8040/api/datasets/${props.datasetId}/data.jsonl`)
    if (!response.ok) {
      throw new Error(`Failed to fetch dataset: ${response.statusText}`)
    }

    const text = await response.text()
    rawData.value = text.trim().split('\n').filter(line => line.length > 0)
    displayedLines.value = Math.min(10, rawData.value.length)
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

// Load data when modal is opened
watch(() => props.show, (newVal) => {
  if (newVal) {
    loadData()
  } else {
    // Reset state when closed
    rawData.value = []
    displayedLines.value = 10
    isPretty.value = false
    error.value = null
  }
})
</script>
