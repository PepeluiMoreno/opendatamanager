<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Datasets</h1>
      <div class="flex gap-4 items-center">
        <!-- Resource Filter -->
        <select
          v-model="selectedResourceId"
          @change="loadDatasets"
          class="px-4 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
        >
          <option value="">All Resources</option>
          <option
            v-for="resource in resources"
            :key="resource.id"
            :value="resource.id"
          >
            {{ resource.name }}
          </option>
        </select>
        <button
          @click="loadDatasets"
          class="btn btn-secondary"
        >
          Refresh
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-8">
      Loading datasets...
    </div>

    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <div v-else class="card">
      <div v-if="datasets.length === 0" class="text-gray-400 text-center py-8">
        No datasets generated yet
      </div>

      <div v-else class="space-y-4">
        <div
          v-for="dataset in datasets"
          :key="dataset.id"
          class="border border-gray-600 rounded p-6"
        >
          <div class="flex justify-between items-start mb-4">
            <div class="flex-1">
              <div class="flex items-center space-x-3 mb-2">
                <h3 class="text-xl font-semibold">{{ getResourceName(dataset.resourceId) }}</h3>
                <span class="text-sm bg-blue-600 px-3 py-1 rounded">
                  v{{ dataset.majorVersion }}.{{ dataset.minorVersion }}.{{ dataset.patchVersion }}
                </span>
              </div>
              <div class="text-sm text-gray-400 space-y-1">
                <div><strong>Created:</strong> {{ formatDate(dataset.createdAt) }}</div>
                <div><strong>Records:</strong> {{ dataset.recordCount || 0 }}</div>
                <div v-if="dataset.checksum" class="font-mono text-xs"><strong>Checksum:</strong> {{ dataset.checksum.substring(0, 16) }}...</div>
              </div>
            </div>
          </div>

          <!-- Action Buttons -->
          <div class="flex gap-2 border-t border-gray-600 pt-4">
            <a
              :href="`http://localhost:8040/api/datasets/${dataset.id}/data.jsonl`"
              download
              class="btn btn-primary text-sm"
              title="Download JSONL data file"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
              </svg>
              Download
            </a>

            <button
              @click="previewDataset(dataset)"
              class="btn btn-secondary text-sm"
              title="Preview dataset content"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              Preview
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Dataset Preview Modal -->
    <DatasetPreviewModal
      :show="showPreviewModal"
      :datasetId="selectedDataset?.id || ''"
      :resourceName="selectedDataset ? getResourceName(selectedDataset.resourceId) : ''"
      :version="selectedDataset ? `${selectedDataset.majorVersion}.${selectedDataset.minorVersion}.${selectedDataset.patchVersion}` : ''"
      @close="closePreviewModal"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchDatasets, fetchResources } from '../api/graphql'
import DatasetPreviewModal from '../components/DatasetPreviewModal.vue'

const datasets = ref([])
const resources = ref([])
const loading = ref(false)
const error = ref(null)
const selectedResourceId = ref('')
const showPreviewModal = ref(false)
const selectedDataset = ref(null)

async function loadDatasets() {
  try {
    loading.value = true
    error.value = null
    const data = await fetchDatasets(selectedResourceId.value || null)
    datasets.value = data.datasets || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function loadResources() {
  try {
    const data = await fetchResources(false)
    resources.value = data.resources || []
  } catch (e) {
    console.error('Failed to load resources:', e)
  }
}

function getResourceName(resourceId) {
  const resource = resources.value.find(r => r.id === resourceId)
  return resource ? resource.name : resourceId
}

function formatDate(dateString) {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleString()
}

function previewDataset(dataset) {
  selectedDataset.value = dataset
  showPreviewModal.value = true
}

function closePreviewModal() {
  showPreviewModal.value = false
  selectedDataset.value = null
}

onMounted(() => {
  loadResources()
  loadDatasets()
})
</script>
