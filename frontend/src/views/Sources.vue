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
                {{ source.fetcher.code }}
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
              <label class="block text-xs font-medium mb-1">Fetcher Type</label>
            </Tooltip>
            <select v-model="form.fetcherTypeId" required class="input w-full text-sm">
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
            <div class="flex items-center justify-between mb-2">
              <label class="block text-xs font-medium">Parameters</label>
              <button
                type="button"
                @click="addParam"
                class="btn btn-secondary text-xs py-1 px-2"
              >
                + Add
              </button>
            </div>

            <!-- Header row -->
            <div v-if="form.params.length > 0" class="flex gap-2 mb-1 text-xs text-gray-400 px-2">
              <div class="w-1/5 flex-shrink-0">Key</div>
              <div class="flex-1 min-w-0">Value</div>
              <div class="w-12 flex-shrink-0"></div>
            </div>

            <!-- Parameter rows -->
            <div class="space-y-1">
              <div
                v-for="(param, index) in form.params"
                :key="index"
                class="flex gap-2 items-start border border-gray-700 rounded p-2 hover:border-gray-600"
              >
                <div class="w-1/5 flex-shrink-0">
                  <input
                    v-model="param.key"
                    type="text"
                    placeholder="e.g., url, confesion..."
                    class="input w-full text-xs"
                  />
                </div>
                <div class="flex-1 min-w-0">
                  <input
                    v-model="param.value"
                    type="text"
                    :placeholder="getPlaceholder(param.key) || 'Enter value...'"
                    class="input w-full text-xs"
                  />
                </div>
                <div class="w-12 flex-shrink-0 flex items-center justify-center gap-1">
                  <div v-if="getTooltip(param.key)" class="relative">
                    <Tooltip :text="getTooltip(param.key)">
                      <span class="text-gray-400 text-xs cursor-help">ℹ️</span>
                    </Tooltip>
                  </div>
                  <button
                    type="button"
                    @click="removeParam(index)"
                    class="text-red-400 hover:text-red-300"
                    title="Remove"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import Tooltip from '../components/Tooltip.vue'
import {
  fetchResources,
  fetchfetchers,
  fetchFieldMetadata,
  createResource,
  updateResource,
  deleteResource,
  previewResourceData,
} from '../api/graphql'

const sources = ref([])
const fetchers = ref([])
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
  fetcherTypeId: '',
  params: [],
  active: true,
})

async function loadData() {
  try {
    loading.value = true
    error.value = null
    const [resourcesData, typesData, resourceMetadata, paramMetadata] = await Promise.all([
      fetchResources(false),
      fetchfetchers(),
      fetchFieldMetadata('resource'),
      fetchFieldMetadata('resource_param'),
    ])
    sources.value = resourcesData.resources
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

function addParam() {
  form.value.params.push({ key: '', value: '' })
}

function removeParam(index) {
  const param = form.value.params[index]
  const paramName = param.key || 'this parameter'
  if (confirm(`Are you sure you want to remove "${paramName}"?`)) {
    form.value.params.splice(index, 1)
  }
}

function editSource(source) {
  editingSource.value = source
  form.value = {
    name: source.name,
    publisher: source.publisher,
    fetcherTypeId: source.fetcherType.id,
    params: source.params.map(p => ({ key: p.key, value: p.value })),
    active: source.active,
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
      fetcherTypeId: form.value.fetcherTypeId,
      params: form.value.params.filter(p => p.key && p.value),
      active: form.value.active,
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
    fetcherTypeId: '',
    params: [],
    active: true,
  }
}

onMounted(() => {
  loadData()
})
</script>
