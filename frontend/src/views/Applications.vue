<template>
  <div class="p-6 flex flex-col lg:flex-row gap-6 h-full">

    <!-- ── Maestro: aplicaciones ───────────────────────────────────────── -->
    <aside class="lg:w-1/3 flex flex-col min-h-0">
      <div class="flex items-center justify-between mb-3">
        <h1 class="text-xl font-bold text-white">Applications</h1>
        <button @click="openCreateApp" class="btn btn-primary text-sm py-1 px-3">+ New</button>
      </div>

      <div v-if="loading" class="text-gray-400 text-center py-8">Loading…</div>
      <div v-else-if="error" class="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm">{{ error }}</div>
      <div v-else-if="applications.length === 0" class="text-gray-400 text-sm py-8 text-center">
        No applications yet. Click “New”.
      </div>

      <div v-else class="flex-1 overflow-y-auto space-y-2 pr-1 min-h-0">
        <button
          v-for="app in applications" :key="app.id"
          @click="selectedAppId = app.id"
          :class="['w-full text-left card hover:border-gray-600 transition-colors',
                   selectedAppId === app.id ? 'border-purple-500 bg-purple-900/20' : '']"
        >
          <div class="flex items-start justify-between gap-2">
            <div class="min-w-0">
              <h3 class="font-bold text-purple-300 truncate">{{ app.name }}</h3>
              <p v-if="app.description" class="text-xs text-gray-400 mt-0.5 truncate">{{ app.description }}</p>
            </div>
            <span :class="app.active ? 'text-green-400' : 'text-red-400'" class="text-xs font-medium flex-shrink-0">
              {{ app.active ? 'Active' : 'Inactive' }}
            </span>
          </div>
          <div class="flex items-center gap-2 mt-2">
            <span class="text-xs font-mono px-2 py-0.5 rounded" :class="modeClass(app.consumptionMode)">
              {{ app.consumptionMode === 'both' ? 'webhook + graphql' : app.consumptionMode }}
            </span>
            <span class="text-xs text-gray-500">{{ subsForApp(app.id).length }} subs</span>
          </div>
        </button>
      </div>
    </aside>

    <!-- ── Detalle: suscripciones de la aplicación seleccionada ─────────── -->
    <section class="lg:flex-1 flex flex-col min-h-0 rounded-xl border border-gray-700 bg-gray-800">
      <div v-if="!selectedApp" class="flex-1 flex items-center justify-center text-gray-500 text-sm">
        Select an application to manage its subscriptions.
      </div>

      <template v-else>
        <!-- Cabecera del detalle -->
        <div class="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
          <div class="min-w-0">
            <h2 class="text-lg font-bold text-white truncate">{{ selectedApp.name }}</h2>
            <div class="flex items-center gap-2 mt-1">
              <span class="text-xs font-mono px-2 py-0.5 rounded" :class="modeClass(selectedApp.consumptionMode)">
                {{ selectedApp.consumptionMode }}
              </span>
              <span v-if="selectedApp.webhookUrl" class="text-xs text-gray-500 truncate">{{ selectedApp.webhookUrl }}</span>
            </div>
          </div>
          <div class="flex gap-2 flex-shrink-0">
            <button @click="openEditApp(selectedApp)" class="btn btn-secondary text-sm py-1 px-3">Edit app</button>
            <button @click="confirmDeleteApp(selectedApp)" class="btn btn-danger text-sm py-1 px-3">Delete app</button>
            <button @click="openNewSub" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">+ Subscription</button>
          </div>
        </div>

        <!-- Tabla de suscripciones -->
        <div class="flex-1 overflow-auto min-h-0">
          <div v-if="subsForApp(selectedApp.id).length === 0" class="flex flex-col items-center justify-center h-40 text-gray-500 gap-2">
            <span>No subscriptions for this application.</span>
            <button @click="openNewSub" class="text-blue-400 hover:underline text-sm">Subscribe to a resource</button>
          </div>
          <table v-else class="w-full text-sm">
            <thead class="sticky top-0 bg-gray-900 z-10">
              <tr class="text-left text-gray-400 border-b border-gray-700">
                <th class="py-3 px-4 font-medium">Resource</th>
                <th class="py-3 px-4 font-medium">Auto-upgrade</th>
                <th class="py-3 px-4 font-medium">Pinned version</th>
                <th class="py-3 px-4 font-medium">Current version</th>
                <th class="py-3 px-4 font-medium">Notified at</th>
                <th class="py-3 px-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="sub in pagedSubs" :key="sub.id"
                  class="border-b border-gray-700 hover:bg-gray-750 transition-colors">
                <td class="py-3 px-4">
                  <div class="text-gray-200 font-medium">{{ resourceName(sub.resourceId) }}</div>
                  <div class="text-xs text-gray-400">{{ resourcePublisher(sub.resourceId) }}</div>
                </td>
                <td class="py-3 px-4">
                  <span class="text-xs px-2 py-0.5 rounded font-semibold" :class="upgradeBadge(sub.autoUpgrade)">{{ sub.autoUpgrade }}</span>
                </td>
                <td class="py-3 px-4 text-gray-400 font-mono text-xs">{{ sub.pinnedVersion || '—' }}</td>
                <td class="py-3 px-4 text-gray-400 font-mono text-xs">{{ sub.currentVersion || '—' }}</td>
                <td class="py-3 px-4 text-gray-400 text-xs">{{ formatDate(sub.notifiedAt) }}</td>
                <td class="py-3 px-4 text-right">
                  <button @click="confirmDeleteSub(sub)" class="px-3 py-1 bg-red-700 hover:bg-red-600 text-white rounded text-xs font-medium transition-colors">Delete</button>
                </td>
              </tr>
            </tbody>
          </table>
          <Paginator v-model:page="aPage" v-model:perPage="aPerPage" :total="aTotal" />
        </div>
      </template>
    </section>

    <!-- ── Modal: crear/editar aplicación ──────────────────────────────── -->
    <div v-if="showAppModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="closeAppModal">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h2 class="text-2xl font-bold mb-4">{{ editingApp ? 'Edit Application' : 'Create Application' }}</h2>
        <form @submit.prevent="submitApp" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">Name</label>
            <input v-model="appForm.name" type="text" required class="input w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-2">Description</label>
            <textarea v-model="appForm.description" rows="3" class="input w-full"></textarea>
          </div>
          <div>
            <label class="block text-sm font-medium mb-2">Webhook URL</label>
            <input v-model="appForm.webhookUrl" type="url" class="input w-full" placeholder="https://your-app/odmgr-webhook" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-2">Consumption Mode</label>
            <div class="grid grid-cols-3 gap-2">
              <label v-for="opt in consumptionModes" :key="opt.value"
                :class="['flex flex-col items-start p-3 rounded border cursor-pointer transition-colors',
                         appForm.consumptionMode === opt.value ? 'border-purple-500 bg-purple-900/30' : 'border-gray-600 hover:border-gray-500']">
                <input type="radio" v-model="appForm.consumptionMode" :value="opt.value" class="sr-only" />
                <span class="text-sm font-mono font-semibold">{{ opt.value }}</span>
                <span class="text-xs text-gray-400 mt-1">{{ opt.label }}</span>
              </label>
            </div>
          </div>
          <div class="flex items-center">
            <input v-model="appForm.active" type="checkbox" id="app-active" class="mr-2" />
            <label for="app-active" class="text-sm">Active</label>
          </div>
          <div v-if="appModalError" class="p-2 bg-red-900 border border-red-700 rounded text-red-200 text-xs">{{ appModalError }}</div>
          <div class="flex justify-end space-x-2 pt-2">
            <button type="button" @click="closeAppModal" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">{{ editingApp ? 'Update' : 'Create' }}</button>
          </div>
        </form>
      </div>
    </div>

    <!-- ── Modal: borrar aplicación ────────────────────────────────────── -->
    <div v-if="showDeleteAppModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="showDeleteAppModal = false">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-2xl font-bold mb-4">Delete Application</h2>
        <p class="mb-6">Delete <strong class="text-purple-300">{{ appToDelete?.name }}</strong>? Its subscriptions and notifications will also be deleted.</p>
        <label class="flex items-start gap-2 mb-6 cursor-pointer">
          <input type="checkbox" v-model="hardDeleteFlag" class="accent-red-500 mt-0.5" />
          <span class="text-sm text-gray-300">Permanently delete</span>
        </label>
        <div class="flex justify-end space-x-2">
          <button @click="showDeleteAppModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="handleDeleteApp" class="btn btn-danger">Delete</button>
        </div>
      </div>
    </div>

    <!-- ── Modal: nueva suscripción (app fija = seleccionada) ──────────── -->
    <div v-if="showSubModal" class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
      <div class="bg-gray-800 border border-gray-600 rounded-xl p-6 w-full max-w-lg shadow-2xl">
        <h3 class="text-lg font-bold text-white mb-1">New subscription</h3>
        <p class="text-sm text-gray-400 mb-5">Application: <span class="text-purple-300 font-medium">{{ selectedApp?.name }}</span></p>
        <div class="space-y-4">
          <div>
            <label class="block text-sm text-gray-300 mb-1">Resource <span class="text-red-400">*</span></label>
            <select v-model="subForm.resourceId" class="w-full bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
              <option value="">Select resource…</option>
              <option v-for="r in resources" :key="r.id" :value="r.id">{{ r.name }}{{ r.publisher ? ' — ' + r.publisher : '' }}</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm text-gray-300 mb-1">Auto-upgrade</label>
              <select v-model="subForm.autoUpgrade" class="w-full bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500">
                <option value="patch">patch — always latest</option>
                <option value="minor">minor — latest minor</option>
                <option value="none">none — pin to version</option>
              </select>
            </div>
            <div>
              <label class="block text-sm text-gray-300 mb-1">Pinned version</label>
              <input v-model="subForm.pinnedVersion" type="text" placeholder="e.g. 1.2.* or empty"
                class="w-full bg-gray-700 border border-gray-600 text-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-blue-500" />
            </div>
          </div>
        </div>
        <div v-if="subModalError" class="mt-3 p-2 bg-red-900 border border-red-700 rounded text-red-200 text-xs">{{ subModalError }}</div>
        <div class="flex gap-3 mt-6 justify-end">
          <button @click="showSubModal = false" class="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg text-sm transition-colors">Cancel</button>
          <button @click="submitSub" :disabled="saving || !subForm.resourceId"
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
import { usePagination } from '../composables/usePagination.js'
import Paginator from '../components/Paginator.vue'
import {
  fetchApplications, createApplication, updateApplication, deleteApplication,
  fetchSubscriptions, subscribeResource, unsubscribeResource, fetchResources,
} from '../api/graphql'

const applications  = ref([])
const subscriptions = ref([])
const resources     = ref([])
const loading       = ref(true)
const error         = ref(null)
const selectedAppId = ref('')

// App CRUD state
const showAppModal       = ref(false)
const editingApp         = ref(null)
const appModalError      = ref(null)
const showDeleteAppModal = ref(false)
const appToDelete        = ref(null)
const hardDeleteFlag     = ref(false)
const consumptionModes = [
  { value: 'webhook', label: 'Download JSONL via webhook' },
  { value: 'graphql', label: 'Query GraphQL API' },
  { value: 'both',    label: 'Both modes' },
]
const appForm = ref({ name: '', description: '', webhookUrl: '', consumptionMode: 'webhook', active: true })

// Subscription state
const showSubModal  = ref(false)
const saving        = ref(false)
const subModalError = ref(null)
const subForm = ref({ resourceId: '', pinnedVersion: '', autoUpgrade: 'patch' })

const selectedApp = computed(() => applications.value.find(a => a.id === selectedAppId.value) || null)
function subsForApp(id) { return subscriptions.value.filter(s => s.applicationId === id) }
const subsSeleccionada = computed(() => selectedApp.value ? subsForApp(selectedApp.value.id) : [])
const { page: aPage, perPage: aPerPage, total: aTotal, paged: pagedSubs } = usePagination(subsSeleccionada, 25)

onMounted(load)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [appRes, subRes, resRes] = await Promise.all([
      fetchApplications(), fetchSubscriptions(), fetchResources(),
    ])
    applications.value  = appRes?.applications        ?? []
    subscriptions.value = subRes?.resourceSubscriptions ?? []
    resources.value     = resRes?.resources           ?? []
    if (!selectedApp.value && applications.value.length) selectedAppId.value = applications.value[0].id
  } catch (e) {
    error.value = e.message || 'Error loading data'
  } finally {
    loading.value = false
  }
}

// ── App CRUD ──
function openCreateApp() {
  editingApp.value = null
  appForm.value = { name: '', description: '', webhookUrl: '', consumptionMode: 'webhook', active: true }
  appModalError.value = null
  showAppModal.value = true
}
function openEditApp(app) {
  editingApp.value = app
  appForm.value = {
    name: app.name, description: app.description || '', webhookUrl: app.webhookUrl || '',
    consumptionMode: app.consumptionMode || 'webhook', active: app.active,
  }
  appModalError.value = null
  showAppModal.value = true
}
function closeAppModal() { showAppModal.value = false; editingApp.value = null }
async function submitApp() {
  appModalError.value = null
  try {
    const input = {
      name: appForm.value.name, description: appForm.value.description,
      webhookUrl: appForm.value.webhookUrl || null,
      consumptionMode: appForm.value.consumptionMode, active: appForm.value.active,
    }
    if (editingApp.value) await updateApplication(editingApp.value.id, input)
    else                  await createApplication(input)
    closeAppModal()
    await load()
  } catch (e) { appModalError.value = e.message || 'Failed to save application' }
}
function confirmDeleteApp(app) { appToDelete.value = app; hardDeleteFlag.value = false; showDeleteAppModal.value = true }
async function handleDeleteApp() {
  try {
    await deleteApplication(appToDelete.value.id, hardDeleteFlag.value)
    if (selectedAppId.value === appToDelete.value.id) selectedAppId.value = ''
    showDeleteAppModal.value = false
    appToDelete.value = null
    await load()
  } catch (e) { error.value = e.message || 'Failed to delete application' }
}

// ── Subscriptions ──
function openNewSub() {
  subForm.value = { resourceId: '', pinnedVersion: '', autoUpgrade: 'patch' }
  subModalError.value = null
  showSubModal.value = true
}
async function submitSub() {
  saving.value = true
  subModalError.value = null
  try {
    await subscribeResource(selectedAppId.value, subForm.value.resourceId, subForm.value.pinnedVersion || null, subForm.value.autoUpgrade)
    showSubModal.value = false
    await load()
  } catch (e) { subModalError.value = e.message || 'Error creating subscription' }
  finally { saving.value = false }
}
async function confirmDeleteSub(sub) {
  if (!confirm(`Delete subscription: "${selectedApp.value?.name}" → "${resourceName(sub.resourceId)}"?`)) return
  try { await unsubscribeResource(sub.id); await load() }
  catch (e) { error.value = e.message || 'Error deleting subscription' }
}

// ── Lookups / format ──
function resourceName(id)      { return resources.value.find(r => r.id === id)?.name      ?? id }
function resourcePublisher(id) { return resources.value.find(r => r.id === id)?.publisher ?? '' }
function modeClass(mode) {
  return { graphql: 'bg-blue-900 text-blue-300', webhook: 'bg-purple-900 text-purple-300', both: 'bg-teal-900 text-teal-300' }[mode] ?? 'bg-gray-700 text-gray-300'
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
