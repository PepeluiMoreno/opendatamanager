<template>
  <div class="flex h-full bg-gray-900 overflow-hidden" ref="containerRef">

    <!-- ── Sidebar: lista de datasets ── -->
    <div class="flex-shrink-0 bg-gray-800 border-r border-gray-700 flex flex-col overflow-hidden"
         :style="{ width: sidebarWidth + 'px' }">
      <div class="px-3 py-2.5 border-b border-gray-700 flex-shrink-0">
        <h2 class="text-sm font-semibold text-white">Data Explorer</h2>
        <p class="text-xs text-gray-500 mt-0.5">API GraphQL dinámica</p>
      </div>

      <div v-if="loading" class="p-3 text-gray-400 text-xs">Cargando datasets...</div>
      <div v-else-if="error" class="p-3 text-red-400 text-xs">{{ error }}</div>
      <div v-else-if="datasets.length === 0" class="p-3 text-gray-500 text-xs">
        No hay datasets disponibles.<br>Ejecuta algún resource primero.
      </div>

      <div v-else class="flex-1 overflow-y-auto p-1.5 space-y-0.5">
        <button
          v-for="ds in datasets"
          :key="ds.queryName"
          @click="selectDataset(ds)"
          class="w-full text-left px-2.5 py-2 rounded-md transition-colors"
          :class="selected?.queryName === ds.queryName
            ? 'bg-blue-600 text-white'
            : 'text-gray-300 hover:bg-gray-700'"
        >
          <div class="font-medium text-xs truncate">{{ ds.resourceName }}</div>
          <div class="flex items-center gap-1 mt-0.5">
            <span class="text-xs opacity-60 font-mono truncate" style="font-size:0.65rem">{{ ds.queryName }}</span>
            <span class="opacity-50 ml-auto flex-shrink-0" style="font-size:0.65rem">
              {{ ds.recordCount != null ? ds.recordCount.toLocaleString() : '—' }}
            </span>
          </div>
        </button>
      </div>

      <div v-if="selected" class="border-t border-gray-700 p-3 flex-shrink-0">
        <button @click="openInNewTab"
          class="w-full text-xs text-blue-400 hover:text-blue-300 text-center py-1">
          ↗ Abrir en pestaña nueva
        </button>
      </div>
    </div>

    <!-- ── Divisor arrastrable ── -->
    <div
      class="w-1 flex-shrink-0 cursor-col-resize bg-gray-700 hover:bg-blue-500 transition-colors relative group"
      :class="{ 'bg-blue-500': dragging }"
      @mousedown.prevent="startDrag"
    >
      <!-- Indicador visual central -->
      <div class="absolute inset-y-0 -left-1 -right-1 group-hover:bg-blue-500/10"
           :class="{ 'bg-blue-500/10': dragging }" />
    </div>

    <!-- ── Panel principal: GraphiQL embebido ── -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">

      <div v-if="selected" class="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center gap-3 flex-shrink-0">
        <span class="text-xs text-gray-400 flex-shrink-0">Query:</span>
        <code class="text-xs text-green-400 font-mono truncate flex-1 min-w-0">
          {{ exampleQueryOneliner }}
        </code>
        <button
          @click="copyQuery"
          class="text-xs text-gray-400 hover:text-white px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 flex-shrink-0"
        >{{ copied ? '✓ Copiado' : 'Copiar' }}</button>
      </div>

      <iframe
        v-if="iframeSrc"
        :key="iframeSrc"
        :src="iframeSrc"
        class="flex-1 border-0 w-full min-h-0"
        title="GraphiQL Explorer"
      />

      <div v-else class="flex-1 flex flex-col items-center justify-center text-gray-600 gap-4">
        <svg class="w-16 h-16 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"
            d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z"/>
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4"/>
        </svg>
        <p class="text-lg">Selecciona un dataset para explorar sus datos</p>
        <p class="text-sm">O abre el explorer libre
          <a href="/graphql/data" target="_blank" class="text-blue-400 hover:underline">en nueva pestaña</a>
        </p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const datasets = ref([])
const selected = ref(null)
const loading = ref(true)
const error = ref(null)
const copied = ref(false)
const iframeSrc = ref('')

// ── Redimensionado del sidebar ───────────────────────────────────────────────

const containerRef = ref(null)
const sidebarWidth = ref(288)   // 288px = w-72 inicial
const dragging = ref(false)
const MIN_SIDEBAR = 180
const MAX_SIDEBAR = 600

let dragStartX = 0
let dragStartWidth = 0

function startDrag(e) {
  dragging.value = true
  dragStartX = e.clientX
  dragStartWidth = sidebarWidth.value
  document.body.style.cursor = 'col-resize'
  document.body.style.userSelect = 'none'
}

function onMouseMove(e) {
  if (!dragging.value) return
  const delta = e.clientX - dragStartX
  sidebarWidth.value = Math.min(MAX_SIDEBAR, Math.max(MIN_SIDEBAR, dragStartWidth + delta))
}

function onMouseUp() {
  if (!dragging.value) return
  dragging.value = false
  document.body.style.cursor = ''
  document.body.style.userSelect = ''
}

onMounted(() => {
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  loadRegistry()
})

onUnmounted(() => {
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
})

// ── Fetch del registro ──────────────────────────────────────────────────────

async function loadRegistry() {
  loading.value = true
  error.value = null
  try {
    const resp = await fetch('/api/graphql-data/registry')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    datasets.value = await resp.json()
    if (datasets.value.length > 0) selectDataset(datasets.value[0])
  } catch (e) {
    error.value = `No se pudo cargar el registro: ${e.message}`
  } finally {
    loading.value = false
  }
}

// ── Generación de query ejemplo ─────────────────────────────────────────────

function buildExampleQuery(ds) {
  const fields = ds.fields.slice(0, 12).join('\n      ')
  return `{\n  ${ds.queryName}(limit: 20) {\n    total\n    items {\n      ${fields}\n    }\n  }\n}`
}

const exampleQueryOneliner = computed(() => {
  if (!selected.value) return ''
  const fields = selected.value.fields.slice(0, 5).join(' ')
  return `{ ${selected.value.queryName}(limit:20) { total items { ${fields}${selected.value.fields.length > 5 ? ' ...' : ''} } } }`
})

// ── Selección y navegación ──────────────────────────────────────────────────

function selectDataset(ds) {
  selected.value = ds
  const query = encodeURIComponent(buildExampleQuery(ds))
  iframeSrc.value = `/graphql/data?query=${query}&_t=${Date.now()}`
}

function openInNewTab() {
  if (!selected.value) return
  window.open(`/graphql/data?query=${encodeURIComponent(buildExampleQuery(selected.value))}`, '_blank')
}

async function copyQuery() {
  if (!selected.value) return
  await navigator.clipboard.writeText(buildExampleQuery(selected.value))
  copied.value = true
  setTimeout(() => (copied.value = false), 2000)
}
</script>
