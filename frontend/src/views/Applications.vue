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

        <div class="space-y-3 text-sm mb-4">
          <div>
            <span class="text-gray-400">Models Path:</span>
            <code class="block mt-1 text-xs bg-gray-900 p-2 rounded text-green-400">
              {{ app.modelsPath }}
            </code>
          </div>

          <div>
            <span class="text-gray-400">Subscribed Projects:</span>
            <div class="flex flex-wrap gap-2 mt-2">
              <span
                v-for="project in app.subscribedProjects"
                :key="project"
                class="bg-gray-900 px-2 py-1 rounded text-blue-400"
              >
                {{ project }}
              </span>
            </div>
          </div>
        </div>

        <div class="flex space-x-2">
          <button
            @click="editApplication(app)"
            class="btn btn-secondary text-sm py-1 px-3"
          >
            Edit
          </button>
          <button
            @click="confirmDelete(app)"
            class="btn btn-danger text-sm py-1 px-3"
          >
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
            <textarea
              v-model="form.description"
              rows="3"
              class="input w-full"
            ></textarea>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Models Path</label>
            <input
              v-model="form.modelsPath"
              type="text"
              required
              class="input w-full"
              placeholder="e.g., /path/to/app/core/models"
            />
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">
              Subscribed Projects (comma-separated)
            </label>
            <input
              v-model="projectsInput"
              type="text"
              class="input w-full"
              placeholder="e.g., project1, project2, project3"
            />
            <div class="flex flex-wrap gap-2 mt-2">
              <span
                v-for="project in form.subscribedProjects"
                :key="project"
                class="bg-gray-900 px-2 py-1 rounded text-blue-400 text-sm"
              >
                {{ project }}
              </span>
            </div>
          </div>

          <div class="flex items-center">
            <input
              v-model="form.active"
              type="checkbox"
              id="app-active"
              class="mr-2"
            />
            <label for="app-active" class="text-sm">Active</label>
          </div>

          <div class="flex justify-end space-x-2 pt-4">
            <button type="button" @click="closeModals" class="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary">
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
          Are you sure you want to delete application "{{ appToDelete?.name }}"?
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
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
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
const appToDelete = ref(null)
const editingApp = ref(null)

const form = ref({
  name: '',
  description: '',
  modelsPath: '',
  subscribedProjects: [],
  active: true,
})

const projectsInput = computed({
  get: () => form.value.subscribedProjects.join(', '),
  set: (value) => {
    form.value.subscribedProjects = value
      .split(',')
      .map(p => p.trim())
      .filter(p => p.length > 0)
  }
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
    modelsPath: app.modelsPath,
    subscribedProjects: [...app.subscribedProjects],
    active: app.active,
  }
  showEditModal.value = true
}

function confirmDelete(app) {
  appToDelete.value = app
  showDeleteModal.value = true
}

async function handleDelete() {
  try {
    await deleteApplication(appToDelete.value.id)
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
      modelsPath: form.value.modelsPath,
      subscribedProjects: form.value.subscribedProjects,
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
    modelsPath: '',
    subscribedProjects: [],
    active: true,
  }
}

onMounted(() => {
  loadData()
})
</script>
