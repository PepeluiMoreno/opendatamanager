<template>
  <div class="p-8 max-w-4xl">
    <h1 class="text-3xl font-bold mb-6">Discovering</h1>

    <!-- Resource selector -->
    <div class="card p-5 mb-6">
      <label class="block text-sm text-gray-400 mb-2">Recurso padre</label>
      <div v-if="loadingResources" class="text-sm text-gray-500">Cargando recursos…</div>
      <select v-else v-model="selectedResourceId" class="input w-full">
        <option value="">— Selecciona un recurso —</option>
        <option v-for="r in discoverableResources" :key="r.id" :value="r.id">
          {{ r.name }}
        </option>
      </select>
      <button
        @click="launchDiscover"
        :disabled="!selectedResourceId || phase !== 'idle'"
        class="btn btn-primary mt-4"
        :class="(!selectedResourceId || phase !== 'idle') ? 'opacity-50 cursor-not-allowed' : ''"
      >
        {{ phase === 'running' ? 'Descubriendo…' : 'Lanzar Discovery' }}
      </button>
    </div>

    <!-- Log panel -->
    <div v-if="phase !== 'idle'" class="card p-5 mb-6">
      <div class="flex items-center justify-between mb-3">
        <span class="text-sm font-medium text-gray-300">Log</span>
        <span
          class="text-xs px-2 py-0.5 rounded-full font-medium"
          :class="{
            'bg-blue-900 text-blue-300': phase === 'running',
            'bg-green-900 text-green-300': phase === 'done',
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

    <!-- Sections -->
    <div v-if="phase === 'done' && sections.length">
      <div class="flex items-center justify-between mb-3">
        <p class="text-sm text-gray-400">
          {{ sections.length }} sección{{ sections.length !== 1 ? 'es' : '' }} descubiertas.
        </p>
        <div class="flex gap-3">
          <button @click="selectAll(true)" class="text-xs text-purple-400 hover:text-purple-300">Seleccionar todo</button>
          <button @click="selectAll(false)" class="text-xs text-gray-400 hover:text-gray-300">Deseleccionar</button>
        </div>
      </div>

      <div class="space-y-3 mb-6">
        <div
          v-for="(sec, i) in sections" :key="i"
          class="border rounded-lg p-4 transition-colors"
          :class="sec.selected ? 'border-purple-600 bg-gray-750' : 'border-gray-700 bg-gray-800'"
        >
          <div class="flex items-start gap-3">
            <input type="checkbox" v-model="sec.selected" class="accent-purple-500 mt-1 flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <input v-model="sec.name" class="input text-sm w-full mb-2 font-medium" placeholder="Nombre del recurso…" />
              <input v-model="sec.targetTable" class="input text-xs font-mono w-full mb-2 text-gray-400" placeholder="target_table (snake_case)" />
              <div class="flex flex-wrap gap-3 text-xs text-gray-500">
                <span>{{ sec.page_count }} pág{{ sec.page_count !== 1 ? 's' : '' }}</span>
                <span>{{ sec.total_file_count }} fichero{{ sec.total_file_count !== 1 ? 's' : '' }}</span>
                <span v-for="ext in sec.extensions" :key="ext"
                      class="px-1.5 py-0.5 rounded bg-gray-700 text-gray-300 font-mono uppercase">{{ ext }}</span>
              </div>
              <p class="text-xs font-mono text-gray-600 mt-1 truncate" :title="sec.url_pattern">{{ sec.url_pattern }}</p>
            </div>
          </div>
        </div>
      </div>

      <div class="flex items-center gap-4">
        <button
          @click="createResources"
          :disabled="creating || selectedCount === 0"
          class="btn btn-primary"
          :class="(creating || selectedCount === 0) ? 'opacity-50 cursor-not-allowed' : ''"
        >
          {{ creating ? 'Creando…' : `Crear ${selectedCount} recurso${selectedCount !== 1 ? 's' : ''}` }}
        </button>
        <button @click="reset" class="btn btn-secondary">Nueva búsqueda</button>
        <span v-if="createSuccess" class="text-sm text-green-400">{{ createSuccess }}</span>
      </div>
    </div>

    <div v-if="phase === 'done' && sections.length === 0" class="text-gray-500 text-sm">
      El discover completó pero no encontró secciones.
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { fetchResources, executeResource, fetchDiscoverArtifact, createChildResources } from '../api/graphql'

const loadingResources = ref(true)
const allResources = ref([])
const selectedResourceId = ref('')
const phase = ref('idle')   // idle | running | done | error
const logText = ref('')
const errorMsg = ref('')
const sections = ref([])
const creating = ref(false)
const createSuccess = ref('')
const logEl = ref(null)
let sseSource = null
let pollTimer = null

const discoverableResources = computed(() =>
  allResources.value.filter(r =>
    !r.autoGenerated &&
    !r.deletedAt &&
    (r.fetcher?.classPath?.toLowerCase().includes('document_portal') ||
     r.fetcher?.code?.toLowerCase().includes('portal'))
  )
)

const selectedCount = computed(() => sections.value.filter(s => s.selected).length)

function selectAll(val) {
  sections.value.forEach(s => { s.selected = val })
}

function nameToTable(name) {
  return name.toLowerCase()
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

async function launchDiscover() {
  if (!selectedResourceId.value) return
  phase.value = 'running'
  logText.value = ''
  errorMsg.value = ''
  sections.value = []
  createSuccess.value = ''

  const res = await executeResource(selectedResourceId.value, { _discover_mode: true })
  if (!res?.executeResource?.success) {
    phase.value = 'error'
    errorMsg.value = res?.executeResource?.message || 'Error al lanzar discovery'
    return
  }

  const execId = res.executeResource.executionId
  if (execId) {
    startSSE(execId)
  }
  startPolling()
}

function startSSE(execId) {
  if (sseSource) sseSource.close()
  sseSource = new EventSource(`/api/executions/${execId}/logs?since=0`)
  sseSource.onmessage = (e) => {
    appendLog(e.data)
  }
  sseSource.addEventListener('done', () => {
    sseSource?.close(); sseSource = null
  })
  sseSource.onerror = () => { sseSource?.close(); sseSource = null }
}

function startPolling() {
  let polls = 0
  pollTimer = setInterval(async () => {
    polls++
    if (polls > 300) {  // 10 min
      clearInterval(pollTimer)
      phase.value = 'error'
      errorMsg.value = 'Discovery timed out — revisa los procesos'
      return
    }
    const r = await fetchDiscoverArtifact(selectedResourceId.value)
    if (r?.discoverArtifact) {
      clearInterval(pollTimer)
      loadSections(r.discoverArtifact)
    }
  }, 2000)
}

function loadSections(json) {
  const raw = JSON.parse(json)
  const resource = allResources.value.find(r => r.id === selectedResourceId.value)
  const baseName = resource?.name || ''
  sections.value = raw.map(s => ({
    ...s,
    selected: true,
    name: baseName + ' — ' + s.suggested_name,
    targetTable: nameToTable(s.suggested_name),
  }))
  phase.value = 'done'
  appendLog(`\nDISCOVER COMPLETADO — ${sections.value.length} secciones`)
}

async function createResources() {
  creating.value = true
  createSuccess.value = ''
  try {
    const approved = sections.value.filter(s => s.selected)
    const input = approved.map(s => ({
      urlPattern: s.url_pattern,
      name: s.name,
      targetTable: s.targetTable,
      pageIncludePatterns: JSON.stringify(s.suggested_page_include_patterns || []),
      extensions: s.extensions,
    }))
    const res = await createChildResources(selectedResourceId.value, input)
    const created = res?.createChildResources || []
    createSuccess.value = `${created.length} recurso${created.length !== 1 ? 's' : ''} creado${created.length !== 1 ? 's' : ''}`
    sections.value.forEach(s => { s.selected = false })
  } finally {
    creating.value = false
  }
}

function reset() {
  clearInterval(pollTimer)
  sseSource?.close(); sseSource = null
  phase.value = 'idle'
  logText.value = ''
  errorMsg.value = ''
  sections.value = []
  createSuccess.value = ''
}

onMounted(async () => {
  try {
    const res = await getResources()
    allResources.value = res?.resources || []
  } finally {
    loadingResources.value = false
  }
})

onUnmounted(() => {
  clearInterval(pollTimer)
  sseSource?.close()
})
</script>
