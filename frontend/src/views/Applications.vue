<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-8">
      <h1 class="text-3xl font-bold">Applications</h1>
      <button @click="showCreateModal = true" class="btn btn-primary">
        + Create Application
      </button>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-8">
      Loading...
    </div>

    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div
        v-for="app in applications"
        :key="app.id"
        class="card hover:border-gray-600 transition-colors"
      >
        <div class="flex items-start justify-between mb-4">
          <div>
            <h3 class="text-xl font-bold text-purple-400">{{ app.name }}</h3>
            <p v-if="app.description" class="text-sm text-gray-400 mt-1">
              {{ app.description }}
            </p>
          </div>
          <span
            :class="app.active ? 'text-green-400' : 'text-red-400'"
            class="text-sm font-medium"
          >
            {{ app.active ? 'Active' : 'Inactive' }}
          </span>
        </div>

        <div class="space-y-1 text-sm mb-4">
          <div class="flex items-center gap-2">
            <span class="text-gray-400">Consumption:</span>
            <span
              :class="{
                'bg-blue-900 text-blue-300':     app.consumptionMode === 'graphql',
                'bg-purple-900 text-purple-300': app.consumptionMode === 'webhook',
                'bg-teal-900 text-teal-300':     app.consumptionMode === 'both',
              }"
              class="text-xs font-mono px-2 py-0.5 rounded"
            >{{ app.consumptionMode === 'both' ? 'webhook + graphql' : app.consumptionMode }}</span>
          </div>
          <div v-if="app.webhookUrl" class="text-xs text-gray-500 break-all">{{ app.webhookUrl }}</div>
        </div>

        <div class="flex space-x-2">
          <button @click="editApplication(app)" class="btn btn-secondary text-sm py-1 px-3">
            Edit
          </button>
          <button @click="confirmDelete(app)" class="btn btn-danger text-sm py-1 px-3">
            Delete
          </button>
        </div>
      </div>
    </div>

    <div v-if="!loading && applications.length === 0" class="text-gray-400 text-center py-8">
      No applications configured yet. Click "Create Application" to add one.
    </div>

    <!-- Create/Edit Modal -->
    <div
      v-if="showCreateModal || showEditModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModals"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 class="text-2xl font-bold mb-4">
          {{ showCreateModal ? 'Create Application' : 'Edit Application' }}
        </h2>

        <form @submit.prevent="submitForm" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">Name</label>
            <input v-model="form.name" type="text" required class="input w-full" />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Description</label>
            <textarea v-model="form.description" rows="3" class="input w-full"></textarea>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Webhook URL</label>
            <input
              v-model="form.webhookUrl"
              type="url"
              class="input w-full"
              placeholder="https://your-app/odmgr-webhook"
            />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2 flex items-center gap-2">
              Consumption Mode
              <button type="button" @click="showModeInfo = true"
                class="text-gray-500 hover:text-blue-400 transition-colors text-xs border border-gray-600 hover:border-blue-500 rounded-full w-4 h-4 flex items-center justify-center leading-none">?</button>
            </label>
            <div class="grid grid-cols-3 gap-2">
              <label
                v-for="opt in consumptionModes"
                :key="opt.value"
                :class="[
                  'flex flex-col items-start p-3 rounded border cursor-pointer transition-colors',
                  form.consumptionMode === opt.value
                    ? 'border-purple-500 bg-purple-900/30'
                    : 'border-gray-600 hover:border-gray-500',
                ]"
              >
                <input type="radio" v-model="form.consumptionMode" :value="opt.value" class="sr-only" />
                <span class="text-sm font-mono font-semibold">{{ opt.value }}</span>
                <span class="text-xs text-gray-400 mt-1">{{ opt.label }}</span>
              </label>
            </div>
            <p class="text-xs text-gray-500 mt-2">
              <template v-if="form.consumptionMode === 'webhook'">
                ODMGR posts the full dataset metadata and JSONL download URL. Your app downloads the file and runs its ETL.
              </template>
              <template v-else-if="form.consumptionMode === 'graphql'">
                ODMGR sends a lightweight ping. Your app then queries <code class="text-green-400">/graphql/data</code> to fetch exactly what it needs.
              </template>
              <template v-else>
                Your app receives both the full JSONL payload and the GraphQL reference.
              </template>
            </p>
          </div>

          <div class="flex items-center">
            <input v-model="form.active" type="checkbox" id="app-active" class="mr-2" />
            <label for="app-active" class="text-sm">Active</label>
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button type="button" @click="closeModals" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">
              {{ showCreateModal ? 'Create' : 'Update' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Consumption Mode Info Modal -->
    <div v-if="showModeInfo"
         class="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50"
         @click.self="showModeInfo = false">
      <div class="bg-gray-800 rounded-xl shadow-2xl border border-gray-700 w-full max-w-lg p-6 space-y-4">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-bold text-white">How does Consumption Mode work?</h3>
          <button @click="showModeInfo = false" class="text-gray-400 hover:text-white text-xl leading-none">×</button>
        </div>

        <p class="text-sm text-gray-300">
          When ODMGR completes an execution, it fires a <span class="text-purple-300 font-semibold">webhook</span>
          to each subscribed application. The <code class="text-green-400">consumption_mode</code> determines
          what that notification contains.
        </p>

        <div class="space-y-3">
          <div class="rounded-lg border border-purple-700/50 bg-purple-900/20 p-3">
            <p class="text-sm font-mono font-semibold text-purple-300 mb-1">webhook</p>
            <p class="text-xs text-gray-300">
              The POST includes full dataset metadata and the JSONL download URL.
              Your app downloads the file directly and runs its ETL. Best if you don't want to depend on GraphQL.
            </p>
          </div>
          <div class="rounded-lg border border-blue-700/50 bg-blue-900/20 p-3">
            <p class="text-sm font-mono font-semibold text-blue-300 mb-1">graphql</p>
            <p class="text-xs text-gray-300">
              The POST is a lightweight trigger: "new data available for resource X". Your app uses it
              to query <code class="text-green-400">/graphql/data</code> and request exactly what it needs.
              More flexible for apps with complex queries.
            </p>
          </div>
          <div class="rounded-lg border border-teal-700/50 bg-teal-900/20 p-3">
            <p class="text-sm font-mono font-semibold text-teal-300 mb-1">both</p>
            <p class="text-xs text-gray-300">
              Your app receives both the full JSONL payload and the GraphQL reference. Useful during
              migrations or when different modules consume data differently.
            </p>
          </div>
        </div>

        <div class="rounded-lg bg-gray-700/40 p-3 text-xs text-gray-400">
          <p class="font-semibold text-gray-300 mb-1">Typical flow with GSH:</p>
          <p>ODMGR completes execution → fires webhook to GSH → GSH receives ping → GSH queries
          <code class="text-green-400">/graphql/data</code> → GSH runs its ETL with fresh data.</p>
        </div>

        <div class="flex justify-end">
          <button @click="showModeInfo = false" class="btn btn-secondary text-sm">Got it</button>
        </div>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="showDeleteModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showDeleteModal = false"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-2xl font-bold mb-4">Delete Application</h2>
        <p class="mb-6">
          Are you sure you want to delete <strong class="text-purple-300">{{ appToDelete?.name }}</strong>?
          The subscriptions and notifications associated with this application will also be deleted.
        </p>

        <label class="flex items-start gap-2 mb-6 cursor-pointer">
          <input type="checkbox" v-model="hardDeleteFlag" class="accent-red-500 mt-0.5" />
          <span class="text-sm text-gray-300">Permanently delete</span>
        </label>

        <div class="flex justify-end space-x-2">
          <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="handleDelete" class="btn btn-danger">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  fetchApplications,
  createApplication,
  updateApplication,
  deleteApplication,
} from '../api/graphql'

const applications = ref([])
const loading = ref(true)
const error = ref(null)

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const showModeInfo = ref(false)
const appToDelete = ref(null)
const editingApp = ref(null)
const hardDeleteFlag = ref(false)

const consumptionModes = [
  { value: 'webhook', label: 'Download JSONL via webhook' },
  { value: 'graphql', label: 'Query GraphQL API' },
  { value: 'both',    label: 'Both modes' },
]

const form = ref({
  name: '',
  description: '',
  webhookUrl: '',
  consumptionMode: 'webhook',
  active: true,
})

async function loadData() {
  try {
    loading.value = true
    error.value = null
    const data = await fetchApplications()
    applications.value = data.applications
  } catch (e) {
    error.value = 'Failed to load applications: ' + e.message
  } finally {
    loading.value = false
  }
}

function editApplication(app) {
  editingApp.value = app
  form.value = {
    name: app.name,
    description: app.description || '',
    webhookUrl: app.webhookUrl || '',
    consumptionMode: app.consumptionMode || 'webhook',
    active: app.active,
  }
  showEditModal.value = true
}

function confirmDelete(app) {
  appToDelete.value = app
  hardDeleteFlag.value = false
  showDeleteModal.value = true
}

async function handleDelete() {
  try {
    await deleteApplication(appToDelete.value.id, hardDeleteFlag.value)
    showDeleteModal.value = false
    appToDelete.value = null
    await loadData()
  } catch (e) {
    error.value = 'Failed to delete application: ' + e.message
  }
}

async function submitForm() {
  try {
    error.value = null
    const input = {
      name: form.value.name,
      description: form.value.description,
      webhookUrl: form.value.webhookUrl || null,
      consumptionMode: form.value.consumptionMode,
      active: form.value.active,
    }

    if (showCreateModal.value) {
      await createApplication(input)
    } else {
      await updateApplication(editingApp.value.id, input)
    }

    closeModals()
    await loadData()
  } catch (e) {
    error.value = 'Failed to save application: ' + e.message
  }
}

function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  editingApp.value = null
  form.value = {
    name: '',
    description: '',
    webhookUrl: '',
    consumptionMode: 'webhook',
    active: true,
  }
}

onMounted(() => {
  loadData()
})
</script>
