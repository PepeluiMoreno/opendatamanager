<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-8">
      <h1 class="text-3xl font-bold">Tipos de Servicio Web</h1>
      <div class="flex space-x-3">
        <button @click="showCreateModal" class="btn btn-primary">
          + Nuevo Tipo de Servicio
        </button>
        <button @click="loadData" class="btn btn-secondary">
          Actualizar
        </button>
      </div>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-8">
      Loading...
    </div>

    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <FetcherTypeCard
        v-for="type in fetcherTypes"
        :key="type.id"
        :fetcher-type="type"
        :sources-count="getSourcesCount(type.id)"
        @select="showTypeDetails(type)"
      />
    </div>

    <div v-if="!loading && fetcherTypes.length === 0" class="text-gray-400 text-center py-8">
      No hay tipos de servicio configurados todavía
    </div>

    <!-- Type Details Modal -->
    <div
      v-if="selectedType"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="selectedType = null"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-start justify-between mb-6">
          <div>
            <h2 class="text-2xl font-bold text-blue-400">{{ selectedType.code }}</h2>
            <p class="text-sm text-gray-400 mt-1">{{ selectedType.id }}</p>
          </div>
          <div class="flex items-center space-x-2">
            <button @click="editType(selectedType)" class="btn btn-secondary text-sm">
              Edit
            </button>
            <button @click="confirmDelete(selectedType)" class="btn bg-red-800 hover:bg-red-700 text-sm">
              Delete
            </button>
            <button @click="selectedType = null" class="text-gray-400 hover:text-white text-2xl ml-2">
              ×
            </button>
          </div>
        </div>

        <div class="space-y-4">
          <div v-if="selectedType.description">
            <h3 class="font-bold mb-2">Description:</h3>
            <p class="text-gray-300">{{ selectedType.description }}</p>
          </div>

          <div>
            <h3 class="font-bold mb-2">Sources using this type:</h3>
            <div v-if="getSourcesByType(selectedType.id).length > 0" class="space-y-2">
              <router-link
                v-for="source in getSourcesByType(selectedType.id)"
                :key="source.id"
                :to="`/resources/${source.id}/test`"
                class="block p-3 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
              >
                <div class="font-medium">{{ source.name }}</div>
                <div class="text-sm text-gray-400">{{ source.publisher }}</div>
              </router-link>
            </div>
            <div v-else class="text-gray-400 text-sm">
              No sources using this type yet
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div
      v-if="showFormModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeFormModal"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl">
        <div class="flex items-start justify-between mb-6">
          <h2 class="text-2xl font-bold">{{ formMode === 'create' ? 'Nuevo Tipo de Servicio' : 'Editar Tipo de Servicio' }}</h2>
          <button @click="closeFormModal" class="text-gray-400 hover:text-white text-2xl">
            ×
          </button>
        </div>

        <form @submit.prevent="submitForm" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">Tipo de Servicio Web *</label>
            <input
              v-model="formData.code"
              type="text"
              required
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
              placeholder="e.g., API REST, SOAP, FILES, CSV"
            />
            <p class="text-xs text-gray-400 mt-1">Tipo de servicio de datos (API REST, SOAP, archivos, etc.)</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Description</label>
            <textarea
              v-model="formData.description"
              rows="3"
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
              placeholder="Describe what this fetcher type does..."
            ></textarea>
          </div>

          <!-- Advanced Section -->
          <details class="mt-4">
            <summary class="cursor-pointer text-sm text-gray-400 hover:text-white mb-2">
              Advanced Settings
            </summary>
            <div class="mt-3 p-4 bg-gray-900 rounded border border-gray-700">
              <div>
                <label class="block text-sm font-medium mb-2">Class Path *</label>
                <input
                  v-model="formData.classPath"
                  type="text"
                  required
                  class="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded focus:outline-none focus:border-blue-500 font-mono text-sm"
                  placeholder="e.g., app.fetchers.rest.RestFetcher"
                />
                <p class="text-xs text-gray-500 mt-1">Python class path for the fetcher implementation</p>
              </div>
            </div>
          </details>

          <div v-if="formError" class="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm">
            {{ formError }}
          </div>

          <div class="flex justify-end space-x-3 pt-4">
            <button type="button" @click="closeFormModal" class="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" :disabled="submitting" class="btn btn-primary">
              {{ submitting ? 'Saving...' : (formMode === 'create' ? 'Create' : 'Update') }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="deleteConfirmation"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="deleteConfirmation = null"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4">Confirm Delete</h2>
        <p class="text-gray-300 mb-4">
          Are you sure you want to delete the fetcher type <strong class="text-blue-400">{{ deleteConfirmation.code }}</strong>?
        </p>
        <div v-if="getSourcesByType(deleteConfirmation.id).length > 0" class="p-3 bg-yellow-900 border border-yellow-700 rounded text-yellow-200 text-sm mb-4">
          Warning: This fetcher type is being used by {{ getSourcesByType(deleteConfirmation.id).length }} source(s).
          You cannot delete it until all sources using it are removed or reassigned.
        </div>
        <div v-if="deleteError" class="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm mb-4">
          {{ deleteError }}
        </div>
        <div class="flex justify-end space-x-3">
          <button @click="deleteConfirmation = null" class="btn btn-secondary">
            Cancel
          </button>
          <button
            @click="handleDelete"
            :disabled="deleting || getSourcesByType(deleteConfirmation.id).length > 0"
            class="btn bg-red-800 hover:bg-red-700 disabled:opacity-50"
          >
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  fetchFetcherTypes,
  fetchResources,
  createFetcherType,
  updateFetcherType,
  deleteFetcherType
} from '../api/graphql'
import FetcherTypeCard from '../components/FetcherTypeCard.vue'

const fetcherTypes = ref([])
const sources = ref([])
const loading = ref(true)
const error = ref(null)
const selectedType = ref(null)
const showFormModal = ref(false)
const formMode = ref('create') // 'create' or 'edit'
const formData = ref({
  code: '',
  classPath: '',
  description: ''
})
const formError = ref(null)
const submitting = ref(false)
const editingTypeId = ref(null)
const deleteConfirmation = ref(null)
const deleteError = ref(null)
const deleting = ref(false)

async function loadData() {
  try {
    loading.value = true
    error.value = null
    const [typesData, resourcesData] = await Promise.all([
      fetchFetcherTypes(),
      fetchResources(false)
    ])
    fetcherTypes.value = typesData.fetcherTypes
    sources.value = resourcesData.resources
  } catch (e) {
    error.value = 'Failed to load data: ' + e.message
  } finally {
    loading.value = false
  }
}

function getSourcesCount(typeId) {
  return sources.value.filter(s => s.fetcherType.id === typeId).length
}

function getSourcesByType(typeId) {
  return sources.value.filter(s => s.fetcherType.id === typeId)
}

function showTypeDetails(type) {
  selectedType.value = type
}

function showCreateModal() {
  formMode.value = 'create'
  formData.value = {
    code: '',
    classPath: '',
    description: ''
  }
  formError.value = null
  editingTypeId.value = null
  showFormModal.value = true
}

function editType(type) {
  formMode.value = 'edit'
  formData.value = {
    code: type.code,
    classPath: type.classPath,
    description: type.description || ''
  }
  formError.value = null
  editingTypeId.value = type.id
  selectedType.value = null
  showFormModal.value = true
}

function closeFormModal() {
  showFormModal.value = false
  formData.value = { code: '', classPath: '', description: '' }
  formError.value = null
  editingTypeId.value = null
}

async function submitForm() {
  try {
    submitting.value = true
    formError.value = null

    const input = {
      code: formData.value.code,
      classPath: formData.value.classPath,
      description: formData.value.description || null
    }

    if (formMode.value === 'create') {
      await createFetcherType(input)
    } else {
      await updateFetcherType(editingTypeId.value, input)
    }

    closeFormModal()
    await loadData()
  } catch (e) {
    formError.value = e.message || 'Failed to save fetcher type'
  } finally {
    submitting.value = false
  }
}

function confirmDelete(type) {
  selectedType.value = null
  deleteConfirmation.value = type
  deleteError.value = null
}

async function handleDelete() {
  try {
    deleting.value = true
    deleteError.value = null

    await deleteFetcherType(deleteConfirmation.value.id)

    deleteConfirmation.value = null
    await loadData()
  } catch (e) {
    deleteError.value = e.message || 'Failed to delete fetcher type'
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>
