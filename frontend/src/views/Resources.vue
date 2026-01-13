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
      <!-- Search bar -->
      <div class="mb-4 p-4 border-b border-gray-700">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name or publisher..."
          class="input w-full"
        />
      </div>

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
            v-for="resource in filteredResources"
            :key="resource.id"
            class="border-b border-gray-700 hover:bg-gray-700 transition-colors"
          >
            <td class="py-3 px-4 font-medium">{{ resource.name }}</td>
            <td class="py-3 px-4 text-gray-400">{{ resource.publisher }}</td>
            <td class="py-3 px-4">
              <code class="text-xs bg-gray-900 px-2 py-1 rounded text-blue-400">
                {{ resource.fetcher.code }}
              </code>
            </td>
            <td class="py-3 px-4">
              <span
                :class="resource.active ? 'text-green-400' : 'text-red-400'"
                class="text-sm font-medium"
              >
                {{ resource.active ? 'Active' : 'Inactive' }}
              </span>
            </td>
            <td class="py-3 px-4">
              <div class="flex justify-end gap-2">
                <button
                  @click="showPreviewData(resource)"
                  class="btn btn-primary text-sm py-1 px-3"
                >
                  Test
                </button>
                <button
                  @click="editResource(resource)"
                  class="btn btn-secondary text-sm py-1 px-3"
                >
                  Edit
                </button>
                <button
                  @click="confirmDelete(resource)"
                  class="btn btn-danger text-sm py-1 px-3"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="filteredResources.length === 0" class="text-gray-400 text-center py-8">
        <span v-if="searchQuery">No resources match your search.</span>
        <span v-else>No resources configured yet. Click "Create Resource" to add one.</span>
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
              <label class="block text-xs font-medium mb-1">Fetcher Type</label>
            </Tooltip>
            <select v-model="form.fetcherId" required class="input w-full text-sm">
              <option value="">Select a type...</option>
              <option
                v-for="type in fetchers"
                :key="type.id"
                :value="type.id"
              >
                {{ type.code }} - {{ type.description }}
              </option>
            </select>
          </div>

          <div>
            <!-- Tabs for Parameters and Concurrency -->
            <div class="flex space-x-1 mb-4 border-b border-gray-600">
              <button
                type="button"
                @click="activeParamTab = 'parameters'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeParamTab === 'parameters'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Parameters
              </button>
              <button
                type="button"
                @click="activeParamTab = 'concurrency'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeParamTab === 'concurrency'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Concurrency & Parallelism
              </button>
            </div>

            <!-- Tab Content: Parameters -->
            <div v-if="activeParamTab === 'parameters'" class="h-[400px] overflow-y-auto pr-2">
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
                    <select
                      v-if="param.dataType === 'enum' && param.enumValues"
                      :value="getParamValue(param.paramName)"
                      @change="updateParamValue(param.paramName, $event.target.value)"
                      class="input w-full text-xs"
                    >
                      <option value="">Select...</option>
                      <option v-for="val in param.enumValues" :key="val" :value="val">{{ val }}</option>
                    </select>
                    <input
                      v-else
                      :value="getParamValue(param.paramName)"
                      type="text"
                      :placeholder="param.defaultValue || `Enter ${param.paramName}...`"
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
                    <select
                      v-if="getParamType(paramName) === 'enum' && getParamEnumValues(paramName)"
                      :value="getParamValue(paramName)"
                      @change="updateParamValue(paramName, $event.target.value)"
                      class="input w-full text-xs"
                    >
                      <option value="">Select...</option>
                      <option v-for="val in getParamEnumValues(paramName)" :key="val" :value="val">{{ val }}</option>
                    </select>
                    <input
                      v-else
                      :value="getParamValue(paramName)"
                      type="text"
                      :placeholder="getParamDefaultValue(paramName) || `Enter ${paramName}...`"
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

            <!-- Tab Content: Concurrency & Parallelism -->
            <div v-if="activeParamTab === 'concurrency'" class="h-[400px] overflow-y-auto pr-2">
              <div class="space-y-4">
                <!-- Number of Workers -->
                <div>
                  <Tooltip text="Controls how many parallel workers will process this resource. 1 = sequential processing, >1 = parallel processing with multiple workers.">
                    <label class="block text-sm font-medium mb-2">
                      Number of Workers
                    </label>
                  </Tooltip>
                  <input
                    v-model.number="form.numWorkers"
                    type="number"
                    min="1"
                    max="20"
                    class="input w-full text-sm"
                    placeholder="1"
                  />
                  <p class="text-xs text-gray-400 mt-1">
                    Parallel workers for processing (1 = sequential, >1 = parallel)
                  </p>
                  <p class="text-xs text-yellow-400 mt-1" v-if="form.numWorkers > 10">
                    ⚠️ Using more than 10 workers may cause performance issues
                  </p>
                </div>

                <!-- Max Concurrent Requests -->
                <div>
                  <Tooltip text="Maximum number of simultaneous HTTP requests that can be made to the API at once. Lower values are safer for rate-limited APIs.">
                    <label class="block text-sm font-medium mb-2">
                      Max Concurrent Requests
                    </label>
                  </Tooltip>
                  <input
                    v-model.number="form.maxConcurrentRequests"
                    type="number"
                    min="1"
                    max="50"
                    class="input w-full text-sm"
                    placeholder="5"
                  />
                  <p class="text-xs text-gray-400 mt-1">
                    Maximum simultaneous HTTP requests (default: 5)
                  </p>
                </div>

                <!-- Rate Limit per Second -->
                <div>
                  <Tooltip text="Maximum number of requests per second allowed to the API. Helps prevent hitting API rate limits and getting blocked.">
                    <label class="block text-sm font-medium mb-2">
                      Rate Limit (requests/second)
                    </label>
                  </Tooltip>
                  <input
                    v-model.number="form.rateLimitPerSecond"
                    type="number"
                    min="1"
                    max="100"
                    class="input w-full text-sm"
                    placeholder="10"
                  />
                  <p class="text-xs text-gray-400 mt-1">
                    Maximum requests per second to the API (default: 10)
                  </p>
                </div>

                <!-- Request Delay -->
                <div>
                  <Tooltip text="Fixed delay in milliseconds between consecutive requests. Use this for APIs that require spacing between calls. 0 = no delay.">
                    <label class="block text-sm font-medium mb-2">
                      Request Delay (milliseconds)
                    </label>
                  </Tooltip>
                  <input
                    v-model.number="form.requestDelayMs"
                    type="number"
                    min="0"
                    max="5000"
                    class="input w-full text-sm"
                    placeholder="0"
                  />
                  <p class="text-xs text-gray-400 mt-1">
                    Delay between consecutive requests in milliseconds (default: 0)
                  </p>
                </div>

                <!-- Retry Attempts -->
                <div>
                  <Tooltip text="Number of times to retry a failed request before giving up. 0 = no retries, higher values are more resilient to temporary failures.">
                    <label class="block text-sm font-medium mb-2">
                      Retry Attempts
                    </label>
                  </Tooltip>
                  <input
                    v-model.number="form.retryAttempts"
                    type="number"
                    min="0"
                    max="10"
                    class="input w-full text-sm"
                    placeholder="3"
                  />
                  <p class="text-xs text-gray-400 mt-1">
                    Number of retry attempts on failure (default: 3)
                  </p>
                </div>

                <!-- Retry Backoff Factor -->
                <div>
                  <Tooltip text="Exponential backoff multiplier for retry delays. For example, with factor 2.0: first retry waits 2s, second waits 4s, third waits 8s. Higher values = longer waits between retries.">
                    <label class="block text-sm font-medium mb-2">
                      Retry Backoff Factor
                    </label>
                  </Tooltip>
                  <input
                    v-model.number="form.retryBackoffFactor"
                    type="number"
                    min="1"
                    max="5"
                    step="0.1"
                    class="input w-full text-sm"
                    placeholder="2.0"
                  />
                  <p class="text-xs text-gray-400 mt-1">
                    Exponential backoff multiplier for retries (default: 2.0)
                  </p>
                </div>

                <!-- Batch Size -->
                <div>
                  <Tooltip text="Number of records to process in each batch when paginating through large datasets. Smaller batches = more API calls but less memory usage. Larger batches = fewer API calls but more memory.">
                    <label class="block text-sm font-medium mb-2">
                      Batch Size
                    </label>
                  </Tooltip>
                  <input
                    v-model.number="form.batchSize"
                    type="number"
                    min="1"
                    max="10000"
                    class="input w-full text-sm"
                    placeholder="100"
                  />
                  <p class="text-xs text-gray-400 mt-1">
                    Number of records per batch for pagination (default: 100)
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div class="flex items-center">
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
          Are you sure you want to delete resource "{{ resourceToDelete?.name }}"?
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
          <h2 class="text-2xl font-bold">Test Result - {{ previewResource?.name }}</h2>
          <button @click="showPreviewModal = false" class="text-gray-400 hover:text-white text-2xl">
            ×
          </button>
        </div>

        <div v-if="loadingPreview" class="text-gray-400 text-center py-8">
          Testing resource... Fetching up to 100 records
        </div>

        <div v-else-if="previewError" class="p-4 bg-red-900 border border-red-700 rounded text-red-200 mb-4">
          {{ previewError }}
        </div>

        <div v-else-if="previewData">
          <div class="mb-4 text-sm text-gray-400">
            Showing first {{ getRecordCount(previewData) }} record(s)
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
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import Tooltip from '../components/Tooltip.vue'
import {
  fetchResources,
  fetchFetchers,
  fetchFieldMetadata,
  createResource,
  updateResource,
  deleteResource,
  previewResourceData,
} from '../api/graphql'

const resources = ref([])
const fetchers = ref([])
const fieldMetadata = ref({}) // Metadata for tooltips
const loading = ref(true)
const error = ref(null)
const searchQuery = ref('')

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const showPreviewModal = ref(false)
const resourceToDelete = ref(null)
const editingResource = ref(null)
const previewResource = ref(null)
const previewData = ref(null)
const loadingPreview = ref(false)
const previewError = ref(null)

const form = ref({
  name: '',
  publisher: '',
  fetcherId: '',
  params: [],
  active: true,
  numWorkers: 1,
  maxConcurrentRequests: null,
  rateLimitPerSecond: null,
  requestDelayMs: null,
  retryAttempts: null,
  retryBackoffFactor: null,
  batchSize: null,
})

const activeParamTab = ref('parameters')

// Computed property for selected fetcher
const selectedFetcher = computed(() => {
  if (!fetchers.value || fetchers.value.length === 0) return null
  return fetchers.value.find(type => type.id === form.value.fetcherId)
})

// Computed property for required parameters
const requiredParams = computed(() => {
  if (!selectedFetcher.value || !selectedFetcher.value.paramsDef) {
    return []
  }
  return selectedFetcher.value.paramsDef.filter(param => param.required === true)
})

// Computed property for optional parameters
const optionalParams = computed(() => {
  if (!selectedFetcher.value || !selectedFetcher.value.paramsDef) {
    return []
  }
  return selectedFetcher.value.paramsDef.filter(param => param.required !== true)
})

// Computed property for added optional parameters
const addedOptionalParams = computed(() => {
  const allRequired = requiredParams.value.map(p => p.paramName)
  return form.value.params
    .map(p => p.key)
    .filter(key => !allRequired.includes(key))
})

// Computed property for available optional parameters
const availableOptionalParams = computed(() => {
  const currentParamNames = form.value.params.map(p => p.key)
  return optionalParams.value.filter(param => !currentParamNames.includes(param.paramName))
})

// Computed property to filter resources based on search query
const filteredResources = computed(() => {
  if (!searchQuery.value) {
    return resources.value
  }

  const query = searchQuery.value.toLowerCase()
  return resources.value.filter(resource =>
    resource.name.toLowerCase().includes(query) ||
    resource.publisher.toLowerCase().includes(query)
  )
})

const selectedOptionalParam = ref('')

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
    resources.value = resourcesData.resources
    fetchers.value = typesData.fetchers

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

// Helper functions for parameters
function getParamValue(paramName) {
  const param = form.value.params.find(p => p.key === paramName)
  return param ? param.value : ''
}

function getParamType(paramName) {
  const param = optionalParams.value.find(p => p.paramName === paramName)
  return param ? param.dataType : 'string'
}

function getParamEnumValues(paramName) {
  const param = optionalParams.value.find(p => p.paramName === paramName)
  return param ? param.enumValues : null
}

function getParamDefaultValue(paramName) {
  // Check required params first
  const requiredParam = requiredParams.value.find(p => p.paramName === paramName)
  if (requiredParam && requiredParam.defaultValue) {
    return requiredParam.defaultValue
  }

  // Then check optional params
  const optionalParam = optionalParams.value.find(p => p.paramName === paramName)
  if (optionalParam && optionalParam.defaultValue) {
    return optionalParam.defaultValue
  }

  return null
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
    // Use defaultValue from parameter definition instead of empty string
    const defaultValue = getParamDefaultValue(paramName) || ''
    form.value.params.push({ key: paramName, value: defaultValue })
  }

  selectedOptionalParam.value = ''
}

function removeOptionalParam(paramName) {
  const index = form.value.params.findIndex(p => p.key === paramName)
  if (index !== -1) {
    form.value.params.splice(index, 1)
  }
}

function editResource(resource) {
  editingResource.value = resource

  // Helper to extract concurrency params
  const getParam = (key, defaultValue = null) => {
    const param = resource.params.find(p => p.key === key)
    return param ? (defaultValue === null ? param.value : parseInt(param.value)) : defaultValue
  }

  // Extract concurrency parameters
  const concurrencyKeys = [
    'num_workers',
    'max_concurrent_requests',
    'rate_limit_per_second',
    'request_delay_ms',
    'retry_attempts',
    'retry_backoff_factor',
    'batch_size'
  ]

  // Filter out concurrency params from regular params
  const regularParams = resource.params.filter(p => !concurrencyKeys.includes(p.key))

  form.value = {
    name: resource.name,
    publisher: resource.publisher,
    fetcherId: resource.fetcher.id,
    params: regularParams.map(p => ({ key: p.key, value: p.value })),
    active: resource.active,
    numWorkers: parseInt(getParam('num_workers', 1)),
    maxConcurrentRequests: getParam('max_concurrent_requests') ? parseInt(getParam('max_concurrent_requests')) : null,
    rateLimitPerSecond: getParam('rate_limit_per_second') ? parseInt(getParam('rate_limit_per_second')) : null,
    requestDelayMs: getParam('request_delay_ms') ? parseInt(getParam('request_delay_ms')) : null,
    retryAttempts: getParam('retry_attempts') ? parseInt(getParam('retry_attempts')) : null,
    retryBackoffFactor: getParam('retry_backoff_factor') ? parseFloat(getParam('retry_backoff_factor')) : null,
    batchSize: getParam('batch_size') ? parseInt(getParam('batch_size')) : null,
  }
  showEditModal.value = true
}

async function showPreviewData(resource) {
  previewResource.value = resource
  previewData.value = null
  previewError.value = null
  showPreviewModal.value = true
  loadingPreview.value = true

  try {
    const result = await previewResourceData(resource.id, 100)
    previewData.value = result.previewResourceData
  } catch (e) {
    previewError.value = 'Failed to load preview data: ' + e.message
  } finally {
    loadingPreview.value = false
  }
}

function getRecordCount(data) {
  if (!data) return 0

  // If it's an array, check if first element has a 'content' array
  if (Array.isArray(data)) {
    if (data.length > 0 && data[0].content && Array.isArray(data[0].content)) {
      return data[0].content.length
    }
    return data.length
  }

  // If it's an object with a 'content' array property
  if (typeof data === 'object' && data.content && Array.isArray(data.content)) {
    return data.content.length
  }

  // Regular object
  if (typeof data === 'object') return Object.keys(data).length > 0 ? 1 : 0

  return 1
}

function confirmDelete(resource) {
  resourceToDelete.value = resource
  showDeleteModal.value = true
}

async function handleDelete() {
  try {
    await deleteResource(resourceToDelete.value.id)
    showDeleteModal.value = false
    resourceToDelete.value = null
    await loadData()
  } catch (e) {
    error.value = 'Failed to delete resource: ' + e.message
  }
}

async function submitForm() {
  try {
    error.value = null

    // Combine regular params with concurrency params
    const allParams = [...form.value.params.filter(p => p.key && p.value)]

    // Add concurrency params if not default/null
    const concurrencyParams = {
      'num_workers': { value: form.value.numWorkers, default: 1 },
      'max_concurrent_requests': { value: form.value.maxConcurrentRequests, default: null },
      'rate_limit_per_second': { value: form.value.rateLimitPerSecond, default: null },
      'request_delay_ms': { value: form.value.requestDelayMs, default: null },
      'retry_attempts': { value: form.value.retryAttempts, default: null },
      'retry_backoff_factor': { value: form.value.retryBackoffFactor, default: null },
      'batch_size': { value: form.value.batchSize, default: null },
    }

    for (const [key, config] of Object.entries(concurrencyParams)) {
      const value = config.value
      const defaultValue = config.default

      if (value !== null && value !== defaultValue) {
        allParams.push({ key, value: String(value) })
      }
    }

    const input = {
      name: form.value.name,
      publisher: form.value.publisher,
      fetcherId: form.value.fetcherId,
      params: allParams,
      active: form.value.active,
    }

    if (showCreateModal.value) {
      await createResource(input)
    } else {
      await updateResource(editingResource.value.id, input)
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
  editingResource.value = null
  activeParamTab.value = 'parameters'
  form.value = {
    name: '',
    publisher: '',
    fetcherId: '',
    params: [],
    active: true,
    numWorkers: 1,
    maxConcurrentRequests: null,
    rateLimitPerSecond: null,
    requestDelayMs: null,
    retryAttempts: null,
    retryBackoffFactor: null,
    batchSize: null,
  }
}

onMounted(() => {
  loadData()
})
</script>
