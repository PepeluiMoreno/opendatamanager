<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Resources</h1>
      <button @click="showCreateModal = true" class="btn btn-primary">
        + Create Resource
      </button>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-8">
      Loading...
    </div>

    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <div v-else class="card">
      <table class="w-full">
        <thead>
          <tr class="border-b border-gray-700">
            <th class="text-left py-3 px-4">Name</th>
            <th class="text-left py-3 px-4">Publisher</th>
            <th class="text-left py-3 px-4">Type</th>
            <th class="text-left py-3 px-4">Status</th>
            <th class="text-right py-3 px-4">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="source in sources"
            :key="source.id"
            class="border-b border-gray-700 hover:bg-gray-700 transition-colors"
          >
            <td class="py-3 px-4 font-medium">{{ source.name }}</td>
            <td class="py-3 px-4 text-gray-400">{{ source.publisher }}</td>
            <td class="py-3 px-4">
              <code class="text-xs bg-gray-900 px-2 py-1 rounded text-blue-400">
                {{ source.fetcher.name }}
              </code>
            </td>
            <td class="py-3 px-4">
              <span
                :class="source.active ? 'text-green-400' : 'text-red-400'"
                class="text-sm font-medium"
              >
                {{ source.active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="py-3 px-4">
              <div class="flex justify-end gap-2">
                <router-link
                  :to="`/resources/${source.id}/test`"
                  class="btn btn-primary text-sm py-1 px-3"
                >
                  Test
                </router-link>
                <button
                  @click="showPreviewData(source)"
                  class="btn btn-success text-sm py-1 px-3"
                >
                  Preview
                </button>
                <button
                  @click="editSource(source)"
                  class="btn btn-secondary text-sm py-1 px-3"
                >
                  Edit
                </button>
                <button
                  @click="confirmDelete(source)"
                  class="btn btn-danger text-sm py-1 px-3"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="sources.length === 0" class="text-gray-400 text-center py-8">
        No resources configured yet. Click "Create Resource" to add one.
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div
      v-if="showCreateModal || showEditModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModals"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-5xl max-h-[90vh] overflow-y-auto">
        <h2 class="text-xl font-bold mb-4">
          {{ showCreateModal ? 'Create Resource' : 'Edit Resource' }}
        </h2>

        <form @submit.prevent="submitForm" class="space-y-3 text-sm">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <Tooltip :text="getTooltip('name')">
                <label class="block text-xs font-medium mb-1">Name</label>
              </Tooltip>
              <input
                v-model="form.name"
                type="text"
                required
                class="input w-full text-sm"
                :placeholder="getPlaceholder('name')"
              />
            </div>

            <div>
              <Tooltip :text="getTooltip('publisher')">
                <label class="block text-xs font-medium mb-1">Publisher</label>
              </Tooltip>
              <input
                v-model="form.publisher"
                type="text"
                required
                class="input w-full text-sm"
                :placeholder="getPlaceholder('publisher')"
              />
            </div>
          </div>

          <div>
            <Tooltip :text="getTooltip('fetcher_id')">
              <label class="block text-xs font-medium mb-1">Select Fetcher</label>
            </Tooltip>
            <select v-model="form.fetcherId" required class="input w-full text-sm">
              <option value="">Select a fetcher...</option>
              <option
                v-for="type in Fetchers"
                :key="type.id"
                :value="type.id"
              >
                {{ type.name }} - {{ type.description }}
              </option>
            </select>
          </div>

          <div>
            <label class="block text-xs font-medium mb-2">Parameters</label>

            <!-- Required Parameters (always shown) -->
            <div v-if="requiredParams.length > 0" class="mb-4">
              <h4 class="text-sm font-medium mb-2 text-red-400">Required Parameters</h4>
              <div class="space-y-1">
                <div
                  v-for="param in requiredParams"
                  :key="`req-${param.paramName}`"
                  class="flex gap-2 items-start border border-red-600 rounded p-2 bg-red-950 bg-opacity-20"
                >
                  <div class="w-1/5 flex-shrink-0">
                    <label class="block text-xs text-gray-300 mb-1">{{ param.paramName }}</label>
                    <span class="text-xs text-gray-400">{{ param.dataType }}</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <input
                      :value="getParamValue(param.paramName)"
                      type="text"
                      :placeholder="getPlaceholder(param.paramName) || `Enter ${param.paramName}...`"
                      class="input w-full text-xs"
                      @input="updateParamValue(param.paramName, $event.target.value)"
                    />
                  </div>
                </div>
              </div>
            </div>

            <!-- Add Optional Parameters Dropdown -->
            <div v-if="selectedFetcher && optionalParams.length > 0" class="mb-4">
              <select
                v-model="selectedOptionalParam"
                @change="addOptionalParameter"
                class="w-full text-sm px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
              >
                <option value="">+ Add optional parameter...</option>
                <option
                  v-for="param in availableOptionalParams"
                  :key="param.paramName"
                  :value="param.paramName"
                >
                  {{ param.paramName }} ({{ param.dataType }})
                </option>
              </select>
            </div>

            <!-- Optional Parameters (added by user) -->
            <div v-if="addedOptionalParams.length > 0">
              <h4 class="text-sm font-medium mb-2 text-blue-400">Optional Parameters</h4>
              <div class="space-y-1">
                <div
                  v-for="paramName in addedOptionalParams"
                  :key="`opt-${paramName}`"
                  class="flex gap-2 items-start border border-blue-600 rounded p-2 bg-blue-950 bg-opacity-20"
                >
                  <div class="w-1/5 flex-shrink-0">
                    <label class="block text-xs text-gray-300 mb-1">{{ paramName }}</label>
                    <span class="text-xs text-gray-400">{{ getParamType(paramName) }}</span>
                  </div>
                  <div class="flex-1 min-w-0">
                    <input
                      :value="getParamValue(paramName)"
                      type="text"
                      :placeholder="getPlaceholder(paramName) || `Enter ${paramName}...`"
                      class="input w-full text-xs"
                      @input="updateParamValue(paramName, $event.target.value)"
                    />
                  </div>
                  <div class="w-8 flex-shrink-0 flex items-center justify-center">
                    <button
                      type="button"
                      @click="removeOptionalParam(paramName)"
                      class="text-red-400 hover:text-red-300"
                      title="Remove optional parameter"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>
            
            <!-- No parameters message -->
            <div v-if="requiredParams.length === 0 && addedOptionalParams.length === 0" class="text-center py-4 text-gray-400 text-sm">
              <div v-if="!selectedFetcher">
                Select a Fetcher to see available parameters
              </div>
              <div v-else>
                This Fetcher has no parameters defined
              </div>
            </div>
          </div>

          <!-- Execution Settings -->
          <div class="border-t border-gray-700 pt-4 mt-4">
            <h3 class="text-sm font-bold mb-3 text-blue-400">⚙️ Execution Settings</h3>
            <div class="grid grid-cols-3 gap-4">
              <div>
                <label class="block text-xs font-medium mb-1">Max Workers</label>
                <input
                  v-model.number="form.maxWorkers"
                  type="number"
                  min="1"
                  max="10"
                  class="input w-full text-sm"
                  title="Number of parallel workers (1 = sequential)"
                />
                <span class="text-xs text-gray-400">1 = sequential, >1 = parallel</span>
              </div>

              <div>
                <label class="block text-xs font-medium mb-1">Timeout (seconds)</label>
                <input
                  v-model.number="form.timeoutSeconds"
                  type="number"
                  min="30"
                  max="3600"
                  class="input w-full text-sm"
                  title="Timeout per resource execution"
                />
                <span class="text-xs text-gray-400">Default: 300s (5 min)</span>
              </div>

              <div>
                <label class="block text-xs font-medium mb-1">Priority</label>
                <input
                  v-model.number="form.executionPriority"
                  type="number"
                  min="-10"
                  max="10"
                  class="input w-full text-sm"
                  title="Execution priority (higher = first)"
                />
                <span class="text-xs text-gray-400">Higher executes first</span>
              </div>

              <div>
                <label class="block text-xs font-medium mb-1">Retry Attempts</label>
                <input
                  v-model.number="form.retryAttempts"
                  type="number"
                  min="0"
                  max="5"
                  class="input w-full text-sm"
                  title="Number of retries on failure"
                />
                <span class="text-xs text-gray-400">0 = no retries</span>
              </div>

              <div>
                <label class="block text-xs font-medium mb-1">Retry Delay (seconds)</label>
                <input
                  v-model.number="form.retryDelaySeconds"
                  type="number"
                  min="10"
                  max="300"
                  class="input w-full text-sm"
                  title="Delay between retries"
                />
                <span class="text-xs text-gray-400">Default: 60s</span>
              </div>
            </div>
          </div>

          <!-- Dataset Loading Settings -->
          <div class="border-t border-gray-700 pt-4 mt-4">
            <h3 class="text-sm font-bold mb-3 text-green-400">💾 Dataset Loading Settings</h3>
            <div class="grid grid-cols-2 gap-4">
              <div class="flex items-center">
                <input
                  v-model="form.enableLoad"
                  type="checkbox"
                  id="enableLoad"
                  class="mr-2"
                />
                <label for="enableLoad" class="text-xs cursor-pointer">Enable automatic loading to core schema</label>
              </div>

              <div v-if="form.enableLoad">
                <label class="block text-xs font-medium mb-1">Load Mode</label>
                <select v-model="form.loadMode" class="input w-full text-sm">
                  <option value="replace">Replace (delete all, insert new)</option>
                  <option value="upsert">Upsert (update existing, insert new)</option>
                  <option value="append">Append (only insert)</option>
                </select>
              </div>
            </div>
          </div>

          <!-- Active checkbox - only in edit mode -->
          <div v-if="showEditModal" class="flex items-center border-t border-gray-700 pt-4 mt-4">
            <input
              v-model="form.active"
              type="checkbox"
              id="active"
              class="mr-2"
            />
            <Tooltip :text="getTooltip('active')">
              <label for="active" class="text-xs cursor-pointer">Active</label>
            </Tooltip>
          </div>

          <div class="flex justify-end space-x-2 pt-3 border-t border-gray-700">
            <button type="button" @click="closeModals" class="btn btn-secondary text-sm">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary text-sm">
              {{ showCreateModal ? 'Create' : 'Update' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="showDeleteModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showDeleteModal = false"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-2xl font-bold mb-4">Confirm Delete</h2>
        <p class="mb-6">
          Are you sure you want to delete resource "{{ sourceToDelete?.name }}"?
        </p>
        <div class="flex justify-end space-x-2">
          <button @click="showDeleteModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="handleDelete" class="btn btn-danger">
            Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Preview Data Modal -->
    <div
      v-if="showPreviewModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showPreviewModal = false"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-6xl max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-2xl font-bold">Preview Data - {{ previewSource?.name }}</h2>
          <button @click="showPreviewModal = false" class="text-gray-400 hover:text-white text-2xl">
            ×
          </button>
        </div>

        <div v-if="loadingPreview" class="text-gray-400 text-center py-8">
          Loading preview data...
        </div>

        <div v-else-if="previewError" class="p-4 bg-red-900 border border-red-700 rounded text-red-200 mb-4">
          {{ previewError }}
        </div>

        <div v-else-if="previewData">
          <div class="mb-4 text-sm text-gray-400">
            Showing first {{ Array.isArray(previewData) ? previewData.length : 1 }} record(s)
          </div>

          <!-- JSON view -->
          <pre class="bg-gray-900 p-4 rounded text-xs overflow-x-auto text-green-400">{{ JSON.stringify(previewData, null, 2) }}</pre>
        </div>

        <div class="flex justify-end mt-4">
          <button @click="showPreviewModal = false" class="btn btn-secondary">
            Close
          </button>
        </div>
      </div>
    </div>

    <!-- Confirm Remove Parameter Dialog -->
    <ConfirmDialog
      v-if="showRemoveParamDialog"
      title="Remove Parameter"
      :message="`Are you sure you want to remove this parameter?`"
      confirm-text="Remove"
      cancel-text="Cancel"
      @confirm="confirmRemoveParam"
      @cancel="cancelRemoveParam"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import Tooltip from '../components/Tooltip.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import {
  fetchResources,
  fetchFetchers,
  fetchFieldMetadata,
  createResource,
  updateResource,
  deleteResource,
  previewResourceData,
} from '../api/graphql'

const sources = ref([])
const Fetchers = ref([])
const fieldMetadata = ref({}) // Metadata for tooltips
const loading = ref(true)
const error = ref(null)

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const showPreviewModal = ref(false)
const sourceToDelete = ref(null)
const editingSource = ref(null)
const previewSource = ref(null)
const previewData = ref(null)
const loadingPreview = ref(false)
const previewError = ref(null)

const form = ref({
  name: '',
  publisher: '',
  fetcherId: '',
  params: [],
  active: true,
  // Dataset loading settings
  enableLoad: false,
  loadMode: 'replace',
  // Execution settings
  maxWorkers: 1,
  timeoutSeconds: 300,
  retryAttempts: 0,
  retryDelaySeconds: 60,
  executionPriority: 0,
})

// Computed properties for selected fetcher type
const selectedFetcher = computed(() => {
  if (!Fetchers.value || Fetchers.value.length === 0) return null
  return Fetchers.value.find(type => type.id === form.value.fetcherId)
})

const requiredParams = computed(() => {
  if (!selectedFetcher.value || !selectedFetcher.value.paramsDef) {
    return []
  }
  return selectedFetcher.value.paramsDef.filter(param => param.required === true)
})

const optionalParams = computed(() => {
  if (!selectedFetcher.value || !selectedFetcher.value.paramsDef) {
    return []
  }
  return selectedFetcher.value.paramsDef.filter(param => param.required !== true)
})

const addedOptionalParams = computed(() => {
  const allRequired = requiredParams.value.map(p => p.paramName)
  return form.value.params
    .map(p => p.key)
    .filter(key => !allRequired.includes(key))
})

const availableOptionalParams = computed(() => {
  const currentParamNames = form.value.params.map(p => p.key)
  return optionalParams.value.filter(param => !currentParamNames.includes(param.paramName))
})

const selectedOptionalParam = ref('')
const showRemoveParamDialog = ref(false)
const paramToRemove = ref(null)

// Helper functions for parameters
function getParamValue(paramName) {
  const param = form.value.params.find(p => p.key === paramName)
  return param ? param.value : ''
}

function getParamType(paramName) {
  const param = optionalParams.value.find(p => p.paramName === paramName)
  return param ? param.dataType : 'string'
}

function updateParamValue(paramName, value) {
  const param = form.value.params.find(p => p.key === paramName)
  if (param) {
    param.value = value
  } else {
    form.value.params.push({ key: paramName, value })
  }
}

function addOptionalParameter() {
  if (!selectedOptionalParam.value) return
  
  const paramName = selectedOptionalParam.value
  const existingParam = form.value.params.find(p => p.key === paramName)
  
  if (!existingParam) {
    form.value.params.push({ key: paramName, value: '' })
  }
  
  selectedOptionalParam.value = ''
}

function removeOptionalParam(paramName) {
  const index = form.value.params.findIndex(p => p.key === paramName)
  if (index !== -1) {
    form.value.params.splice(index, 1)
  }
}

 async function loadData() {
  try {
    loading.value = true
    error.value = null
    const [resourcesData, typesData, resourceMetadata, paramMetadata] = await Promise.all([
      fetchResources(false),
      fetchFetchers(),
      fetchFieldMetadata('resource'),
      fetchFieldMetadata('resource_param'),
    ])
    sources.value = resourcesData.resources
    Fetchers.value = typesData.fetchers

    // Organize metadata by field_name for easy lookup
    const metaMap = {}
    resourceMetadata.fieldMetadata.forEach(m => {
      metaMap[m.fieldName] = m
    })
    paramMetadata.fieldMetadata.forEach(m => {
      metaMap[m.fieldName] = m
    })
    fieldMetadata.value = metaMap
  } catch (e) {
    error.value = 'Failed to load data: ' + e.message
  } finally {
    loading.value = false
  }
}

// Helper to get tooltip text for a field
function getTooltip(fieldName) {
  return fieldMetadata.value[fieldName]?.helpText || ''
}

// Helper to get placeholder for a field
function getPlaceholder(fieldName) {
  return fieldMetadata.value[fieldName]?.placeholder || ''
}

function addParam() {
  form.value.params.push({ key: '', value: '' })
}

function removeParam(index) {
  paramToRemove.value = index
  showRemoveParamDialog.value = true
}

function confirmRemoveParam() {
  if (paramToRemove.value !== null) {
    form.value.params.splice(paramToRemove.value, 1)
    showRemoveParamDialog.value = false
    paramToRemove.value = null
  }
}

function cancelRemoveParam() {
  showRemoveParamDialog.value = false
  paramToRemove.value = null
}

function editSource(source) {
  editingSource.value = source
  form.value = {
    name: source.name,
    publisher: source.publisher,
    fetcherId: source.fetcher.id,
    params: source.params.map(p => ({ key: p.key, value: p.value })),
    active: source.active,
    // Dataset loading settings
    enableLoad: source.enableLoad || false,
    loadMode: source.loadMode || 'replace',
    // Execution settings
    maxWorkers: source.maxWorkers || 1,
    timeoutSeconds: source.timeoutSeconds || 300,
    retryAttempts: source.retryAttempts || 0,
    retryDelaySeconds: source.retryDelaySeconds || 60,
    executionPriority: source.executionPriority || 0,
  }
  showEditModal.value = true
}

async function showPreviewData(source) {
  previewSource.value = source
  previewData.value = null
  previewError.value = null
  showPreviewModal.value = true
  loadingPreview.value = true

  try {
    const result = await previewResourceData(source.id, 10)
    previewData.value = result.previewResourceData
  } catch (e) {
    previewError.value = 'Failed to load preview data: ' + e.message
  } finally {
    loadingPreview.value = false
  }
}

function confirmDelete(source) {
  sourceToDelete.value = source
  showDeleteModal.value = true
}

async function handleDelete() {
  try {
    await deleteResource(sourceToDelete.value.id)
    showDeleteModal.value = false
    sourceToDelete.value = null
    await loadData()
  } catch (e) {
    error.value = 'Failed to delete resource: ' + e.message
  }
}

async function submitForm() {
  try {
    error.value = null
    const input = {
      name: form.value.name,
      publisher: form.value.publisher,
      fetcherId: form.value.fetcherId,
      params: form.value.params.filter(p => p.key && p.value),
      active: form.value.active,
      // Dataset loading settings
      enableLoad: form.value.enableLoad,
      loadMode: form.value.loadMode,
      // Execution settings
      maxWorkers: form.value.maxWorkers,
      timeoutSeconds: form.value.timeoutSeconds,
      retryAttempts: form.value.retryAttempts,
      retryDelaySeconds: form.value.retryDelaySeconds,
      executionPriority: form.value.executionPriority,
    }

    if (showCreateModal.value) {
      await createResource(input)
    } else {
      await updateResource(editingSource.value.id, input)
    }

    closeModals()
    await loadData()
  } catch (e) {
    error.value = 'Failed to save resource: ' + e.message
  }
}

function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  editingSource.value = null
  form.value = {
    name: '',
    publisher: '',
    fetcherId: '',
    params: [],
    active: true,
    // Dataset loading settings
    enableLoad: false,
    loadMode: 'replace',
    // Execution settings
    maxWorkers: 1,
    timeoutSeconds: 300,
    retryAttempts: 0,
    retryDelaySeconds: 60,
    executionPriority: 0,
  }
}

onMounted(() => {
  loadData()
})
</script>
