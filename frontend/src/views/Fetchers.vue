<template>
  <div class="p-8">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Fetchers</h1>
      <button @click="showCreateModal = true" class="btn btn-primary">Add Fetcher</button>
    </div>

    <!-- Filters -->
    <div class="card mb-4 flex flex-wrap gap-4 items-end">
      <div>
        <label class="block text-xs text-gray-400 mb-1">Search</label>
        <input
          v-model="filterText"
          type="text"
          placeholder="Name or description..."
          class="input text-sm w-56"
        />
      </div>
      <div>
        <label class="block text-xs text-gray-400 mb-1">Created from</label>
        <input v-model="filterDateFrom" type="date" class="input text-sm" />
      </div>
      <div>
        <label class="block text-xs text-gray-400 mb-1">Created to</label>
        <input v-model="filterDateTo" type="date" class="input text-sm" />
      </div>
      <button
        v-if="filterText || filterDateFrom || filterDateTo"
        @click="filterText = ''; filterDateFrom = ''; filterDateTo = ''"
        class="btn btn-secondary text-sm self-end"
      >Clear</button>
    </div>

    <!-- Table -->
    <div class="card p-0 overflow-hidden">
      <div v-if="loading" class="text-center py-10 text-gray-400">Loading fetchers...</div>
      <div v-else-if="error" class="text-center py-10 text-red-400">{{ error }}</div>
      <div v-else-if="filtered.length === 0" class="text-center py-10 text-gray-500">
        No fetchers match the current filters.
      </div>
      <table v-else class="w-full text-sm">
        <thead class="bg-gray-900 text-gray-400 text-xs uppercase tracking-wide">
          <tr>
            <th class="px-4 py-3 text-left cursor-pointer select-none hover:text-white" @click="setSort('name')">
              Name <SortIcon field="name" :sortBy="sortBy" :sortDir="sortDir" />
            </th>
            <th class="px-4 py-3 text-left hidden md:table-cell">Description</th>
            <th class="px-4 py-3 text-center cursor-pointer select-none hover:text-white w-28" @click="setSort('resources')">
              Resources <SortIcon field="resources" :sortBy="sortBy" :sortDir="sortDir" />
            </th>
            <th class="px-4 py-3 text-center cursor-pointer select-none hover:text-white w-28" @click="setSort('params')">
              Params <SortIcon field="params" :sortBy="sortBy" :sortDir="sortDir" />
            </th>
            <th class="px-4 py-3 text-left cursor-pointer select-none hover:text-white w-36" @click="setSort('createdAt')">
              Created <SortIcon field="createdAt" :sortBy="sortBy" :sortDir="sortDir" />
            </th>
            <th class="px-4 py-3 w-24"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
          <tr
            v-for="f in filtered"
            :key="f.id"
            class="hover:bg-gray-750 transition-colors"
          >
            <td class="px-4 py-3 font-medium text-white">
              <span :title="f.classPath || ''" class="cursor-default">{{ f.name || f.code }}</span>
              <span v-if="f.classPath" class="block text-xs text-gray-600 font-mono mt-0.5">{{ f.classPath }}</span>
            </td>
            <td class="px-4 py-3 text-gray-400 hidden md:table-cell max-w-xs truncate" :title="f.description">
              {{ f.description || '—' }}
            </td>
            <td class="px-4 py-3 text-center">
              <span
                class="inline-flex items-center justify-center min-w-[1.5rem] px-2 py-0.5 rounded-full text-xs font-semibold"
                :class="f.resources?.length ? 'bg-blue-900 text-blue-300' : 'bg-gray-700 text-gray-500'"
              >{{ f.resources?.length ?? 0 }}</span>
            </td>
            <td class="px-4 py-3 text-center">
              <span class="text-gray-400">{{ f.paramsDef?.length ?? 0 }}</span>
            </td>
            <td class="px-4 py-3 text-gray-500 text-xs">{{ formatDate(f.createdAt) }}</td>
            <td class="px-4 py-3">
              <div class="flex justify-end gap-2">
                <button
                  @click="editFetcher(f)"
                  class="p-1.5 rounded text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
                  title="Edit"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                  </svg>
                </button>
                <button
                  @click="deleteFetcher(f)"
                  :disabled="f.resources?.length > 0"
                  class="p-1.5 rounded transition-colors"
                  :class="f.resources?.length > 0
                    ? 'text-gray-600 cursor-not-allowed'
                    : 'text-gray-400 hover:text-red-400 hover:bg-gray-700'"
                  :title="f.resources?.length > 0 ? 'Cannot delete: has resources' : 'Delete'"
                >
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <!-- Footer count -->
      <div v-if="!loading && !error && filtered.length > 0" class="px-4 py-2 border-t border-gray-700 text-xs text-gray-500">
        {{ filtered.length }} fetcher{{ filtered.length !== 1 ? 's' : '' }}
        <span v-if="filtered.length !== Fetchers.length"> (filtered from {{ Fetchers.length }})</span>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <CreateEditFetcherModal
      v-if="showCreateModal"
      :Fetcher="editingFetcher"
      @close="closeModal"
      @saved="onSaved"
    />

    <!-- Notifications -->
    <transition enter-active-class="transition ease-out duration-300" enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0" leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="errorMessage" class="mt-4 p-4 bg-red-900 border border-red-700 rounded text-red-200">{{ errorMessage }}</div>
    </transition>
    <transition enter-active-class="transition ease-out duration-300" enter-from-class="opacity-0 translate-y-2"
      enter-to-class="opacity-100 translate-y-0" leave-active-class="transition ease-in duration-200"
      leave-from-class="opacity-100" leave-to-class="opacity-0">
      <div v-if="successMessage" class="mt-4 p-4 bg-green-900 border border-green-700 rounded text-green-200 flex items-center justify-between">
        <span>{{ successMessage }}</span>
        <button @click="successMessage = null" class="text-green-400 hover:text-green-200 ml-4">×</button>
      </div>
    </transition>

    <!-- Delete Modal -->
    <div v-if="showDeleteDialog"
         class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
         @click.self="cancelDeleteFetcher">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md border border-gray-700 shadow-2xl">
        <h2 class="text-xl font-bold mb-4">Delete Fetcher</h2>
        <p class="mb-6">
          Are you sure you want to delete <strong class="text-purple-300">{{ fetcherToDelete?.name || fetcherToDelete?.description }}</strong>?
          The fetcher will be hidden from the UI.
        </p>
        <label class="flex items-start gap-2 mb-6 cursor-pointer">
          <input type="checkbox" v-model="hardDeleteFlag" class="accent-red-500 mt-0.5" />
          <span>
            <span class="text-sm text-gray-300">Permanently delete</span>
            <span class="block text-xs text-gray-500 mt-0.5">The fetcher record will be removed from the database.</span>
          </span>
        </label>
        <div class="flex justify-end gap-2">
          <button @click="cancelDeleteFetcher" class="btn btn-secondary">Cancel</button>
          <button @click="confirmDeleteFetcher" class="btn btn-danger">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { fetchFetchers, deleteFetcher as deleteFetcherAPI } from '../api/graphql'
import CreateEditFetcherModal from './CreateEditFetcherModal.vue'
import { onMounted } from 'vue'

// ── Sort icon component ──────────────────────────────────────────────────────
const SortIcon = {
  props: ['field', 'sortBy', 'sortDir'],
  template: `<span class="ml-1 opacity-60">
    <span v-if="sortBy === field">{{ sortDir === 'asc' ? '▲' : '▼' }}</span>
    <span v-else class="opacity-30">⇅</span>
  </span>`
}

// ── State ────────────────────────────────────────────────────────────────────
const Fetchers     = ref([])
const loading      = ref(false)
const error        = ref(null)
const errorMessage = ref(null)
const successMessage = ref(null)

const showCreateModal  = ref(false)
const showDeleteDialog = ref(false)
const hardDeleteFlag   = ref(false)
const editingFetcher   = ref(null)
const fetcherToDelete  = ref(null)

const filterText     = ref('')
const filterDateFrom = ref('')
const filterDateTo   = ref('')
const sortBy         = ref('name')
const sortDir        = ref('asc')

// ── Computed ─────────────────────────────────────────────────────────────────
const filtered = computed(() => {
  let list = Fetchers.value

  if (filterText.value) {
    const q = filterText.value.toLowerCase()
    list = list.filter(f =>
      (f.name || f.code || '').toLowerCase().includes(q) ||
      (f.description || '').toLowerCase().includes(q)
    )
  }

  if (filterDateFrom.value) {
    const from = new Date(filterDateFrom.value)
    list = list.filter(f => f.createdAt && new Date(f.createdAt) >= from)
  }

  if (filterDateTo.value) {
    const to = new Date(filterDateTo.value)
    to.setHours(23, 59, 59, 999)
    list = list.filter(f => f.createdAt && new Date(f.createdAt) <= to)
  }

  return [...list].sort((a, b) => {
    let va, vb
    if (sortBy.value === 'name') {
      va = (a.name || a.code || '').toLowerCase()
      vb = (b.name || b.code || '').toLowerCase()
    } else if (sortBy.value === 'resources') {
      va = a.resources?.length ?? 0
      vb = b.resources?.length ?? 0
    } else if (sortBy.value === 'params') {
      va = a.paramsDef?.length ?? 0
      vb = b.paramsDef?.length ?? 0
    } else if (sortBy.value === 'createdAt') {
      va = a.createdAt ? new Date(a.createdAt).getTime() : 0
      vb = b.createdAt ? new Date(b.createdAt).getTime() : 0
    }
    if (va < vb) return sortDir.value === 'asc' ? -1 : 1
    if (va > vb) return sortDir.value === 'asc' ? 1 : -1
    return 0
  })
})

// ── Helpers ──────────────────────────────────────────────────────────────────
function setSort(field) {
  if (sortBy.value === field) {
    sortDir.value = sortDir.value === 'asc' ? 'desc' : 'asc'
  } else {
    sortBy.value = field
    sortDir.value = field === 'resources' ? 'desc' : 'asc'
  }
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('es-ES', { year: 'numeric', month: '2-digit', day: '2-digit' })
}

// ── Data ─────────────────────────────────────────────────────────────────────
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

// ── Actions ──────────────────────────────────────────────────────────────────
function editFetcher(f) {
  editingFetcher.value = { ...f }
  showCreateModal.value = true
}

function deleteFetcher(f) {
  fetcherToDelete.value = f
  hardDeleteFlag.value = false
  showDeleteDialog.value = true
}

async function confirmDeleteFetcher() {
  if (!fetcherToDelete.value) return
  try {
    await deleteFetcherAPI(fetcherToDelete.value.id, hardDeleteFlag.value)
    successMessage.value = `Fetcher "${fetcherToDelete.value.name}" deleted successfully`
    showDeleteDialog.value = false
    fetcherToDelete.value = null
    loadFetchers()
    setTimeout(() => { successMessage.value = null }, 3000)
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
  setTimeout(() => { successMessage.value = null }, 3000)
}

onMounted(loadFetchers)
</script>
