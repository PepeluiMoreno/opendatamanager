<template>
  <div class="p-8">
    <h1 class="text-3xl font-bold mb-2">Trash</h1>
    <p class="text-gray-400 text-sm mb-6">Soft-deleted records. Restore them or permanently delete them.</p>

    <!-- Tabs -->
    <div class="flex gap-1 mb-6 border-b border-gray-700">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        @click="activeTab = tab.key"
        :class="[
          'px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px',
          activeTab === tab.key
            ? 'border-purple-500 text-purple-300'
            : 'border-transparent text-gray-400 hover:text-gray-200'
        ]"
      >
        {{ tab.label }}
        <span v-if="counts[tab.key]" class="ml-1 text-xs bg-gray-700 px-1.5 py-0.5 rounded-full">
          {{ counts[tab.key] }}
        </span>
      </button>
    </div>

    <div v-if="loading" class="text-gray-400 py-8 text-center">Loading...</div>
    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200 text-sm">{{ error }}</div>

    <div v-else>
      <!-- Empty state -->
      <div v-if="currentItems.length === 0" class="text-gray-500 text-center py-12">
        No deleted {{ activeTab }} found.
      </div>

      <!-- Table -->
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-400 border-b border-gray-700">
            <th class="py-2 pr-4 font-medium">Name</th>
            <th class="py-2 pr-4 font-medium">Deleted at</th>
            <th class="py-2 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in currentItems"
            :key="itemId(item)"
            class="border-b border-gray-800 hover:bg-gray-800/40"
          >
            <td class="py-3 pr-4 text-gray-200">{{ itemName(item) }}</td>
            <td class="py-3 pr-4 text-gray-500 text-xs">{{ formatDate(item.deletedAt) }}</td>
            <td class="py-3 text-right">
              <div class="flex justify-end gap-2">
                <button
                  @click="restore(item)"
                  class="text-green-400 hover:text-green-300 text-xs px-3 py-1 rounded border border-green-800 hover:border-green-600 transition-colors"
                >
                  Restore
                </button>
                <button
                  @click="confirmHardDelete(item)"
                  class="text-red-400 hover:text-red-300 text-xs px-3 py-1 rounded border border-red-900 hover:border-red-700 transition-colors"
                >
                  Delete permanently
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Hard-delete confirmation modal -->
    <div
      v-if="itemToDelete"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="itemToDelete = null"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4">Delete permanently</h2>
        <p class="mb-6 text-gray-300">
          This will permanently remove <strong class="text-red-300">{{ itemName(itemToDelete) }}</strong> from the database. This cannot be undone.
        </p>
        <div class="flex justify-end gap-2">
          <button @click="itemToDelete = null" class="btn btn-secondary">Cancel</button>
          <button @click="hardDelete" class="btn btn-danger">Delete permanently</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  fetchDeletedResources, fetchDeletedApplications, fetchDeletedPublishers,
  fetchDeletedFetchers, fetchDeletedExecutions,
  restoreResource, restoreApplication, restorePublisher, restoreFetcher, restoreExecution,
  deleteResource, deleteApplication, deletePublisher, deleteFetcher,
} from '../api/graphql'

const tabs = [
  { key: 'resources',    label: 'Resources' },
  { key: 'applications', label: 'Applications' },
  { key: 'publishers',   label: 'Publishers' },
  { key: 'fetchers',     label: 'Fetchers' },
  { key: 'executions',   label: 'Processes' },
  { key: 'datasets',     label: 'Datasets' },
]

const activeTab = ref('resources')
const loading = ref(true)
const error = ref(null)
const itemToDelete = ref(null)

const data = ref({
  resources: [],
  applications: [],
  publishers: [],
  fetchers: [],
  executions: [],
  datasets: [],
})

const currentItems = computed(() => data.value[activeTab.value] || [])

const counts = computed(() => {
  const c = {}
  for (const tab of tabs) {
    const n = data.value[tab.key]?.length
    if (n) c[tab.key] = n
  }
  return c
})

function itemName(item) {
  if (item.datasetId) return `${item.resourceName || '—'} · v${item.version}`
  return item.name || item.nombre || item.code || item.resourceName || item.description || item.id
}

function itemId(item) {
  return item.datasetId || item.id
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })
}

async function fetchDeletedDatasets() {
  const resp = await fetch('/api/datasets/trash')
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return await resp.json()
}

async function load() {
  try {
    loading.value = true
    error.value = null
    const [res, apps, pubs, fetchers, execs, datasets] = await Promise.all([
      fetchDeletedResources(),
      fetchDeletedApplications(),
      fetchDeletedPublishers(),
      fetchDeletedFetchers(),
      fetchDeletedExecutions(),
      fetchDeletedDatasets(),
    ])
    data.value = {
      resources:    res.deletedResources    || [],
      applications: apps.deletedApplications || [],
      publishers:   pubs.deletedPublishers   || [],
      fetchers:     fetchers.deletedFetchers  || [],
      executions:   execs.deletedExecutions   || [],
      datasets:     datasets || [],
    }
  } catch (e) {
    error.value = e.message
  } finally {
    loading.value = false
  }
}

async function restore(item) {
  try {
    if (activeTab.value === 'datasets') {
      const resp = await fetch(`/api/datasets/${item.datasetId}/restore`, { method: 'POST' })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    } else {
      const fn = {
        resources:    restoreResource,
        applications: restoreApplication,
        publishers:   restorePublisher,
        fetchers:     restoreFetcher,
        executions:   restoreExecution,
      }[activeTab.value]
      await fn(item.id)
    }
    await load()
  } catch (e) {
    error.value = e.message
  }
}

function confirmHardDelete(item) {
  itemToDelete.value = item
}

async function hardDelete() {
  try {
    if (activeTab.value === 'datasets') {
      const resp = await fetch(`/api/datasets/${itemToDelete.value.datasetId}?hard=true`, { method: 'DELETE' })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    } else {
      const fn = {
        resources:    (id) => deleteResource(id, true),
        applications: (id) => deleteApplication(id, true),
        publishers:   (id) => deletePublisher(id, true),
        fetchers:     (id) => deleteFetcher(id, true),
        executions:   null,
      }[activeTab.value]
      if (fn) await fn(itemToDelete.value.id)
    }
    itemToDelete.value = null
    await load()
  } catch (e) {
    error.value = e.message
    itemToDelete.value = null
  }
}

onMounted(load)
</script>
