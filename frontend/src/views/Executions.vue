<template>
  <div class="p-8">
    <!-- Header -->
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-3xl font-bold">Processes</h1>
      <div class="flex items-center gap-3">
        <span class="text-xs text-gray-500">Auto-refresh every 5s</span>
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
        </span>
      </div>
    </div>

    <!-- Status filter tabs -->
    <div class="flex items-center gap-2 mb-4">
      <button
        v-for="tab in statusTabs"
        :key="tab.value"
        @click="statusFilter = tab.value"
        class="px-3 py-1.5 text-xs rounded-full border transition-colors"
        :class="statusFilter === tab.value
          ? 'bg-gray-600 border-gray-500 text-white font-medium'
          : 'border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600'"
      >
        {{ tab.label }}
        <span class="ml-1 opacity-60">{{ countByStatus(tab.value) }}</span>
      </button>
    </div>

    <!-- Concurrency panel -->
    <div class="card p-4 mb-6">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-gray-300">Runtime concurrency</h2>
        <span class="text-xs text-gray-500">updated every 5s</span>
      </div>
      <div class="grid grid-cols-4 gap-4">
        <div class="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <p class="text-2xl font-bold" :class="concurrency.running_executions > 0 ? 'text-blue-400' : 'text-gray-400'">
            {{ concurrency.running_executions ?? '—' }}
          </p>
          <p class="text-xs text-gray-500 mt-0.5">Running now</p>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <p class="text-2xl font-bold text-gray-300">{{ concurrency.worker_threads ?? '—' }}</p>
          <p class="text-xs text-gray-500 mt-0.5">Worker threads</p>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <p class="text-2xl font-bold text-gray-300">{{ concurrency.total_threads ?? '—' }}</p>
          <p class="text-xs text-gray-500 mt-0.5">Total threads</p>
        </div>
        <div class="bg-gray-900 rounded-lg p-3 border border-gray-700">
          <p class="text-xs font-mono text-gray-400 leading-5 max-h-12 overflow-hidden">
            <span
              v-for="t in (concurrency.threads ?? []).filter(t => t.daemon && t.name.startsWith('Thread-'))"
              :key="t.name"
              class="inline-block mr-2"
              :class="t.alive ? 'text-blue-400' : 'text-gray-600'"
            >{{ t.name }}</span>
            <span v-if="!(concurrency.threads ?? []).filter(t => t.daemon && t.name.startsWith('Thread-')).length" class="text-gray-600 italic">idle</span>
          </p>
          <p class="text-xs text-gray-500 mt-0.5">Active fetcher threads</p>
        </div>
      </div>
    </div>

    <div v-if="loading && executions.length === 0" class="text-gray-400 text-center py-16">
      Loading...
    </div>

    <div v-else-if="filteredExecutions.length === 0" class="text-gray-400 text-center py-16">
      {{ executions.length === 0 ? 'No executions yet. Run a resource to see it here.' : 'No processes match this filter.' }}
    </div>

    <div v-else class="space-y-3 max-h-[calc(100vh-320px)] overflow-y-auto pr-1">
      <div
        v-for="ex in filteredExecutions"
        :key="ex.id"
        class="card"
      >
        <!-- Card header -->
        <div class="p-4">
          <div class="flex items-start justify-between gap-4">
            <!-- Status badge + name -->
            <div class="flex items-center gap-3 min-w-0">
              <span :class="statusClass(ex.status)" class="text-xs font-bold px-2 py-1 rounded-full whitespace-nowrap">
                {{ statusLabel(ex.status) }}
              </span>
              <div class="min-w-0">
                <p class="font-medium text-sm truncate">
                  {{ resourceName(ex.resourceId, ex) }}
                  <span v-if="execLabel(ex)" class="text-yellow-300 font-normal"> — {{ execLabel(ex) }}</span>
                </p>
                <p class="text-xs text-gray-500 mt-0.5">{{ formatDate(ex.startedAt) }}</p>
              </div>
            </div>

            <!-- Stats + actions -->
            <div class="flex items-center gap-3 flex-shrink-0">
              <div v-if="ex.totalRecords" class="text-right">
                <p class="text-lg font-bold text-blue-400">{{ ex.recordsLoaded?.toLocaleString() }}</p>
                <p class="text-xs text-gray-500">/ {{ ex.totalRecords?.toLocaleString() }} records</p>
              </div>
              <div v-if="ex.completedAt || ex.status === 'paused'" class="text-right">
                <p class="text-sm font-medium text-gray-300">{{ activeDuration(ex) }}</p>
                <p class="text-xs text-gray-500">{{ ex.activeSeconds ? 'active time' : 'duration' }}</p>
              </div>
              <div v-else-if="ex.status === 'running'" class="text-right">
                <p class="text-sm font-medium text-yellow-400">{{ elapsed(ex.startedAt) }}</p>
                <p class="text-xs text-gray-500">elapsed</p>
              </div>

              <!-- Log toggle -->
              <button
                @click="toggleLog(ex)"
                class="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded border transition-colors"
                :class="openLog === ex.id
                  ? 'bg-gray-700 border-gray-500 text-white'
                  : 'border-gray-600 text-gray-400 hover:text-white hover:border-gray-400'"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414A1 1 0 0121 9.586V19a2 2 0 01-2 2z"/>
                </svg>
                {{ openLog === ex.id ? 'Hide logs' : 'View logs' }}
              </button>

              <!-- Pausing… indicator (pause requested but still running) -->
              <span
                v-if="ex.status === 'running' && ex.pauseRequested"
                class="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded border border-yellow-800 text-yellow-600 cursor-default"
                title="Waiting for current page to finish…"
              >
                <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Pausing…
              </span>

              <!-- Pause button (running, not yet requested) -->
              <button
                v-else-if="ex.status === 'running'"
                @click="doPause(ex)"
                class="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded border border-yellow-800 text-yellow-500 hover:bg-yellow-950 hover:border-yellow-600 hover:text-yellow-300 transition-colors"
                title="Pause at next page boundary"
              >
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z"/>
                </svg>
                Pause
              </button>

              <!-- Restarting… indicator (resume requested, waiting for thread) -->
              <span
                v-if="ex.status === 'paused' && resumingIds.has(ex.id)"
                class="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded border border-green-800 text-green-600 cursor-default"
                title="Launching thread…"
              >
                <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                </svg>
                Restarting…
              </span>

              <!-- Resume button (paused, not yet requested) -->
              <button
                v-else-if="ex.status === 'paused'"
                @click="doResume(ex)"
                class="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded border border-green-800 text-green-500 hover:bg-green-950 hover:border-green-600 hover:text-green-300 transition-colors"
                title="Resume execution"
              >
                <svg class="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7L8 5z"/>
                </svg>
                Resume
              </button>

              <!-- Kill button (running or paused) -->
              <button
                v-if="ex.status === 'running' || ex.status === 'paused'"
                @click="confirmAbort(ex)"
                class="flex items-center gap-1.5 px-2 py-1.5 text-xs rounded border border-red-900 text-red-500 hover:bg-red-950 hover:border-red-600 hover:text-red-300 transition-colors"
                title="Kill process"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 12a9 9 0 11-18 0 9 9 0 0118 0zM9 10a1 1 0 011-1h4a1 1 0 011 1v4a1 1 0 01-1 1h-4a1 1 0 01-1-1v-4z"/>
                </svg>
                Kill
              </button>

              <!-- Delete button (non-running, non-paused) -->
              <button
                v-if="ex.status !== 'running' && ex.status !== 'paused'"
                @click="confirmDelete(ex)"
                class="flex items-center gap-1 px-2 py-1.5 text-xs rounded border border-gray-700 text-gray-500 hover:border-red-700 hover:text-red-400 transition-colors"
                title="Remove from list"
              >
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                </svg>
              </button>
            </div>
          </div>

          <!-- Progress bar + stats row -->
          <div v-if="ex.status === 'running' || ex.status === 'completed' || ex.status === 'failed'" class="mt-3 space-y-2">

            <!-- Bar with % overlay -->
            <div class="relative h-5 bg-gray-700 rounded-full overflow-hidden">
              <div
                :class="ex.status === 'failed' ? 'bg-red-600' : ex.status === 'running' ? 'bg-blue-600' : 'bg-green-600'"
                class="h-full rounded-full transition-all duration-700"
                :style="{ width: (progressPct(ex) ?? (ex.status === 'running' ? 8 : 0)) + '%' }"
              ></div>
              <span class="absolute inset-0 flex items-center justify-center text-xs font-semibold text-white mix-blend-plus-lighter select-none">
                <template v-if="progressPct(ex) != null">{{ progressPct(ex) }}%</template>
                <template v-else-if="ex.status === 'running'">extracting…</template>
              </span>
            </div>

            <!-- Stats chips: records · ETA · params · memory -->
            <div class="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-gray-400">

              <!-- Records -->
              <span v-if="ex.totalRecords">
                <span class="text-white font-medium">{{ ex.totalRecords.toLocaleString() }}</span> records
                <template v-if="ex.recordsLoaded">
                  · <span class="text-green-400">{{ ex.recordsLoaded.toLocaleString() }}</span> loaded
                </template>
              </span>

              <!-- ETA (only when we can compute a rate) -->
              <span v-if="eta(ex)" class="text-yellow-400 font-medium">
                ≈ {{ eta(ex) }} remaining
              </span>

              <!-- Execution param overrides — hidden when already shown in the title label -->
              <template v-if="!execLabel(ex) && ex.executionParams && Object.keys(ex.executionParams).length">
                <span v-for="(v, k) in ex.executionParams" :key="k"
                  class="bg-blue-900/50 border border-blue-800 text-blue-300 px-1.5 py-0.5 rounded font-mono">
                  {{ k }}={{ v }}
                </span>
              </template>

              <!-- Key resource params (page_size, num_workers) -->
              <template v-for="tag in resourceParamTags(ex.resourceId)" :key="tag">
                <span class="bg-gray-700/60 border border-gray-600 text-gray-400 px-1.5 py-0.5 rounded font-mono">{{ tag }}</span>
              </template>

              <!-- Memory (only for running, from concurrency poll) -->
              <span v-if="ex.status === 'running' && concurrency.process_mem_rss_mb" class="text-purple-400">
                RAM proceso: {{ concurrency.process_mem_rss_mb }} MB
                <template v-if="concurrency.ram_total_mb">
                  ({{ Math.round(concurrency.process_mem_rss_mb / concurrency.ram_total_mb * 100) }}% of {{ Math.round(concurrency.ram_total_mb / 1024) }} GB)
                </template>
              </span>

            </div>
          </div>

          <!-- Error -->
          <div v-if="ex.errorMessage" class="mt-3 text-xs text-red-400 bg-red-950 bg-opacity-40 border border-red-800 rounded p-2 font-mono">
            {{ ex.errorMessage }}
          </div>
        </div>

        <!-- Log viewer panel -->
        <div v-if="openLog === ex.id" class="border-t border-gray-700">
          <!-- Settings bar -->
          <div class="bg-gray-800 px-4 py-3 space-y-3">
            <div class="flex items-center gap-3 flex-wrap">
              <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer select-none">
                <button type="button" @click="logCfg.autoRefresh = !logCfg.autoRefresh"
                  :class="logCfg.autoRefresh ? 'bg-blue-500' : 'bg-gray-600'"
                  class="relative inline-flex h-4 w-8 items-center rounded-full transition-colors focus:outline-none">
                  <span :class="logCfg.autoRefresh ? 'translate-x-4' : 'translate-x-1'" class="inline-block h-3 w-3 transform rounded-full bg-white transition-transform"></span>
                </button>
                Auto-refresh
              </label>
              <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer select-none">
                <button type="button" @click="logCfg.wrap = !logCfg.wrap"
                  :class="logCfg.wrap ? 'bg-blue-500' : 'bg-gray-600'"
                  class="relative inline-flex h-4 w-8 items-center rounded-full transition-colors focus:outline-none">
                  <span :class="logCfg.wrap ? 'translate-x-4' : 'translate-x-1'" class="inline-block h-3 w-3 transform rounded-full bg-white transition-transform"></span>
                </button>
                Wrap lines
              </label>
              <label class="flex items-center gap-2 text-xs text-gray-300 cursor-pointer select-none">
                <button type="button" @click="logCfg.timestamps = !logCfg.timestamps"
                  :class="logCfg.timestamps ? 'bg-blue-500' : 'bg-gray-600'"
                  class="relative inline-flex h-4 w-8 items-center rounded-full transition-colors focus:outline-none">
                  <span :class="logCfg.timestamps ? 'translate-x-4' : 'translate-x-1'" class="inline-block h-3 w-3 transform rounded-full bg-white transition-transform"></span>
                </button>
                Timestamps
              </label>
              <div class="flex items-center gap-1.5">
                <span class="text-xs text-gray-400">Fetch</span>
                <select v-model="logCfg.since" @change="fetchLog(ex)"
                  class="text-xs bg-gray-700 border border-gray-600 text-gray-200 rounded px-2 py-1 focus:outline-none">
                  <option :value="0">All logs</option>
                  <option :value="1440">Last day</option>
                  <option :value="240">Last 4 hours</option>
                  <option :value="60">Last hour</option>
                  <option :value="10">Last 10 minutes</option>
                </select>
              </div>
              <div class="flex items-center gap-1.5 flex-1 min-w-32">
                <span class="text-xs text-gray-400">Search</span>
                <input v-model="logCfg.filter" @input="fetchLog(ex)" placeholder="Filter..."
                  class="flex-1 text-xs bg-gray-700 border border-gray-600 text-gray-200 rounded px-2 py-1 focus:outline-none placeholder-gray-500"/>
              </div>
              <div class="flex items-center gap-1.5">
                <span class="text-xs text-gray-400">Lines</span>
                <input v-model.number="logCfg.lines" @change="fetchLog(ex)" type="number" min="10" max="5000"
                  class="w-20 text-xs bg-gray-700 border border-gray-600 text-gray-200 rounded px-2 py-1 focus:outline-none"/>
              </div>
            </div>
            <div class="flex items-center gap-2">
              <button @click="downloadLog(ex)" class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-900 hover:bg-gray-700 text-white rounded border border-gray-600 transition-colors">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                </svg>
                Download logs
              </button>
              <button @click="copyLog()" class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-900 hover:bg-gray-700 text-white rounded border border-gray-600 transition-colors">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                </svg>
                {{ copied ? 'Copied!' : 'Copy' }}
              </button>
              <button @click="fetchLog(ex)" class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-gray-900 hover:bg-gray-700 text-gray-300 rounded border border-gray-600 transition-colors">
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                Refresh
              </button>
              <span v-if="logLoading" class="text-xs text-gray-500 ml-1 animate-pulse">Loading...</span>
            </div>
          </div>

          <!-- Terminal output -->
          <div ref="logTerminal"
            class="bg-gray-950 font-mono text-xs leading-5 h-80 overflow-y-auto p-3"
            :class="logCfg.wrap ? 'whitespace-pre-wrap break-all' : 'whitespace-pre overflow-x-auto'">
            <div v-if="logLines.length === 0" class="text-gray-600 italic">
              <span v-if="logLoading">Loading logs...</span>
              <span v-else-if="logNotFound">No log file for this execution — it ran before logging was enabled.</span>
              <span v-else-if="logCfg.since > 0">No lines in the selected time range. Try <a class="underline cursor-pointer text-gray-400" @click="logCfg.since = 0; fetchLog(executions.find(e => e.id === openLog))">All logs</a>.</span>
              <span v-else>No log output yet.</span>
            </div>
            <div v-else>
              <div v-for="(line, i) in displayLines" :key="i" :class="lineClass(line)">{{ line }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Confirm dialog (abort) -->
  <ConfirmDialog
    v-if="dialog.show"
    :title="dialog.title"
    :message="dialog.message"
    :confirmText="dialog.confirmText"
    :dangerMode="true"
    @confirm="handleDialogConfirm"
    @cancel="dialog.show = false"
  />

  <!-- Delete process modal -->
  <div
    v-if="showDeleteModal"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click.self="showDeleteModal = false"
  >
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
      <h2 class="text-lg font-bold mb-3">Delete process</h2>
      <p class="text-sm text-gray-300 mb-4">
        Are you sure you want to delete the execution record for
        <strong>{{ resourceName(executionToDelete?.resourceId, executionToDelete) }}</strong>?
        The log and execution history entry will be removed.
      </p>
      <label class="flex items-start gap-2 text-sm text-gray-300 mb-5 cursor-pointer">
        <input type="checkbox" v-model="hardDeleteFlag" class="accent-red-500 mt-0.5" />
        <span>Permanently delete</span>
      </label>
      <p v-if="deleteError" class="text-xs text-red-400 mb-3 break-words">{{ deleteError }}</p>
      <div class="flex justify-end gap-2">
        <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
        <button @click="handleDelete" class="btn btn-danger">Delete</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { fetchResourceExecutions, fetchResources, deleteExecution, abortExecution, pauseExecution, resumeExecution } from '../api/graphql.js'
import ConfirmDialog from '../components/ConfirmDialog.vue'

const executions = ref([])
const resources = ref([])
const loading = ref(true)
const concurrency = ref({})
const statusFilter = ref('all')
const resumingIds = ref(new Set())
let timer = null
const now = ref(Date.now())

const statusTabs = [
  { value: 'all',       label: 'All' },
  { value: 'running',   label: 'Running' },
  { value: 'paused',    label: 'Paused' },
  { value: 'completed', label: 'Done' },
  { value: 'failed',    label: 'Failed' },
  { value: 'aborted',   label: 'Aborted' },
]

const filteredExecutions = computed(() => {
  if (statusFilter.value === 'all') return executions.value
  return executions.value.filter(e => e.status === statusFilter.value)
})

function countByStatus(val) {
  if (val === 'all') return executions.value.length
  return executions.value.filter(e => e.status === val).length
}

// Log viewer state
const openLog = ref(null)
const logLines = ref([])
const logNotFound = ref(false)
const logLoading = ref(false)
const copied = ref(false)
const logTerminal = ref(null)
let sseSource = null
let logRefreshTimer = null

const logCfg = ref({
  autoRefresh: true,
  wrap: true,
  timestamps: true,
  since: 0,
  filter: '',
  lines: 100,
})

// ---- computed ----
const displayLines = computed(() => {
  if (logCfg.value.timestamps) return logLines.value
  return logLines.value.map(l => l.replace(/^\[\d{2}:\d{2}:\d{2}\] /, ''))
})

// ---- execution list helpers ----
function resourceName(id, ex) {
  // Preferir el snapshot histórico guardado en la ejecución; fallback al nombre actual del resource
  if (ex?.resourceName) return ex.resourceName
  return resources.value.find(r => r.id === id)?.name ?? id
}
function execLabel(ex) {
  const p = ex.executionParams
  if (!p || !Object.keys(p).length) return null
  const resource = resources.value.find(r => r.id === ex.resourceId)
  const resourceParams = resource?.params ?? []
  const pairs = Object.entries(p).filter(([, v]) => v != null && String(v).trim())
  return pairs.length ? pairs.map(([k, v]) => {
    if (k === 'bounding_value') {
      const fieldParam = resourceParams.find(rp => rp.key === 'bounding_field')
      const fieldName = fieldParam?.value ?? 'bounding_value'
      return `${fieldName}≤${v}`
    }
    return `${k}=${v}`
  }).join(' · ') : null
}
function statusLabel(s) {
  return { running: 'RUNNING', completed: 'DONE', failed: 'FAILED', pending: 'PENDING', aborted: 'ABORTED', paused: 'PAUSED' }[s] ?? s.toUpperCase()
}
function statusClass(s) {
  return {
    running:   'bg-blue-900 text-blue-300 border border-blue-700',
    completed: 'bg-green-900 text-green-300 border border-green-700',
    failed:    'bg-red-900 text-red-300 border border-red-700',
    aborted:   'bg-orange-900 text-orange-300 border border-orange-700',
    paused:    'bg-yellow-900 text-yellow-300 border border-yellow-700',
    pending:   'bg-gray-700 text-gray-300 border border-gray-600',
  }[s] ?? 'bg-gray-700 text-gray-300'
}
// Backend stores datetime.utcnow() without timezone info — append Z so browser parses as UTC
function utc(iso) {
  if (!iso) return null
  return new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z')
}
function formatDate(iso) {
  if (!iso) return '—'
  return utc(iso).toLocaleString('es-ES', { dateStyle: 'short', timeStyle: 'medium' })
}
function fmtSeconds(s) {
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`
}
function duration(start, end) {
  if (!start || !end) return '—'
  return fmtSeconds(Math.round((utc(end) - utc(start)) / 1000))
}
function activeDuration(ex) {
  // Prefer accumulated active_seconds (excludes paused periods)
  if (ex.activeSeconds != null) return fmtSeconds(ex.activeSeconds)
  // Fallback: wall-clock duration
  return duration(ex.startedAt, ex.completedAt)
}
function elapsed(start) {
  if (!start) return '—'
  const s = Math.round((now.value - utc(start)) / 1000)
  if (s < 60) return `${s}s`
  if (s < 3600) return `${Math.floor(s/60)}m ${s%60}s`
  return `${Math.floor(s/3600)}h ${Math.floor((s%3600)/60)}m`
}
function progressPct(ex) {
  if (ex.status === 'completed') return 100
  if (ex.status === 'failed')    return 100
  if (!ex.totalRecords)          return null
  if (!ex.recordsLoaded)         return null
  return Math.min(99, Math.round((ex.recordsLoaded / ex.totalRecords) * 100))
}

function eta(ex) {
  if (ex.status !== 'running') return null
  if (!ex.totalRecords || !ex.recordsLoaded || ex.recordsLoaded <= 0) return null
  const elapsedS = (now.value - utc(ex.startedAt)) / 1000
  const rate = ex.recordsLoaded / elapsedS          // records/s
  const remaining = ex.totalRecords - ex.recordsLoaded
  const etaS = Math.round(remaining / rate)
  if (etaS <= 0) return null
  if (etaS < 60)   return `${etaS}s`
  if (etaS < 3600) return `${Math.floor(etaS/60)}m ${etaS%60}s`
  return `${Math.floor(etaS/3600)}h ${Math.floor((etaS%3600)/60)}m`
}

const CONCURRENCY_KEYS = new Set([
  'num_workers','max_concurrent_requests','rate_limit_rps',
  'batch_size','retry_attempts',
])

function resourceParamTags(resourceId) {
  const res = resources.value.find(r => r.id === resourceId)
  if (!res?.params) return []
  return res.params
    .filter(p => CONCURRENCY_KEYS.has(p.key) && p.value)
    .map(p => `${p.key}=${p.value}`)
}

// ---- confirm dialog (abort only) ----
const dialog = ref({ show: false, title: '', message: '', confirmText: 'Confirm', _resolve: null })

function showConfirm(title, message, confirmText = 'Confirm') {
  return new Promise(resolve => {
    dialog.value = { show: true, title, message, confirmText, _resolve: resolve }
  })
}

function handleDialogConfirm() {
  dialog.value.show = false
  dialog.value._resolve?.(true)
}

// ---- delete execution modal ----
const showDeleteModal = ref(false)
const executionToDelete = ref(null)
const hardDeleteFlag = ref(false)

function confirmDelete(ex) {
  executionToDelete.value = ex
  hardDeleteFlag.value = false
  deleteError.value = ''
  showDeleteModal.value = true
}

const deleteError = ref('')

async function handleDelete() {
  if (!executionToDelete.value) return
  deleteError.value = ''
  try {
    await deleteExecution(executionToDelete.value.id, hardDeleteFlag.value)
  } catch (e) {
    const msg = e?.response?.errors?.[0]?.message || e?.message || String(e)
    deleteError.value = msg
    return
  }
  executions.value = executions.value.filter(e => e.id !== executionToDelete.value.id)
  if (openLog.value === executionToDelete.value.id) closeLog()
  showDeleteModal.value = false
  executionToDelete.value = null
  hardDeleteFlag.value = false
}

// ---- pause / resume / kill / delete ----
async function doPause(ex) {
  const res = await pauseExecution(ex.id)
  if (res?.pauseExecution?.success) {
    // Mark pauseRequested locally so the UI shows "Pausing…" immediately.
    // The polling will set status='paused' once the fetcher actually stops.
    const idx = executions.value.findIndex(e => e.id === ex.id)
    if (idx !== -1) executions.value[idx] = { ...executions.value[idx], pauseRequested: true }
  }
}

async function doResume(ex) {
  resumingIds.value = new Set([...resumingIds.value, ex.id])
  const res = await resumeExecution(ex.id)
  if (!res?.resumeExecution?.success) {
    resumingIds.value.delete(ex.id)
    resumingIds.value = new Set(resumingIds.value)
  }
  // On success, leave resumingIds until polling picks up status='running' and clears it
}

async function confirmAbort(ex) {
  const ok = await showConfirm('Matar proceso', `¿Matar el proceso en curso de "${resourceName(ex.resourceId, ex)}"?`, 'Matar')
  if (!ok) return
  const res = await abortExecution(ex.id)
  if (res?.abortExecution?.success) {
    const idx = executions.value.findIndex(e => e.id === ex.id)
    if (idx !== -1) executions.value[idx] = { ...executions.value[idx], status: 'aborted' }
  }
}

// confirmDelete is now defined below with the delete modal state

// ---- log viewer ----
function lineClass(line) {
  if (line.includes('FAILED') || line.includes('ERROR') || line.includes('Error')) return 'text-red-400'
  if (line.includes('WARNING')) return 'text-yellow-400'
  if (line.includes('COMPLETED') || line.includes('Dataset created') || line.includes('Loaded ')) return 'text-green-400'
  if (/\[[1-5]\/5\]/.test(line)) return 'text-blue-300'
  if (line.includes('Ejecutando')) return 'text-cyan-300'
  return 'text-gray-300'
}
function toggleLog(ex) {
  if (openLog.value === ex.id) { closeLog(); return }
  closeLog()
  openLog.value = ex.id
  logLines.value = []
  logNotFound.value = false
  fetchLog(ex)
  if (ex.status === 'running') startSSE(ex)
}
function closeLog() {
  openLog.value = null
  logLines.value = []
  if (sseSource) { sseSource.close(); sseSource = null }
  if (logRefreshTimer) { clearInterval(logRefreshTimer); logRefreshTimer = null }
}
async function fetchLog(ex) {
  logLoading.value = true
  logNotFound.value = false
  try {
    const params = new URLSearchParams({ lines: logCfg.value.lines, filter: logCfg.value.filter, since: logCfg.value.since })
    const res = await fetch(`/api/executions/${ex.id}/logs?${params}`)
    if (res.status === 404) {
      logNotFound.value = true
      logLines.value = []
    } else if (res.ok) {
      const text = await res.text()
      logLines.value = text ? text.split('\n').filter(l => l.trim()) : []
      scrollToBottom()
    }
  } finally {
    logLoading.value = false
  }
}
function startSSE(ex) {
  if (sseSource) sseSource.close()
  const params = new URLSearchParams({ follow: true, filter: logCfg.value.filter })
  sseSource = new EventSource(`/api/executions/${ex.id}/logs?${params}`)
  sseSource.onmessage = (e) => {
    if (e.data) { logLines.value.push(e.data); scrollToBottom() }
  }
  sseSource.addEventListener('done', () => {
    sseSource.close(); sseSource = null
    fetchLog(ex)
  })
  sseSource.onerror = () => { sseSource?.close(); sseSource = null }
}
watch(() => logCfg.value.autoRefresh, (on) => {
  if (!on && logRefreshTimer) { clearInterval(logRefreshTimer); logRefreshTimer = null }
})
watch(openLog, (id) => {
  if (!id) return
  if (logRefreshTimer) { clearInterval(logRefreshTimer); logRefreshTimer = null }
  if (logCfg.value.autoRefresh) {
    logRefreshTimer = setInterval(() => {
      const ex = executions.value.find(e => e.id === id)
      if (ex && ex.status !== 'running') fetchLog(ex)
    }, 5000)
  }
})
function scrollToBottom() {
  nextTick(() => { if (logTerminal.value) logTerminal.value.scrollTop = logTerminal.value.scrollHeight })
}
function copyLog() {
  navigator.clipboard.writeText(displayLines.value.join('\n')).then(() => {
    copied.value = true; setTimeout(() => { copied.value = false }, 2000)
  })
}
function downloadLog(ex) {
  const blob = new Blob([logLines.value.join('\n')], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = `execution-${ex.id.slice(0, 8)}.log`; a.click()
  URL.revokeObjectURL(url)
}

// ---- data loading ----
async function loadConcurrency() {
  try {
    const res = await fetch('/api/system/concurrency')
    if (res.ok) concurrency.value = await res.json()
  } catch {}
}
async function load() {
  try {
    const [exData, resData] = await Promise.all([
      fetchResourceExecutions(),
      fetchResources(false),
    ])
    executions.value = (exData?.resourceExecutions ?? [])
      .slice()
      .sort((a, b) => utc(b.startedAt) - utc(a.startedAt))
    resources.value = resData?.resources ?? []
    // Clear resumingIds for executions that have transitioned to running
    if (resumingIds.value.size) {
      const nowRunning = new Set(executions.value.filter(e => e.status === 'running').map(e => e.id))
      resumingIds.value = new Set([...resumingIds.value].filter(id => !nowRunning.has(id)))
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  load(); loadConcurrency()
  timer = setInterval(() => { load(); loadConcurrency(); now.value = Date.now() }, 5000)
  setInterval(() => { now.value = Date.now() }, 1000)
})
onUnmounted(() => { clearInterval(timer); closeLog() })
</script>
