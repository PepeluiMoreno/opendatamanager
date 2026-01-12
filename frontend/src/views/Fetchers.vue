<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Fetchers</h1>
      <button
        @click="showCreateModal = true"
        class="btn btn-primary"
      >
        Add Fetcher
      </button>
    </div>

    <!-- Fetcher Types List -->
    <div class="card">
      <div v-if="loading" class="text-center py-8">
        <div class="text-gray-400">Loading fetchers...</div>
      </div>
      
      <div v-else-if="error" class="text-center py-8 text-red-400">
        {{ error }}
      </div>
      
      <div v-else-if="Fetchers.length === 0" class="text-center py-8 text-gray-400">
        No fetchers configured yet
      </div>
      
      <div v-else class="space-y-4">
        <div
          v-for="Fetcher in Fetchers"
          :key="Fetcher.id"
          class="border border-gray-600 rounded p-6"
        >
          <div class="flex justify-between items-start">
            <div class="flex-1">
              <div class="flex items-center space-x-3 mb-2">
                <h3 class="text-xl font-semibold">{{ Fetcher.description }}</h3>
              </div>
              <div class="text-sm text-gray-500 mb-3">
              {{ Fetcher.paramsDef?.length || 0 }} parameters configured
            </div>
              <div class="text-sm text-gray-400">
                <div><strong>Parameters:</strong> {{ Fetcher.paramsDef?.length || 0 }} configured</div>
                <div><strong>Resources using this fetcher:</strong> {{ Fetcher.resources?.length || 0 }}</div>
              </div>
            </div>
            
            <div class="flex space-x-2 ml-4">
              <button
                @click="editFetcher(Fetcher)"
                class="btn btn-secondary text-sm"
              >
                Edit
              </button>
              <button
                @click="deleteFetcher(Fetcher)"
                :disabled="Fetcher.resources?.length > 0"
                class="btn btn-danger text-sm"
                :title="Fetcher.resources?.length > 0 ? 'Cannot delete fetcher with resources' : ''"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <CreateEditFetcherModal
      v-if="showCreateModal"
      :Fetcher="editingFetcher"
      @close="closeModal"
      @saved="onSaved"
    />

    <!-- Error Display -->
    <transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0 transform translate-y-2"
      enter-to-class="opacity-100 transform translate-y-0"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="errorMessage" class="mt-4 p-4 bg-red-900 border border-red-700 rounded text-red-200">
        {{ errorMessage }}
      </div>
    </transition>

    <!-- Success Display -->
    <transition
      enter-active-class="transition ease-out duration-300"
      enter-from-class="opacity-0 transform translate-y-2"
      enter-to-class="opacity-100 transform translate-y-0"
      leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="successMessage" class="mt-4 p-4 bg-green-900 border border-green-700 rounded text-green-200 flex items-center justify-between">
        <span>{{ successMessage }}</span>
        <button @click="successMessage = null" class="text-green-400 hover:text-green-200 ml-4">
          ×
        </button>
      </div>
    </transition>

    <!-- Confirm Delete Dialog -->
    <ConfirmDialog
      v-if="showDeleteDialog"
      title="Delete Fetcher"
      :message="`Are you sure you want to delete fetcher '${fetcherToDelete?.name || fetcherToDelete?.description}'? ${fetcherToDelete?.resources?.length > 0 ? 'This fetcher is being used by ' + fetcherToDelete.resources.length + ' resource(s).' : ''}`"
      confirm-text="Delete"
      cancel-text="Cancel"
      @confirm="confirmDeleteFetcher"
      @cancel="cancelDeleteFetcher"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchFetchers, createFetcher, updateFetcher, deleteFetcher as deleteFetcherAPI } from '../api/graphql'
import CreateEditFetcherModal from '../components/CreateEditFetcherModal.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const Fetchers = ref([])
const loading = ref(false)
const error = ref(null)
const errorMessage = ref(null)
const successMessage = ref(null)

// Modal states
const showCreateModal = ref(false)
const showDeleteDialog = ref(false)
const editingFetcher = ref(null)
const fetcherToDelete = ref(null)

async function loadFetchers() {
  try {
    loading.value = true
    error.value = null
    const data = await fetchFetchers()
    Fetchers.value = data.fetchers || []
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

function editFetcher(Fetcher) {
  editingFetcher.value = { ...Fetcher }
  showCreateModal.value = true
}

function deleteFetcher(Fetcher) {
  fetcherToDelete.value = Fetcher
  showDeleteDialog.value = true
}

async function confirmDeleteFetcher() {
  if (!fetcherToDelete.value) return

  try {
    await deleteFetcherAPI(fetcherToDelete.value.id)
    successMessage.value = `Fetcher "${fetcherToDelete.value.name || fetcherToDelete.value.description}" deleted successfully`
    showDeleteDialog.value = false
    fetcherToDelete.value = null
    loadFetchers()

    // Auto-hide success message after 3 seconds
    setTimeout(() => {
      successMessage.value = null
    }, 3000)
  } catch (e) {
    errorMessage.value = `Failed to delete fetcher: ${e.message}`
    showDeleteDialog.value = false
    fetcherToDelete.value = null
  }
}

function cancelDeleteFetcher() {
  showDeleteDialog.value = false
  fetcherToDelete.value = null
}

function closeModal() {
  showCreateModal.value = false
  editingFetcher.value = null
  errorMessage.value = null
}

function onSaved(message) {
  successMessage.value = message
  closeModal()
  loadFetchers()

  // Auto-hide success message after 3 seconds
  setTimeout(() => {
    successMessage.value = null
  }, 3000)
}

onMounted(() => {
  loadFetchers()
})
</script>