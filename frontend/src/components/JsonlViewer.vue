<template>
  <div class="p-6">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">JSONL File Explorer</h1>
      <div class="flex gap-2">
        <button
          @click="downloadAllAsZip"
          class="btn btn-primary text-sm"
          :disabled="downloading"
        >
          📦 Download All as ZIP
        </button>
        <button
          @click="refreshFiles"
          class="btn btn-secondary text-sm"
        >
          🔄 Refresh
        </button>
      </div>
    </div>

    <!-- File Browser -->
    <div class="card">
      <div v-if="loading" class="text-center py-8">
        <div class="text-gray-400">Loading JSONL files...</div>
      </div>
      
      <div v-else-if="error" class="text-center py-8 text-red-400">
        {{ error }}
      </div>
      
      <div v-else-if="files.length === 0" class="text-center py-8 text-gray-400">
        No JSONL files found in staging directory
      </div>
      
      <div v-else class="space-y-4">
        <!-- File List -->
        <div class="grid grid-cols-12 gap-4">
          <div class="col-span-6 font-medium text-gray-300">File</div>
          <div class="col-span-2 text-gray-300">Size</div>
          <div class="col-span-2 text-gray-300">Modified</div>
          <div class="col-span-2 text-gray-300">Actions</div>
        </div>

        <div
          v-for="file in files"
          :key="file.path"
          class="grid grid-cols-12 gap-4 p-3 border border-gray-600 rounded hover:bg-gray-700 transition-colors"
        >
          <!-- File Name -->
          <div class="col-span-6">
            <div class="font-mono text-sm text-blue-400">{{ file.name }}</div>
            <div class="text-xs text-gray-400">{{ file.path }}</div>
          </div>
          
          <!-- File Size -->
          <div class="col-span-2 text-sm text-gray-300">
            {{ formatFileSize(file.size) }}
          </div>
          
          <!-- Modified Time -->
          <div class="col-span-2 text-sm text-gray-300">
            {{ formatDate(file.modified) }}
          </div>
          
          <!-- Actions -->
          <div class="col-span-2 flex gap-2">
            <button
              @click="previewFileData(file)"
              class="btn btn-secondary text-xs"
              title="Preview first 100 lines"
            >
              👁 Preview
            </button>
            <button
              @click="downloadFile(file)"
              class="btn btn-primary text-xs"
              title="Download file"
            >
              ⬇ Download
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Preview Modal -->
    <div
      v-if="showPreviewModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showPreviewModal = false"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-6xl max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-2xl font-bold">Preview: {{ selectedFile.name }}</h2>
          <div class="text-sm text-gray-400">{{ selectedFile.path }}</div>
          <button @click="showPreviewModal = false" class="text-gray-400 hover:text-white text-2xl">
            ×
          </button>
        </div>

        <!-- JSONL Viewer with Line Numbers -->
        <div class="bg-gray-900 rounded p-4 overflow-x-auto">
          <div class="text-xs text-gray-400 mb-2">
            Showing first 100 lines of {{ selectedFile.name }}
          </div>
          <pre class="text-xs text-green-400 font-mono overflow-x-auto">{{ previewData.slice(0, 100).join('\n') }}</pre>
          
          <div v-if="hasMoreLines" class="text-center mt-4">
            <button
              @click="expandPreview"
              class="btn btn-secondary text-sm"
            >
              Load More ({{ previewData.length }} records)
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { 
  listFiles, 
  previewFile as fetchPreview, 
  downloadFile as fetchFile, 
  downloadAllAsZip as fetchZip 
} from '../api/staging'

const files = ref([])
const loading = ref(false)
const error = ref(null)
const showPreviewModal = ref(false)
const selectedFile = ref(null)
const previewData = ref([])
const hasMoreLines = ref(false)
const downloading = ref(false)

async function loadFiles() {
  try {
    loading.value = true
    error.value = null
    files.value = await listFiles()
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

async function previewFileData(file) {
  try {
    selectedFile.value = file
    previewData.value = await fetchPreview(file.path, 100)
    showPreviewModal.value = true
    hasMoreLines.value = previewData.value.length > 100
  } catch (err) {
    error.value = err.message
  }
}

function expandPreview() {
  previewFile(selectedFile.value)
}

function formatDate(timestamp) {
  return new Date(timestamp).toLocaleString()
}

function formatFileSize(bytes) {
  const units = ['B', 'KB', 'MB', 'GB']
  if (bytes === 0) return '0 B'
  const i = Math.floor(Math.log(bytes) / 1024)
  return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${units[i]}`
}

async function downloadFile(file) {
  try {
    await fetchFile(file.path)
  } catch (err) {
    error.value = err.message
  }
}

async function downloadAllAsZip() {
  try {
    downloading.value = true
    await fetchZip()
  } catch (err) {
    error.value = err.message
  } finally {
    downloading.value = false
  }
}

onMounted(() => {
  loadFiles()
})
</script>