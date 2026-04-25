<template>
  <div class="p-8 max-w-5xl">
    <h1 class="text-3xl font-bold mb-6">Discovering</h1>

    <!-- Resource selector -->
    <div class="card p-5 mb-6">
      <label class="block text-sm text-gray-400 mb-2">Crawler (Web Tree)</label>
      <div v-if="loadingResources" class="text-sm text-gray-500">Cargando recursos…</div>
      <select v-else v-model="selectedResourceId" class="input w-full">
        <option value="">— Selecciona un crawler —</option>
        <option v-for="r in crawlerResources" :key="r.id" :value="r.id">
          {{ r.name }}
        </option>
      </select>
      <button
        @click="launchDiscover"
        :disabled="!selectedResourceId || phase === 'running'"
        class="btn btn-primary mt-4"
        :class="(!selectedResourceId || phase === 'running') ? 'opacity-50 cursor-not-allowed' : ''"
      >
        {{ phase === 'running' ? 'Descubriendo…' : 'Lanzar Discovery' }}
      </button>
    </div>

    <!-- Log panel -->
    <div v-if="phase === 'running' || phase === 'error'" class="card p-5 mb-6">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm font-medium text-gray-300">Log</span>
        <span
          class="text-xs px-2 py-0.5 rounded-full font-medium"
          :class="{
            'bg-blue-900 text-blue-300': phase === 'running',
            'bg-red-900 text-red-300': phase === 'error',
          }"
        >{{ phase }}</span>
      </div>
      <div
        ref="logEl"
        class="bg-gray-900 rounded p-3 font-mono text-xs text-gray-300 h-48 overflow-y-auto whitespace-pre-wrap"
      >{{ logText || '…' }}</div>
    </div>

    <!-- Error -->
    <div v-if="phase === 'error'" class="bg-red-900 border border-red-700 rounded p-4 text-red-200 mb-6">
      {{ errorMsg }}
      <button @click="reset" class="ml-4 text-xs underline">Reintentar</button>
    </div>

    <!-- Candidatos -->
    <div v-if="candidates.length">
      <div class="flex items-center justify-between mb-3">
        <p class="text-sm text-gray-400">
          {{ candidates.length }} candidato{{ candidates.length !== 1 ? 's' : '' }}
          <span v-if="filterStatus !== 'all'" class="text-gray-500"> ({{ filterStatus }})</span>
        </p>
        <div class="flex gap-2 text-xs">
          <button
            v-for="s in ['all','discovered','reviewed','promoted','discarded']" :key="s"
            @click="filterStatus = s"
            :class="filterStatus === s ? 'text-purple-300 underline' : 'text-gray-500 hover:text-gray-300'"
          >{{ s }}</button>
        </div>
      </div>

      <div class="space-y-3 mb-6">
        <div
          v-for="c in filteredCandidates" :key="c.id"
          class="border rounded-lg p-4 transition-colors border-gray-700 bg-gray-800"
        >
          <div class="flex items-start gap-3">
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 mb-2">
                <span class="text-sm font-medium text-gray-200">{{ c.suggestedName || '—' }}</span>
                <span class="text-xs px-2 py-0.5 rounded font-medium"
                  :class="statusBadge(c.status)">{{ c.status }}</span>
                <span v-if="c.confidence != null"
                      class="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">
                  conf {{ (c.confidence * 100).toFixed(0) }}%
                </span>
              </div>

              <p class="text-xs font-mono text-gray-500 truncate mb-2" :title="c.pathTemplate">
                {{ c.pathTemplate }}
              </p>

              <div class="flex flex-wrap gap-2 text-xs text-gray-400 mb-2">
                <span class="px-1.5 py-0.5 rounded bg-gray-700">
                  {{ (c.matchedUrls || []).length }} URL{{ (c.matchedUrls || []).length !== 1 ? 's' : '' }}
                </span>
                <span v-for="(n, ext) in (c.fileTypes || {})" :key="ext"
                      class="px-1.5 py-0.5 rounded bg-gray-700 font-mono uppercase">{{ ext }}: {{ n }}</span>
                <span v-for="d in (c.dimensions || [])" :key="d.name"
                      class="px-1.5 py-0.5 rounded bg-purple-900 text-purple-200 font-mono">
                  {{ d.kind }}{{ (d.sample_values || []).length ? ` (${(d.sample_values || []).length})` : '' }}
                </span>
              </div>

              <details class="text-xs text-gray-500" v-if="(c.matchedUrls || []).length">
                <summary class="cursor-pointer hover:text-gray-300">Ver URLs</summary>
                <ul class="mt-2 space-y-1 max-h-40 overflow-y-auto font-mono">
                  <li v-for="u in (c.matchedUrls || []).slice(0, 50)" :key="u" class="truncate">{{ u }}</li>
                  <li v-if="(c.matchedUrls || []).length > 50" class="italic">… y {{ c.matchedUrls.length - 50 }} más</li>
                </ul>
              </details>
            </div>

            <div class="flex flex-col gap-2 flex-shrink-0">
              <button v-if="c.status === 'discovered' || c.status === 'reviewed'"
                      @click="openPromote(c)"
                      class="btn btn-primary text-xs px-3 py-1">Promover</button>
              <button v-if="c.status === 'discovered' || c.status === 'reviewed'"
                      @click="discard(c)"
                      class="btn btn-secondary text-xs px-3 py-1">Descartar</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="phase === 'idle' && selectedResourceId && !loadingResources" class="text-gray-500 text-sm">
      Sin candidatos aún para este crawler. Lanza un Discovery.
    </div>

    <!-- Modal de promoción -->
    <div v-if="promoteCandidate" class="modal-overlay" @click.self="promoteCandidate = null">
      <div class="modal-card-sm p-6">
        <h2 class="text-lg font-bold mb-4">Promover a Resource</h2>
        <label class="block text-xs text-gray-400 mb-1">Nombre</label>
        <input v-model="promoteForm.name" class="input w-full mb-3" placeholder="nombre-unico" />
        <label class="block text-xs text-gray-400 mb-1">target_table</label>
        <input v-model="promoteForm.targetTable" class="input w-full mb-3" placeholder="snake_case" />
        <label class="block text-xs text-gray-400 mb-1">Schedule (cron, opcional)</label>
        <input v-model="promoteForm.schedule" class="input w-full mb-3" placeholder="0 3 * * 0" />
        <label class="flex items-center gap-2 text-xs text-gray-400 mb-4">
          <input type="checkbox" v-model="promoteForm.enableLoad" class="accent-purple-500" />
          Cargar a core (enable_load)
        </label>
        <div class="flex justify-end gap-2">
          <button @click="promoteCandidate = null" class="btn btn-secondary">Cancelar</button>
          <button @click="confirmPromote" :disabled="promoting" class="btn btn-primary">
            {{ promoting ? 'Promoviendo…' : 'Promover' }}
          </button>
        </div>
        <p v-if="promoteError" class="text-red-400 text-xs mt-2">{{ promoteError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import {
  fetchResources,
  executeResource,
  fetchResourceCandidates,
  promoteCandidate as gqlPromoteCandidate,
  discardCandidate,
} from '../api/graphql'

const loadingResources = ref(true)
const allResources = ref([])
const selectedResourceId = ref('')
const phase = ref('idle')   // idle | running | done | error
const logText = ref('')
const errorMsg = ref('')
const candidates = ref([])
const filterStatus = ref('all')
const logEl = ref(null)

const promoteCandidate = ref(null)
const promoteForm = ref({ name: '', targetTable: '', schedule: '', enableLoad: false })
const promoting = ref(false)
const promoteError = ref('')

let sseSource = null
let pollTimer = null

const crawlerResources = computed(() =>
  allResources.value.filter(r =>
    r.fetcher && !r.autoGenerated &&
    (r.fetcher.code === 'Web Tree' || r.fetcher.classPath?.toLowerCase().includes('web_tree_fetcher'))
  )
)

const filteredCandidates = computed(() => {
  if (filterStatus.value === 'all') return candidates.value
  return candidates.value.filter(c => c.status === filterStatus.value)
})

function statusBadge(status) {
  return {
    'bg-blue-900 text-blue-300': status === 'discovered',
    'bg-yellow-900 text-yellow-300': status === 'reviewed',
    'bg-green-900 text-green-300': status === 'promoted',
    'bg-gray-700 text-gray-400': status === 'discarded',
    'bg-purple-900 text-purple-300': status === 'merged' || status === 'split',
  }[status] || 'bg-gray-700 text-gray-300'
}

function nameToTable(name) {
  return (name || '').toLowerCase()
    .replace(/[^a-z0-9\s_]/g, '')
    .trim()
    .replace(/\s+/g, '_')
    .substring(0, 60)
}

function appendLog(line) {
  logText.value += (logText.value ? '\n' : '') + line
  nextTick(() => {
    if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight
  })
}

watch(selectedResourceId, async (id) => {
  if (!id) {
    candidates.value = []
    return
  }
  await loadCandidates()
})

async function loadCandidates() {
  if (!selectedResourceId.value) return
  const res = await fetchResourceCandidates({ crawlerResourceId: selectedResourceId.value })
  candidates.value = res?.resourceCandidates || []
}

async function launchDiscover() {
  if (!selectedResourceId.value) return
  phase.value = 'running'
  logText.value = ''
  errorMsg.value = ''

  const res = await executeResource(selectedResourceId.value, {})
  if (!res?.executeResource?.success) {
    phase.value = 'error'
    errorMsg.value = res?.executeResource?.message || 'Error al lanzar discovery'
    return
  }

  const execId = res.executeResource.executionId
  if (execId) startSSE(execId)
  startPolling(execId)
}

function startSSE(execId) {
  if (sseSource) sseSource.close()
  sseSource = new EventSource(`/api/executions/${execId}/logs?follow=true`)
  sseSource.onmessage = (e) => { if (e.data) appendLog(e.data) }
  sseSource.addEventListener('done', () => { sseSource?.close(); sseSource = null })
  sseSource.onerror = () => { sseSource?.close(); sseSource = null }
}

function startPolling(execId) {
  let polls = 0
  pollTimer = setInterval(async () => {
    polls++
    if (polls > 300) {
      clearInterval(pollTimer)
      phase.value = 'error'
      errorMsg.value = 'Discovery timed out — revisa los procesos'
      return
    }
    const before = candidates.value.length
    await loadCandidates()
    if (candidates.value.length > before || (execId && polls > 5)) {
      // Hay candidatos nuevos o ya pasó tiempo razonable
      if (candidates.value.length > before) {
        clearInterval(pollTimer)
        phase.value = 'idle'
        appendLog(`\nDISCOVER COMPLETADO — ${candidates.value.length} candidato(s)`)
      }
    }
  }, 2000)
}

function openPromote(c) {
  promoteCandidate.value = c
  promoteForm.value = {
    name: c.suggestedName || '',
    targetTable: nameToTable(c.suggestedName || ''),
    schedule: '',
    enableLoad: false,
  }
  promoteError.value = ''
}

async function confirmPromote() {
  if (!promoteCandidate.value) return
  if (!promoteForm.value.name || !promoteForm.value.targetTable) {
    promoteError.value = 'name y target_table son obligatorios'
    return
  }
  promoting.value = true
  promoteError.value = ''
  try {
    await gqlPromoteCandidate(promoteCandidate.value.id, {
      name: promoteForm.value.name,
      targetTable: promoteForm.value.targetTable,
      schedule: promoteForm.value.schedule || null,
      enableLoad: promoteForm.value.enableLoad,
      loadMode: 'upsert',
    })
    promoteCandidate.value = null
    await loadCandidates()
  } catch (e) {
    promoteError.value = e?.message || 'Error al promover'
  } finally {
    promoting.value = false
  }
}

async function discard(c) {
  if (!confirm(`¿Descartar candidato "${c.suggestedName || c.pathTemplate}"?`)) return
  await discardCandidate(c.id)
  await loadCandidates()
}

function reset() {
  clearInterval(pollTimer)
  sseSource?.close(); sseSource = null
  phase.value = 'idle'
  logText.value = ''
  errorMsg.value = ''
}

onMounted(async () => {
  try {
    const res = await fetchResources()
    allResources.value = res?.resources || []
  } catch (e) {
    console.error('Discovering: error loading resources', e)
  } finally {
    loadingResources.value = false
  }
})

onUnmounted(() => {
  clearInterval(pollTimer)
  sseSource?.close()
})
</script>
