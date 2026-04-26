<template>
  <!-- Full-height layout: top = controls, bottom = candidate list -->
  <div class="flex flex-col h-full">

    <!-- ── Top bar ── -->
    <div class="flex-shrink-0 bg-gray-800 border-b border-gray-700 px-4 sm:px-6 py-4 space-y-3">
      <div class="flex items-center justify-between gap-3">
        <h1 class="text-lg sm:text-xl font-bold text-white">Discovering</h1>
        <span v-if="phase === 'running'" class="text-xs px-2 py-0.5 rounded-full bg-blue-900 text-blue-300 animate-pulse">Crawleando…</span>
      </div>

      <!-- Crawler selector + launch -->
      <div class="flex flex-col sm:flex-row gap-2">
        <div v-if="loadingResources" class="text-sm text-gray-500 py-2">Cargando recursos…</div>
        <select
          v-else
          v-model="selectedResourceId"
          class="input flex-1 text-sm"
          :disabled="phase === 'running'"
        >
          <option value="">— Selecciona un crawler Web Tree —</option>
          <option v-for="r in crawlerResources" :key="r.id" :value="r.id">{{ r.name }}</option>
        </select>
        <button
          @click="launchDiscover"
          :disabled="!selectedResourceId || phase === 'running'"
          class="btn btn-primary text-sm px-5 flex-shrink-0"
          :class="(!selectedResourceId || phase === 'running') ? 'opacity-50 cursor-not-allowed' : ''"
        >
          {{ phase === 'running' ? 'Descubriendo…' : 'Lanzar Discovery' }}
        </button>
      </div>

      <!-- Log panel (visible while running or error) -->
      <div v-if="phase === 'running' || phase === 'error'">
        <div
          ref="logEl"
          class="bg-gray-900 rounded-lg px-3 py-2 font-mono text-xs text-gray-400 h-28 overflow-y-auto whitespace-pre-wrap"
        >{{ logText || '…' }}</div>
        <p v-if="phase === 'error'" class="text-xs text-red-400 mt-2">
          {{ errorMsg }}
          <button @click="reset" class="ml-3 underline">Reintentar</button>
        </p>
      </div>
    </div>

    <!-- ── Filter bar (when there are candidates) ── -->
    <div
      v-if="candidates.length"
      class="flex-shrink-0 flex flex-wrap items-center gap-2 px-4 sm:px-6 py-2 bg-gray-800/60 border-b border-gray-700/50"
    >
      <span class="text-xs text-gray-500">{{ filteredCandidates.length }} / {{ candidates.length }}</span>
      <div class="flex gap-1 flex-wrap">
        <button
          v-for="s in statuses" :key="s"
          @click="filterStatus = s"
          class="text-xs px-2.5 py-0.5 rounded-full border transition-colors"
          :class="filterStatus === s
            ? statusActiveClass(s)
            : 'border-gray-600 text-gray-500 hover:border-gray-400 hover:text-gray-300'"
        >{{ s }}</button>
      </div>
      <!-- Merge action (requires ≥2 selected) -->
      <div v-if="selection.size >= 2" class="flex items-center gap-2 ml-auto">
        <span class="text-xs text-gray-400">{{ selection.size }} sel.</span>
        <button @click="openMerge" class="btn btn-secondary text-xs px-3 py-1">Fundir</button>
        <button @click="selection.clear(); selection = new Set()" class="text-xs text-gray-500 hover:text-gray-300 underline">Deselect</button>
      </div>
    </div>

    <!-- ── Candidate list ── -->
    <div class="flex-1 overflow-y-auto px-4 sm:px-6 py-4 space-y-3">

      <p v-if="!candidates.length && phase === 'idle' && selectedResourceId && !loadingResources"
         class="text-sm text-gray-500">
        Sin candidatos aún para este crawler. Lanza un Discovery.
      </p>

      <div
        v-for="c in filteredCandidates" :key="c.id"
        class="rounded-xl border transition-colors"
        :class="[
          selection.has(c.id) ? 'border-purple-500 bg-purple-950/30' : 'border-gray-700 bg-gray-800',
          ['discovered','reviewed'].includes(c.status) ? 'cursor-pointer' : ''
        ]"
        @click="toggleSelect(c)"
      >
        <!-- Card header -->
        <div class="flex items-start gap-3 p-4">
          <!-- Checkbox hint -->
          <div
            v-if="['discovered','reviewed'].includes(c.status)"
            class="mt-0.5 w-4 h-4 flex-shrink-0 rounded border flex items-center justify-center transition-colors"
            :class="selection.has(c.id) ? 'bg-purple-500 border-purple-500' : 'border-gray-600'"
          >
            <svg v-if="selection.has(c.id)" class="w-3 h-3 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7"/>
            </svg>
          </div>
          <div v-else class="w-4 flex-shrink-0" />

          <!-- Main content -->
          <div class="flex-1 min-w-0">
            <div class="flex flex-wrap items-center gap-2 mb-1.5">
              <span class="text-sm font-medium text-gray-100 truncate">{{ c.suggestedName || '—' }}</span>
              <span class="text-xs px-1.5 py-0.5 rounded font-medium" :class="statusBadge(c.status)">{{ c.status }}</span>
              <span v-if="c.confidence != null" class="text-xs px-1.5 py-0.5 rounded bg-gray-700 text-gray-400 font-mono">
                {{ (c.confidence * 100).toFixed(0) }}%
              </span>
            </div>

            <p class="text-xs font-mono text-gray-500 truncate mb-2" :title="c.pathTemplate">{{ c.pathTemplate }}</p>

            <!-- Chips -->
            <div class="flex flex-wrap gap-1.5 text-xs">
              <span class="px-1.5 py-0.5 rounded bg-gray-700 text-gray-400">
                {{ (c.matchedUrls || []).length }} URL{{ (c.matchedUrls || []).length !== 1 ? 's' : '' }}
              </span>
              <span
                v-for="(n, ext) in (c.fileTypes || {})"
                :key="ext"
                class="px-1.5 py-0.5 rounded bg-gray-700 text-gray-300 font-mono uppercase"
              >{{ ext }}: {{ n }}</span>
              <span
                v-for="d in (c.dimensions || [])" :key="d.name"
                class="px-1.5 py-0.5 rounded bg-purple-900/60 text-purple-300 font-mono"
              >{{ d.kind }}{{ (d.sample_values || []).length ? ` ×${d.sample_values.length}` : '' }}</span>
            </div>

            <!-- Expandable URL list -->
            <details class="mt-2 text-xs text-gray-500" @click.stop>
              <summary class="cursor-pointer hover:text-gray-300 select-none">Ver URLs ({{ (c.matchedUrls || []).length }})</summary>
              <ul class="mt-1.5 space-y-0.5 font-mono max-h-32 overflow-y-auto pl-1">
                <li v-for="u in (c.matchedUrls || []).slice(0, 50)" :key="u" class="truncate">{{ u }}</li>
                <li v-if="(c.matchedUrls || []).length > 50" class="italic">… y {{ c.matchedUrls.length - 50 }} más</li>
              </ul>
            </details>
          </div>

          <!-- Actions (stop click propagation so card click doesn't toggle select) -->
          <div class="flex flex-col gap-1.5 flex-shrink-0" @click.stop>
            <button
              v-if="['discovered','reviewed'].includes(c.status)"
              @click="openPromote(c)"
              class="btn btn-primary text-xs px-3 py-1.5 whitespace-nowrap"
            >Promover</button>
            <button
              v-if="['discovered','reviewed'].includes(c.status)"
              @click="openSplit(c)"
              class="btn btn-secondary text-xs px-3 py-1.5 whitespace-nowrap"
            >Partir</button>
            <button
              v-if="['discovered','reviewed'].includes(c.status)"
              @click="discard(c)"
              class="text-xs text-red-400 hover:text-red-300 px-1 py-1 text-center"
            >Descartar</button>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Promote modal ── -->
    <div v-if="promoteCandidate" class="modal-overlay" @click.self="promoteCandidate = null">
      <div class="modal-card p-5 sm:p-6 w-full max-w-md mx-4">
        <h2 class="text-base font-bold mb-1">Promover a Resource</h2>
        <p class="text-xs font-mono text-gray-500 truncate mb-4">{{ promoteCandidate.pathTemplate }}</p>

        <label class="block text-xs text-gray-400 mb-1">Nombre</label>
        <input v-model="promoteForm.name" class="input w-full mb-3 text-sm" placeholder="nombre-unico" />

        <label class="block text-xs text-gray-400 mb-1">target_table</label>
        <input v-model="promoteForm.targetTable" class="input w-full mb-3 text-sm font-mono" placeholder="snake_case" />

        <label class="block text-xs text-gray-400 mb-1">Schedule (cron, opcional)</label>
        <input v-model="promoteForm.schedule" class="input w-full mb-3 text-sm" placeholder="0 3 * * 0" />

        <label class="flex items-center gap-2 text-xs text-gray-400 mb-5 cursor-pointer">
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

    <!-- ── Merge modal ── -->
    <div v-if="mergeTarget" class="modal-overlay" @click.self="mergeTarget = null">
      <div class="modal-card p-5 sm:p-6 w-full max-w-md mx-4">
        <h2 class="text-base font-bold mb-1">Fundir candidatos</h2>
        <p class="text-xs text-gray-500 mb-4">
          Los URLs de los candidatos seleccionados se acumularán en el candidato destino.
          Los demás pasarán a estado <span class="font-mono">merged</span>.
        </p>

        <label class="block text-xs text-gray-400 mb-2">Candidato destino (el que recibe los URLs)</label>
        <select v-model="mergeTargetId" class="input w-full text-sm mb-5">
          <option value="">— Selecciona destino —</option>
          <option v-for="id in [...selection]" :key="id" :value="id">
            {{ candidates.find(c => c.id === id)?.suggestedName || id }}
          </option>
        </select>

        <div class="flex justify-end gap-2">
          <button @click="mergeTarget = null" class="btn btn-secondary">Cancelar</button>
          <button @click="confirmMerge" :disabled="!mergeTargetId || merging" class="btn btn-primary">
            {{ merging ? 'Fundiendo…' : 'Fundir' }}
          </button>
        </div>
        <p v-if="mergeError" class="text-red-400 text-xs mt-2">{{ mergeError }}</p>
      </div>
    </div>

    <!-- ── Split modal ── -->
    <div v-if="splitCandidate" class="modal-overlay" @click.self="splitCandidate = null">
      <div class="modal-card p-5 sm:p-6 w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <h2 class="text-base font-bold mb-1">Partir candidato</h2>
        <p class="text-xs text-gray-500 mb-4">Distribuye las URLs en grupos. Cada grupo creará un nuevo candidato.</p>

        <div v-for="(group, gi) in splitGroups" :key="gi" class="mb-4 border border-gray-700 rounded-lg p-3">
          <div class="flex items-center gap-2 mb-2">
            <input v-model="group.name" class="input flex-1 text-xs" :placeholder="`Grupo ${gi + 1}`" />
            <button v-if="splitGroups.length > 2" @click="splitGroups.splice(gi, 1)" class="text-red-400 hover:text-red-300 text-xs px-1">✕</button>
          </div>
          <textarea
            v-model="group.urlsText"
            class="input w-full text-xs font-mono h-24 resize-none"
            placeholder="Una URL por línea"
          />
          <p class="text-xs text-gray-600 mt-1">{{ group.urlsText.split('\n').filter(u => u.trim()).length }} URLs</p>
        </div>

        <button @click="splitGroups.push({ name: '', urlsText: '' })" class="text-xs text-purple-400 hover:text-purple-300 mb-5">+ Añadir grupo</button>

        <div class="flex justify-end gap-2">
          <button @click="splitCandidate = null" class="btn btn-secondary">Cancelar</button>
          <button @click="confirmSplit" :disabled="splitting" class="btn btn-primary">
            {{ splitting ? 'Partiendo…' : 'Partir' }}
          </button>
        </div>
        <p v-if="splitError" class="text-red-400 text-xs mt-2">{{ splitError }}</p>
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
  mergeCandidates,
  splitCandidate as gqlSplitCandidate,
} from '../api/graphql'

// ── State ──────────────────────────────────────────────────────────────────
const loadingResources  = ref(true)
const allResources      = ref([])
const selectedResourceId = ref('')
const phase             = ref('idle')   // idle | running | error
const logText           = ref('')
const errorMsg          = ref('')
const candidates        = ref([])
const filterStatus      = ref('all')
const logEl             = ref(null)

// Selection (for merge)
const selection = ref(new Set())

// Promote
const promoteCandidate = ref(null)
const promoteForm      = ref({ name: '', targetTable: '', schedule: '', enableLoad: false })
const promoting        = ref(false)
const promoteError     = ref('')

// Merge
const mergeTarget   = ref(null)   // truthy when modal open
const mergeTargetId = ref('')
const merging       = ref(false)
const mergeError    = ref('')

// Split
const splitCandidate = ref(null)
const splitGroups    = ref([{ name: '', urlsText: '' }, { name: '', urlsText: '' }])
const splitting      = ref(false)
const splitError     = ref('')

let sseSource  = null
let pollTimer  = null

const statuses = ['all', 'discovered', 'reviewed', 'promoted', 'discarded', 'merged', 'split']

// ── Computed ───────────────────────────────────────────────────────────────
const crawlerResources = computed(() =>
  allResources.value.filter(r =>
    r.fetcher && !r.autoGenerated &&
    (r.fetcher.code === 'Web Tree' || r.fetcher.classPath?.toLowerCase().includes('web_tree_fetcher'))
  )
)

const filteredCandidates = computed(() =>
  filterStatus.value === 'all'
    ? candidates.value
    : candidates.value.filter(c => c.status === filterStatus.value)
)

// ── Helpers ────────────────────────────────────────────────────────────────
function statusBadge(status) {
  const map = {
    discovered: 'bg-blue-900 text-blue-300',
    reviewed:   'bg-yellow-900 text-yellow-300',
    promoted:   'bg-green-900 text-green-300',
    discarded:  'bg-gray-700 text-gray-400',
    merged:     'bg-purple-900 text-purple-300',
    split:      'bg-orange-900 text-orange-300',
  }
  return map[status] || 'bg-gray-700 text-gray-300'
}

function statusActiveClass(s) {
  const map = {
    all:        'border-gray-400 text-gray-200',
    discovered: 'border-blue-500 text-blue-300 bg-blue-900/30',
    reviewed:   'border-yellow-500 text-yellow-300 bg-yellow-900/30',
    promoted:   'border-green-500 text-green-300 bg-green-900/30',
    discarded:  'border-gray-500 text-gray-400 bg-gray-700/50',
    merged:     'border-purple-500 text-purple-300 bg-purple-900/30',
    split:      'border-orange-500 text-orange-300 bg-orange-900/30',
  }
  return map[s] || 'border-gray-400 text-gray-200'
}

function nameToTable(name) {
  return (name || '').toLowerCase().replace(/[^a-z0-9\s_]/g, '').trim().replace(/\s+/g, '_').substring(0, 60)
}

function appendLog(line) {
  logText.value += (logText.value ? '\n' : '') + line
  nextTick(() => { if (logEl.value) logEl.value.scrollTop = logEl.value.scrollHeight })
}

// ── Selection ──────────────────────────────────────────────────────────────
function toggleSelect(c) {
  if (!['discovered', 'reviewed'].includes(c.status)) return
  const s = new Set(selection.value)
  s.has(c.id) ? s.delete(c.id) : s.add(c.id)
  selection.value = s
}

// ── Data loading ───────────────────────────────────────────────────────────
watch(selectedResourceId, async (id) => {
  selection.value = new Set()
  candidates.value = id ? (await fetchResourceCandidates({ crawlerResourceId: id }))?.resourceCandidates || [] : []
})

async function loadCandidates() {
  if (!selectedResourceId.value) return
  candidates.value = (await fetchResourceCandidates({ crawlerResourceId: selectedResourceId.value }))?.resourceCandidates || []
}

// ── Discover ───────────────────────────────────────────────────────────────
async function launchDiscover() {
  if (!selectedResourceId.value) return
  phase.value   = 'running'
  logText.value = ''
  errorMsg.value = ''
  selection.value = new Set()

  const res = await executeResource(selectedResourceId.value, {})
  if (!res?.executeResource?.success) {
    phase.value    = 'error'
    errorMsg.value = res?.executeResource?.message || 'Error al lanzar discovery'
    return
  }
  const execId = res.executeResource.executionId
  if (execId) startSSE(execId)
  startPolling()
}

function startSSE(execId) {
  if (sseSource) sseSource.close()
  sseSource = new EventSource(`/api/executions/${execId}/logs?follow=true`)
  sseSource.onmessage = (e) => { if (e.data) appendLog(e.data) }
  sseSource.addEventListener('done', () => { sseSource?.close(); sseSource = null })
  sseSource.onerror = () => { sseSource?.close(); sseSource = null }
}

function startPolling() {
  let polls = 0
  pollTimer = setInterval(async () => {
    polls++
    if (polls > 300) {
      clearInterval(pollTimer)
      phase.value    = 'error'
      errorMsg.value = 'Discovery timed out — revisa los procesos'
      return
    }
    const before = candidates.value.length
    await loadCandidates()
    if (candidates.value.length > before) {
      clearInterval(pollTimer)
      phase.value = 'idle'
      appendLog(`\nDISCOVER COMPLETADO — ${candidates.value.length} candidato(s)`)
    }
  }, 2000)
}

function reset() {
  clearInterval(pollTimer)
  sseSource?.close(); sseSource = null
  phase.value = 'idle'
  logText.value = ''
  errorMsg.value = ''
}

// ── Promote ────────────────────────────────────────────────────────────────
function openPromote(c) {
  promoteCandidate.value = c
  promoteForm.value = { name: c.suggestedName || '', targetTable: nameToTable(c.suggestedName || ''), schedule: '', enableLoad: false }
  promoteError.value = ''
}

async function confirmPromote() {
  if (!promoteCandidate.value) return
  if (!promoteForm.value.name || !promoteForm.value.targetTable) { promoteError.value = 'name y target_table son obligatorios'; return }
  promoting.value = true; promoteError.value = ''
  try {
    await gqlPromoteCandidate(promoteCandidate.value.id, {
      name: promoteForm.value.name, targetTable: promoteForm.value.targetTable,
      schedule: promoteForm.value.schedule || null, enableLoad: promoteForm.value.enableLoad, loadMode: 'upsert',
    })
    promoteCandidate.value = null
    await loadCandidates()
  } catch (e) { promoteError.value = e?.message || 'Error al promover' }
  finally { promoting.value = false }
}

// ── Discard ────────────────────────────────────────────────────────────────
async function discard(c) {
  if (!confirm(`¿Descartar "${c.suggestedName || c.pathTemplate}"?`)) return
  await discardCandidate(c.id)
  await loadCandidates()
}

// ── Merge ──────────────────────────────────────────────────────────────────
function openMerge() {
  mergeTarget.value   = true
  mergeTargetId.value = ''
  mergeError.value    = ''
}

async function confirmMerge() {
  if (!mergeTargetId.value) return
  merging.value = true; mergeError.value = ''
  try {
    const sourceIds = [...selection.value].filter(id => id !== mergeTargetId.value)
    await mergeCandidates(sourceIds, mergeTargetId.value)
    mergeTarget.value = null
    selection.value = new Set()
    await loadCandidates()
  } catch (e) { mergeError.value = e?.message || 'Error al fundir' }
  finally { merging.value = false }
}

// ── Split ──────────────────────────────────────────────────────────────────
function openSplit(c) {
  splitCandidate.value = c
  // Pre-distribute URLs evenly across 2 groups
  const urls = c.matchedUrls || []
  const half = Math.ceil(urls.length / 2)
  splitGroups.value = [
    { name: `${c.suggestedName || 'Grupo'} A`, urlsText: urls.slice(0, half).join('\n') },
    { name: `${c.suggestedName || 'Grupo'} B`, urlsText: urls.slice(half).join('\n') },
  ]
  splitError.value = ''
}

async function confirmSplit() {
  if (!splitCandidate.value) return
  splitting.value = true; splitError.value = ''
  try {
    const groups = splitGroups.value
      .map(g => ({ name: g.name, urls: g.urlsText.split('\n').map(u => u.trim()).filter(Boolean) }))
      .filter(g => g.urls.length)
    if (groups.length < 2) { splitError.value = 'Se necesitan al menos 2 grupos con URLs'; return }
    await gqlSplitCandidate(splitCandidate.value.id, groups)
    splitCandidate.value = null
    await loadCandidates()
  } catch (e) { splitError.value = e?.message || 'Error al partir' }
  finally { splitting.value = false }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────
onMounted(async () => {
  try {
    const res = await fetchResources()
    allResources.value = res?.resources || []
  } catch (e) { console.error('Discovering: error loading resources', e) }
  finally { loadingResources.value = false }
})

onUnmounted(() => { clearInterval(pollTimer); sseSource?.close() })
</script>
