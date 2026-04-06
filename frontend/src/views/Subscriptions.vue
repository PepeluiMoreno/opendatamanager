<template>
  <div class="p-6 h-full flex flex-col gap-6 overflow-hidden">

    <!-- Header -->
    <div class="flex items-center justify-between flex-shrink-0">
      <div>
        <h2 class="text-2xl font-bold text-white">Subscriptions</h2>
        <p class="text-gray-400 text-sm mt-1">Manage which applications consume each resource</p>
      </div>
      <button @click="openNew" class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">
        + New subscription
      </button>
    </div>

    <!-- Filters -->
    <div class="flex gap-3 flex-shrink-0 flex-wrap">
      <select v-model="filterApp" class="bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 min-w-[180px]">
        <option value="">All applications</option>
        <option v-for="a in applications" :key="a.id" :value="a.id">{{ a.name }}</option>
      </select>
      <select v-model="filterResource" class="bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500 min-w-[200px]">
        <option value="">All resources</option>
        <option v-for="r in resources" :key="r.id" :value="r.id">{{ r.name }}</option>
      </select>
      <button v-if="filterApp || filterResource" @click="filterApp = ''; filterResource = ''"
        class="px-3 py-2 text-xs bg-yellow-600 hover:bg-yellow-500 text-white rounded-lg transition-colors">
        Clear
      </button>
      <span class="ml-auto self-center text-gray-400 text-sm tabular-nums">
        {{ filtered.length }} / {{ subscriptions.length }}
      </span>
    </div>

    <!-- Error -->
    <div v-if="error" class="flex-shrink-0 p-3 bg-red-900 border border-red-700 rounded-lg text-red-200 text-sm">{{ error }}</div>

    <!-- Table -->
    <div class="flex-1 overflow-auto rounded-xl border border-gray-700 bg-gray-800 min-h-0">
      <div v-if="loading" class="flex items-center justify-center h-40 text-gray-400">Loading...</div>
      <div v-else-if="!filtered.length" class="flex flex-col items-center justify-center h-40 text-gray-500 gap-2">
        <span>No subscriptions found.</span>
        <button @click="openNew" class="text-blue-400 hover:underline text-sm">Create one</button>
      </div>
      <table v-else class="w-full text-sm">
        <thead class="sticky top-0 bg-gray-900 z-10">
          <tr class="text-left text-gray-400 border-b border-gray-700">
            <th class="py-3 px-4 font-medium">Application</th>
            <th class="py-3 px-4 font-medium">Mode</th>
            <th class="py-3 px-4 font-medium">Resource</th>
            <th class="py-3 px-4 font-medium">Auto-upgrade</th>
            <th class="py-3 px-4 font-medium">Pinned version</th>
            <th class="py-3 px-4 font-medium">Current version</th>
            <th class="py-3 px-4 font-medium">Notified at</th>
            <th class="py-3 px-4 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="sub in filtered" :key="sub.id"
            class="border-b border-gray-700 hover:bg-gray-750 transition-colors">
            <td class="py-3 px-4 text-white font-medium">{{ appName(sub.applicationId) }}</td>
            <td class="py-3 px-4">
              <span class="text-xs px-2 py-0.5 rounded font-semibold" :class="modeClass(appMode(sub.applicationId))">
                {{ appMode(sub.applicationId) || '—' }}
              </span>
            </td>
            <td class="py-3 px-4">
              <div class="text-gray-200 font-medium">{{ resourceName(sub.resourceId) }}</div>
              <div class="text-xs text-gray-400">{{ resourcePublisher(sub.resourceId) }}</div>
            </td>
            <td class="py-3 px-4">
              <span class="text-xs px-2 py-0.5 rounded font-semibold" :class="upgradeBadge(sub.autoUpgrade)">
                {{ sub.autoUpgrade }}
              </span>
            </td>
            <td class="py-3 px-4 text-gray-400 font-mono text-xs">{{ sub.pinnedVersion || '—' }}</td>
            <td class="py-3 px-4 text-gray-400 font-mono text-xs">{{ sub.currentVersion || '—' }}</td>
            <td class="py-3 px-4 text-gray-400 text-xs">{{ formatDate(sub.notifiedAt) }}</td>
            <td class="py-3 px-4 text-right">
              <button @click="confirmDelete(sub)"
                class="px-3 py-1 bg-red-700 hover:bg-red-600 text-white rounded text-xs font-medium transition-colors">
                Delete
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Create modal -->
    <div v-if="showModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-gray-800 border border-gray-600 rounded-xl p-6 w-full max-w-lg shadow-2xl">
        <h3 class="text-lg font-bold text-white mb-5">New subscription</h3>

        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-300 mb-1">Application <span class="text-red-400">*</span></label>
            <select v-model="form.applicationId" class="w-full bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
              <option value="">Select application…</option>
              <option v-for="a in applications" :key="a.id" :value="a.id">
                {{ a.name }} ({{ a.consumptionMode }})
              </option>
            </select>
          </div>

          <div>
            <label class="block text-sm text-gray-300 mb-1">Resource <span class="text-red-400">*</span></label>
            <select v-model="form.resourceId" class="w-full bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
              <option value="">Select resource…</option>
              <option v-for="r in resources" :key="r.id" :value="r.id">
                {{ r.name }}{{ r.publisher ? ' — ' + r.publisher : '' }}
              </option>
            </select>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-gray-300 mb-1">Auto-upgrade</label>
              <select v-model="form.autoUpgrade" class="w-full bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                <option value="patch">patch — always latest</option>
                <option value="minor">minor — latest minor</option>
                <option value="none">none — pin to version</option>
              </select>
            </div>
            <div>
              <label class="block text-sm text-gray-300 mb-1">Pinned version</label>
              <input v-model="form.pinnedVersion" type="text" placeholder="e.g. 1.2.* or empty"
                class="w-full bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
              <p class="text-xs text-gray-500 mt-1">Empty = no version constraint</p>
            </div>
          </div>
        </div>

        <div v-if="modalError" class="mt-3 p-2 bg-red-900 border border-red-700 rounded text-red-200 text-xs">{{ modalError }}</div>

        <div class="flex gap-3 mt-6 justify-end">
          <button @click="showModal = false" class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors">
            Cancel
          </button>
          <button @click="submitNew" :disabled="saving || !form.applicationId || !form.resourceId"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors">
            {{ saving ? 'Saving…' : 'Subscribe' }}
          </button>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  fetchSubscriptions,
  subscribeResource,
  unsubscribeResource,
  fetchResources,
  fetchApplications,
} from '../api/graphql'

const subscriptions = ref([])
const resources     = ref([])
const applications  = ref([])
const loading       = ref(true)
const error         = ref(null)
const showModal     = ref(false)
const saving        = ref(false)
const modalError    = ref(null)
const filterApp      = ref('')
const filterResource = ref('')

const form = ref({ applicationId: '', resourceId: '', pinnedVersion: '', autoUpgrade: 'patch' })

const filtered = computed(() => subscriptions.value.filter(s => {
  if (filterApp.value      && s.applicationId !== filterApp.value)      return false
  if (filterResource.value && s.resourceId    !== filterResource.value) return false
  return true
}))

onMounted(load)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [subRes, resRes, appRes] = await Promise.all([
      fetchSubscriptions(),
      fetchResources(),
      fetchApplications(),
    ])
    subscriptions.value = subRes?.datasetSubscriptions ?? []
    resources.value     = resRes?.resources            ?? []
    applications.value  = appRes?.applications         ?? []
  } catch (e) {
    error.value = e.message || 'Error loading data'
  } finally {
    loading.value = false
  }
}

function openNew() {
  form.value = { applicationId: '', resourceId: '', pinnedVersion: '', autoUpgrade: 'patch' }
  modalError.value = null
  showModal.value = true
}

async function submitNew() {
  saving.value = true
  modalError.value = null
  try {
    await subscribeResource(
      form.value.applicationId,
      form.value.resourceId,
      form.value.pinnedVersion || null,
      form.value.autoUpgrade,
    )
    showModal.value = false
    await load()
  } catch (e) {
    modalError.value = e.message || 'Error creating subscription'
  } finally {
    saving.value = false
  }
}

async function confirmDelete(sub) {
  const aName = appName(sub.applicationId)
  const rName = resourceName(sub.resourceId)
  if (!confirm(`Delete subscription: "${aName}" → "${rName}"?`)) return
  try {
    await unsubscribeResource(sub.id)
    await load()
  } catch (e) {
    error.value = e.message || 'Error deleting subscription'
  }
}

// Lookups
function appName(id)          { return applications.value.find(a => a.id === id)?.name          ?? id }
function appMode(id)          { return applications.value.find(a => a.id === id)?.consumptionMode ?? '' }
function resourceName(id)     { return resources.value.find(r => r.id === id)?.name             ?? id }
function resourcePublisher(id){ return resources.value.find(r => r.id === id)?.publisher        ?? '' }

function modeClass(mode) {
  return {
    graphql: 'bg-blue-900 text-blue-300',
    webhook: 'bg-purple-900 text-purple-300',
    both:    'bg-teal-900 text-teal-300',
  }[mode] ?? 'bg-gray-700 text-gray-300'
}

function upgradeBadge(v) {
  if (v === 'patch') return 'bg-green-800 text-green-200'
  if (v === 'minor') return 'bg-blue-800 text-blue-200'
  return 'bg-gray-700 text-gray-300'
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z').toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit',
  })
}
</script>
