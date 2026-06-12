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
            <th class="py-2 pr-3 w-8"><input type="checkbox" class="w-4 h-4 accent-blue-500 cursor-pointer" :checked="allPageSelected" @change="togglePage" /></th>
            <th class="py-2 pr-4 font-medium">Name</th>
            <th class="py-2 pr-4 font-medium">Deleted at</th>
            <th class="py-2 font-medium text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="item in pagedItems"
            :key="itemId(item)"
            class="border-b border-gray-800 hover:bg-gray-800/40"
          >
            <td class="py-3 pr-3"><input type="checkbox" class="w-4 h-4 accent-blue-500 cursor-pointer" :checked="selected.has(itemId(item))" @change="toggleOne(item)" /></td>
            <td class="py-3 pr-4 text-gray-200">{{ itemName(item) }}</td>
            <td class="py-3 pr-4 text-gray-500 text-xs">{{ formatDate(item.deletedAt) }}</td>
            <td class="py-3 text-right">
              <div class="flex justify-end gap-2">
                <button @click="restore(item)" class="act-icon" title="Restaurar">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h5M4 9a9 9 0 11-1 4"/></svg>
                </button>
                <button @click="confirmHardDelete(item)" class="act-icon danger" title="Eliminar permanentemente">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
        <Paginator v-model:page="tPage" v-model:perPage="tPerPage" :total="tTotal" />

        <!-- Barra de acciones colectivas (patrón estándar: Acción… + Aplicar) -->
        <div v-if="selected.size > 0" class="flex items-center gap-2 mt-2 px-3 py-2 rounded-lg bg-blue-900/20 border border-blue-800">
          <span class="text-sm text-blue-200"><b>{{ selected.size }}</b> seleccionados</span>
          <select v-model="bulkAction" class="input text-xs py-1 px-2">
            <option value="">Acción…</option>
            <option value="restore">Restaurar</option>
            <option value="delete">Borrar permanentemente</option>
          </select>
          <button @click="aplicarLote" :disabled="!bulkAction || bulkBusy"
            class="text-xs px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40">
            {{ bulkBusy ? 'Aplicando…' : 'Aplicar' }}
          </button>
          <button @click="clearSel" class="text-xs px-2 py-1.5 rounded border border-gray-600 text-gray-300 hover:bg-gray-700">Limpiar</button>
        </div>
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

    <!-- Bulk hard-delete confirmation modal -->
    <div v-if="bulkConfirm" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" @click.self="bulkConfirm = false">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4">Borrar permanentemente</h2>
        <p class="mb-6 text-gray-300">
          Se eliminarán de forma permanente <strong class="text-red-300">{{ selected.size }}</strong> registros. Esta acción no se puede deshacer.
        </p>
        <div class="flex justify-end gap-2">
          <button @click="bulkConfirm = false" class="btn btn-secondary">Cancelar</button>
          <button @click="bulkHardDelete" :disabled="bulkBusy" class="btn btn-danger">{{ bulkBusy ? 'Borrando…' : 'Borrar permanentemente' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { usePagination } from '../composables/usePagination.js'
import Paginator from '../components/Paginator.vue'
import {
  fetchDeletedResources, fetchDeletedSubscribers, fetchDeletedPublishers,
  fetchDeletedFetchers, fetchDeletedExecutions,
  restoreResource, restoreSubscriber, restorePublisher, restoreFetcher, restoreExecution,
  deleteResource, deleteSubscriber, deletePublisher, deleteFetcher, deleteExecution,
} from '../api/graphql'

const tabs = [
  { key: 'resources',    label: 'Resources' },
  { key: 'subscribers', label: 'Subscribers' },
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
  subscribers: [],
  publishers: [],
  fetchers: [],
  executions: [],
  datasets: [],
})

const currentItems = computed(() => data.value[activeTab.value] || [])
const { page: tPage, perPage: tPerPage, total: tTotal, paged: pagedItems } = usePagination(currentItems, 25)

// Selección y acciones colectivas
const selected = ref(new Set())
const bulkBusy = ref(false)
const bulkConfirm = ref(false)
const bulkAction = ref('')
function clearSel() { selected.value = new Set() }
function toggleOne(item) { const id = itemId(item); const s = new Set(selected.value); s.has(id) ? s.delete(id) : s.add(id); selected.value = s }
const allPageSelected = computed(() => pagedItems.value.length > 0 && pagedItems.value.every(i => selected.value.has(itemId(i))))
function togglePage() { const s = new Set(selected.value); const on = !allPageSelected.value; pagedItems.value.forEach(i => on ? s.add(itemId(i)) : s.delete(itemId(i))); selected.value = s }
const itemsSeleccionados = computed(() => currentItems.value.filter(i => selected.value.has(itemId(i))))
// Al cambiar de pestaña, la selección deja de tener sentido.
watch(activeTab, () => { clearSel(); bulkAction.value = '' })

// Dispatcher de la barra colectiva: restaurar directo; borrar pasa por confirmación.
function aplicarLote() {
  if (bulkAction.value === 'restore') bulkRestore()
  else if (bulkAction.value === 'delete') bulkConfirm.value = true
}

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
      fetchDeletedSubscribers(),
      fetchDeletedPublishers(),
      fetchDeletedFetchers(),
      fetchDeletedExecutions(),
      fetchDeletedDatasets(),
    ])
    data.value = {
      resources:    res.deletedResources    || [],
      subscribers: apps.deletedSubscribers || [],
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

async function doRestore(item) {
  if (activeTab.value === 'datasets') {
    const resp = await fetch(`/api/datasets/${item.datasetId}/restore`, { method: 'POST' })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  } else {
    const fn = {
      resources:    restoreResource,
      subscribers: restoreSubscriber,
      publishers:   restorePublisher,
      fetchers:     restoreFetcher,
      executions:   restoreExecution,
    }[activeTab.value]
    await fn(item.id)
  }
}
async function restore(item) {
  try { await doRestore(item); await load() }
  catch (e) { error.value = e.message }
}

function confirmHardDelete(item) {
  itemToDelete.value = item
}

async function doHardDelete(item) {
  if (activeTab.value === 'datasets') {
    const resp = await fetch(`/api/datasets/${item.datasetId}?hard=true`, { method: 'DELETE' })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  } else {
    const fn = {
      resources:    (id) => deleteResource(id, true),
      subscribers: (id) => deleteSubscriber(id, true),
      publishers:   (id) => deletePublisher(id, true),
      fetchers:     (id) => deleteFetcher(id, true),
      executions:   (id) => deleteExecution(id, true),
    }[activeTab.value]
    if (fn) await fn(item.id)
  }
}
async function hardDelete() {
  try { await doHardDelete(itemToDelete.value); itemToDelete.value = null; await load() }
  catch (e) { error.value = e.message }
}

// Acciones colectivas
async function bulkRestore() {
  bulkBusy.value = true
  try { for (const it of itemsSeleccionados.value) await doRestore(it); clearSel(); await load() }
  catch (e) { error.value = e.message }
  finally { bulkBusy.value = false }
}
async function bulkHardDelete() {
  bulkBusy.value = true
  try { for (const it of itemsSeleccionados.value) await doHardDelete(it); clearSel(); bulkConfirm.value = false; await load() }
  catch (e) { error.value = e.message }
  finally { bulkBusy.value = false }
}

onMounted(load)
</script>
