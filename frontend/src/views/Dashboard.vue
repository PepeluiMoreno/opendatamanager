<template>
  <div class="p-8">
    <h1 class="text-3xl font-bold mb-8">Dashboard</h1>

    <!-- Stats Cards -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
      <div class="card">
        <div class="text-gray-400 text-sm mb-2">Active Resources</div>
        <div class="text-4xl font-bold text-blue-400">{{ stats.activeSources }}</div>
      </div>

      <div class="card">
        <div class="text-gray-400 text-sm mb-2">Fetcher Types</div>
        <div class="text-4xl font-bold text-green-400">{{ stats.fetchers }}</div>
      </div>

      <div class="card">
        <div class="text-gray-400 text-sm mb-2">Subscribed Apps</div>
        <div class="text-4xl font-bold text-purple-400">{{ stats.applications }}</div>
      </div>
    </div>

    <!-- Actions -->
    <div class="card mb-8">
      <h2 class="text-xl font-bold mb-4">Quick Actions</h2>
      <div class="space-x-4">
        <button
          @click="executeAll"
          :disabled="loading"
          class="btn btn-primary"
        >
          {{ loading ? 'Executing...' : 'Execute All Resources' }}
        </button>
        <button
          @click="loadStats"
          class="btn btn-secondary"
        >
          Refresh Stats
        </button>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="card">
      <h2 class="text-xl font-bold mb-4">Recent Resources</h2>
      <div v-if="recentSources.length > 0" class="space-y-3">
        <div
          v-for="source in recentSources"
          :key="source.id"
          class="flex items-center justify-between p-4 bg-gray-700 rounded"
        >
          <div>
            <div class="font-medium">{{ source.name }}</div>
            <div class="text-sm text-gray-400">{{ source.publisher }} - {{ source.fetcher.code }}</div>
          </div>
          <div class="flex items-center space-x-2">
            <span
              :class="source.active ? 'text-green-400' : 'text-red-400'"
              class="text-sm"
            >
              {{ source.active ? 'Active' : 'Inactive' }}
            </span>
            <router-link
              :to="`/resources/${source.id}/test`"
              class="btn btn-secondary text-sm py-1 px-3"
            >
              Test
            </router-link>
          </div>
        </div>
      </div>
      <div v-else class="text-gray-400 text-center py-8">
        No resources configured yet
      </div>
    </div>

    <!-- Error Display -->
    <div v-if="error" class="mt-4 p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <!-- Success Display -->
    <div v-if="successMessage" class="mt-4 p-4 bg-green-900 border border-green-700 rounded text-green-200">
      {{ successMessage }}
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchResources, fetchfetchers, fetchApplications, executeAllResources } from '../api/graphql'

const stats = ref({
  activeSources: 0,
  fetchers: 0,
  applications: 0,
})

const recentSources = ref([])
const loading = ref(false)
const error = ref(null)
const successMessage = ref(null)

async function loadStats() {
  try {
    error.value = null
    const [resourcesData, fetchersData, appsData] = await Promise.all([
      fetchResources(false),
      fetchfetchers(),
      fetchApplications(),
    ])

    stats.value.activeSources = resourcesData.resources?.filter(s => s.active).length || 0
    stats.value.fetchers = fetchersData.fetchers?.length || 0
    stats.value.applications = appsData.applications?.filter(a => a.active).length || 0

    recentSources.value = resourcesData.resources?.slice(0, 5) || []
  } catch (e) {
    // Only show error if it's not just empty data
    console.error('Dashboard error:', e)
    error.value = 'Unable to load dashboard data. Please check that the backend is running.'
  }
}

async function executeAll() {
  try {
    loading.value = true
    error.value = null
    successMessage.value = null

    const result = await executeAllResources()

    if (result.executeAllResources.success) {
      successMessage.value = result.executeAllResources.message
    } else {
      error.value = result.executeAllResources.message
    }
  } catch (e) {
    error.value = 'Failed to execute resources: ' + e.message
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStats()
})
</script>
