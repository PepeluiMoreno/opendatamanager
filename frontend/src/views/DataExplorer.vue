<template>
  <div class="flex flex-col h-full bg-gray-900 overflow-hidden">

    <!-- ── Toolbar ── -->
    <div class="flex-shrink-0 bg-gray-800 border-b border-gray-700 px-5 py-3 space-y-3">
      <div class="flex items-center justify-between gap-4">
        <div>
          <h2 class="text-sm font-semibold text-white">Data Explorer</h2>
          <p class="text-xs text-gray-500 mt-0.5">{{ summary }}</p>
        </div>
        <button @click="loadTree" class="text-xs text-gray-400 hover:text-white px-2.5 py-1.5 rounded bg-gray-700 hover:bg-gray-600 flex items-center gap-1.5">
          <svg class="w-3 h-3" :class="{ 'animate-spin': loading }" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
          </svg>
          Actualizar
        </button>
      </div>

      <div class="flex items-center gap-3 flex-wrap">
        <div class="relative flex-1 min-w-48">
          <svg class="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-4.35-4.35M17 11A6 6 0 115 11a6 6 0 0112 0z"/>
          </svg>
          <input v-model="search" type="text" placeholder="Buscar recurso…"
            class="w-full bg-gray-700 border border-gray-600 rounded-md pl-8 pr-8 py-1.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"/>
          <button v-if="search" @click="search = ''" class="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300 text-xs leading-none">✕</button>
        </div>

        <div class="flex items-center gap-2">
          <button @click="expandAll" class="text-xs text-gray-400 hover:text-white px-2.5 py-1 rounded bg-gray-700 hover:bg-gray-600">Expandir todo</button>
          <button @click="collapseAll" class="text-xs text-gray-400 hover:text-white px-2.5 py-1 rounded bg-gray-700 hover:bg-gray-600">Colapsar todo</button>
        </div>

        <div class="flex items-center gap-2">
          <span class="text-xs text-gray-500">Mostrar:</span>
          <button @click="filterMode = filterMode === 'empty' ? '' : 'empty'"
            class="text-xs px-2.5 py-1 rounded-full border transition-colors"
            :class="filterMode === 'empty' ? 'bg-amber-600/30 border-amber-500 text-amber-300' : 'border-gray-600 text-gray-400 hover:border-gray-400'">
            Sin datos
          </button>
          <button @click="filterMode = filterMode === 'data' ? '' : 'data'"
            class="text-xs px-2.5 py-1 rounded-full border transition-colors"
            :class="filterMode === 'data' ? 'bg-green-600/30 border-green-500 text-green-300' : 'border-gray-600 text-gray-400 hover:border-gray-400'">
            Con datos
          </button>
        </div>
      </div>
    </div>

    <!-- ── Tree table ── -->
    <div class="flex-1 overflow-auto">
      <div v-if="loading" class="flex items-center justify-center h-32 text-gray-400 text-sm">Cargando…</div>
      <div v-else-if="error" class="flex items-center justify-center h-32 text-red-400 text-sm">{{ error }}</div>
      <div v-else-if="filteredTree.length === 0" class="flex items-center justify-center h-32 text-gray-500 text-sm">
        {{ tree.length === 0 ? 'No hay datasets. Ejecuta algún resource primero.' : 'Sin resultados.' }}
      </div>

      <table v-else class="w-full text-xs">
        <thead class="sticky top-0 bg-gray-800 z-10">
          <tr class="border-b border-gray-700">
            <th class="w-8 px-4 py-2.5"></th>
            <th class="text-left px-3 py-2.5 text-gray-400 font-medium">Recurso / Versión</th>
            <th class="text-right px-4 py-2.5 text-gray-400 font-medium">Registros</th>
            <th class="text-right px-4 py-2.5 text-gray-400 font-medium">Campos</th>
            <th class="text-left px-4 py-2.5 text-gray-400 font-medium">Generado</th>
            <th class="w-24 px-4 py-2.5 text-gray-400 font-medium text-center">Acciones</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="res in filteredTree" :key="res.nodeId">

            <!-- Resource row -->
            <tr class="border-b border-gray-700/50 hover:bg-gray-800/40 cursor-pointer transition-colors"
                :class="expandedResources.has(res.nodeId) ? 'bg-gray-800/30' : ''"
                @click="toggleResource(res.nodeId)">
              <td class="px-4 py-3 text-center">
                <svg class="w-3.5 h-3.5 text-gray-500 inline transition-transform duration-150"
                  :class="expandedResources.has(res.resourceId) ? 'rotate-90' : ''"
                  fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                </svg>
              </td>
              <td class="px-3 py-3">
                <div class="flex items-center gap-2">
                  <svg class="w-3.5 h-3.5 flex-shrink-0" :class="res.label ? 'text-purple-400' : 'text-blue-400'" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z"/>
                  </svg>
                  <span class="font-medium text-white">{{ res.displayName }}</span>
                  <span class="text-xs text-gray-500 bg-gray-700 px-1.5 py-0.5 rounded-full">
                    {{ res.versions.length }} {{ res.versions.length === 1 ? 'versión' : 'versiones' }}
                  </span>
                </div>
              </td>
              <td class="px-4 py-3 text-right">
                <span class="font-mono font-medium" :class="res.versions[0]?.recordCount ? 'text-green-400' : 'text-gray-600'">
                  {{ res.versions[0]?.recordCount != null ? res.versions[0].recordCount.toLocaleString() : '—' }}
                </span>
              </td>
              <td class="px-4 py-3 text-right">
                <span class="text-gray-400 font-mono">{{ res.versions[0]?.fields?.length ?? '—' }}</span>
              </td>
              <td class="px-4 py-3 text-gray-400 whitespace-nowrap">
                {{ res.versions[0]?.createdAt ? formatDate(res.versions[0].createdAt) : '—' }}
              </td>
              <!-- Resource-level params button -->
              <td class="px-4 py-3 text-center" @click.stop>
                <button @click="openParams(res, null)"
                  title="Ver parámetros del recurso"
                  class="p-1.5 rounded text-gray-500 hover:text-purple-300 hover:bg-purple-900/30 transition-colors">
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  </svg>
                </button>
              </td>
            </tr>

            <!-- Version rows -->
            <template v-if="expandedResources.has(res.nodeId)">
              <tr v-for="ver in res.versions" :key="ver.datasetId"
                class="border-b border-gray-700/30 hover:bg-gray-800/20 transition-colors">
                <td class="px-4 py-2.5">
                  <div class="flex items-center justify-center">
                    <div class="w-px h-4 bg-gray-600 mr-1"></div>
                    <svg v-if="ver.fields?.length" class="w-3 h-3 cursor-pointer transition-colors"
                      :class="expandedDataset === ver.datasetId ? 'text-blue-400' : 'text-gray-600 hover:text-gray-400'"
                      fill="none" stroke="currentColor" viewBox="0 0 24 24"
                      @click.stop="toggleDataset(ver.datasetId)">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                    <div v-else class="w-3"></div>
                  </div>
                </td>
                <td class="pl-6 pr-3 py-2.5">
                  <div class="flex items-center gap-2">
                    <span class="font-mono text-gray-400">v{{ ver.version }}</span>
                    <span v-if="ver.isLatest" class="text-xs bg-blue-700/50 text-blue-300 border border-blue-600/40 px-1.5 py-0.5 rounded">latest</span>
                  </div>
                </td>
                <td class="px-4 py-2.5 text-right">
                  <span class="font-mono" :class="ver.recordCount ? 'text-green-400' : 'text-gray-600'">
                    {{ ver.recordCount != null ? ver.recordCount.toLocaleString() : '—' }}
                  </span>
                </td>
                <td class="px-4 py-2.5 text-right">
                  <span class="text-gray-500 font-mono">{{ ver.fields?.length ?? '—' }}</span>
                </td>
                <td class="px-4 py-2.5 text-gray-500 whitespace-nowrap">
                  {{ ver.createdAt ? formatDate(ver.createdAt) : '—' }}
                </td>
                <td class="px-4 py-2.5 text-center" @click.stop>
                  <div class="flex items-center justify-center gap-1">
                    <button @click="openParams(res, ver)"
                      title="Ver parámetros"
                      class="p-1.5 rounded text-gray-500 hover:text-purple-300 hover:bg-purple-900/30 transition-colors">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      </svg>
                    </button>
                    <button v-if="ver.queryName" @click="openSandbox(ver)"
                      title="Abrir en Sandbox GraphQL"
                      class="p-1.5 rounded text-gray-400 hover:text-blue-300 hover:bg-blue-900/30 transition-colors">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"/>
                      </svg>
                    </button>
                    <button @click="confirmDelete(ver, res.resourceName)"
                      title="Eliminar dataset"
                      class="p-1.5 rounded text-gray-600 hover:text-red-400 hover:bg-red-900/30 transition-colors">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>

              <!-- Fields expand row -->
              <tr v-if="expandedDataset && res.versions.some(v => v.datasetId === expandedDataset) && expandedResources.has(res.nodeId)"
                  class="bg-gray-800/40 border-b border-gray-700/30">
                <td colspan="6" class="pl-10 pr-5 py-3">
                  <div v-for="ver in res.versions.filter(v => v.datasetId === expandedDataset)" :key="ver.datasetId" class="space-y-2">
                    <p class="text-xs text-gray-500 uppercase tracking-wide font-medium">Campos — v{{ ver.version }}</p>
                    <div class="flex flex-wrap gap-1.5">
                      <span v-for="field in ver.fields" :key="field"
                        class="bg-gray-700 text-gray-300 rounded px-2 py-0.5 font-mono text-xs">{{ field }}</span>
                    </div>
                    <div v-if="ver.queryName" class="flex items-center gap-2 pt-1">
                      <button @click="copyQuery(ver)"
                        class="text-xs text-gray-400 hover:text-white px-2.5 py-1 rounded bg-gray-700 hover:bg-gray-600">
                        {{ copiedId === ver.datasetId ? '✓ Copiado' : 'Copiar query' }}
                      </button>
                      <code class="text-xs text-green-400 font-mono opacity-70 truncate">
                        { {{ ver.queryName }}(limit:20) { total items { {{ ver.fields.slice(0,4).join(' ') }}{{ ver.fields.length > 4 ? ' …' : '' }} } } }
                      </code>
                    </div>
                  </div>
                </td>
              </tr>
            </template>

          </template>
        </tbody>
      </table>
    </div>

    <!-- ── Params modal ── -->
    <div v-if="paramsModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60" @click.self="paramsModal = null">
      <div class="bg-gray-800 border border-gray-600 rounded-xl shadow-2xl w-[820px] max-w-[92vw] max-h-[85vh] flex flex-col">
        <!-- Header -->
        <div class="flex items-start justify-between px-5 py-4 border-b border-gray-700 flex-shrink-0">
          <div>
            <h3 class="text-sm font-semibold text-white">{{ paramsModal.resourceName }}</h3>
            <p v-if="paramsModal.version" class="text-xs text-gray-400 mt-0.5">
              Dataset v{{ paramsModal.version }}
              <span v-if="paramsModal.isLatest" class="ml-1.5 bg-blue-700/50 text-blue-300 border border-blue-600/40 px-1.5 py-0.5 rounded">latest</span>
            </p>
            <p v-else class="text-xs text-gray-400 mt-0.5">Parámetros de configuración del recurso</p>
          </div>
          <button @click="paramsModal = null" class="text-gray-500 hover:text-gray-300 p-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
            </svg>
          </button>
        </div>

        <div class="overflow-y-auto flex-1 px-5 py-4 space-y-5">

          <!-- Execution params (only for version rows) -->
          <div v-if="paramsModal.version">
            <p class="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">
              Parámetros de ejecución
              <span class="normal-case text-gray-600 ml-1">(aplicados en esta ejecución concreta)</span>
            </p>
            <div v-if="paramsModal.executionParams && Object.keys(paramsModal.executionParams).length" class="space-y-1.5">
              <div v-for="(v, k) in paramsModal.executionParams" :key="k"
                class="flex items-start gap-3 bg-blue-900/20 border border-blue-700/30 rounded-lg px-3 py-2">
                <span class="font-mono text-blue-300 text-xs min-w-32 flex-shrink-0">{{ k }}</span>
                <span class="text-white text-xs break-all font-medium">{{ v }}</span>
              </div>
            </div>
            <p v-else class="text-xs text-gray-600 italic">Sin parámetros de ejecución — se usaron los valores estáticos del recurso.</p>
          </div>

          <!-- Static resource params -->
          <div>
            <p class="text-xs text-gray-500 uppercase tracking-wide font-medium mb-2">
              Parámetros del recurso
              <span class="normal-case text-gray-600 ml-1">(configuración estática)</span>
            </p>
            <div v-if="paramsModal.resourceParams && Object.keys(paramsModal.resourceParams).length" class="space-y-1.5">
              <div v-for="k in Object.keys(paramsModal.resourceParams).sort()" :key="k"
                class="flex items-start gap-3 bg-gray-700/50 rounded-lg px-3 py-2">
                <span class="font-mono text-gray-400 text-xs min-w-32 flex-shrink-0">{{ k }}</span>
                <span class="text-gray-200 text-xs break-all">{{ paramsModal.resourceParams[k] }}</span>
              </div>
            </div>
            <p v-else class="text-xs text-gray-600 italic">Sin parámetros configurados.</p>
          </div>

        </div>
      </div>
    </div>

    <!-- ── Delete confirm ── -->
    <div v-if="toDelete" class="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div class="bg-gray-800 border border-gray-600 rounded-xl p-6 w-96 shadow-2xl">
        <h3 class="text-sm font-semibold text-white mb-2">Eliminar dataset</h3>
        <p class="text-sm text-gray-300 mb-1 leading-relaxed">
          ¿Eliminar <span class="text-white font-medium">{{ toDelete.resourceName }}</span>
          versión <span class="font-mono text-blue-300">v{{ toDelete.version }}</span>?
        </p>
        <p class="text-xs text-gray-500 mb-5">Se borrarán el registro en base de datos y el fichero JSONL. <span class="text-red-400">No se puede deshacer.</span></p>
        <div class="flex gap-2 justify-end">
          <button @click="toDelete = null" class="text-xs px-4 py-2 rounded-lg bg-gray-700 text-gray-300 hover:bg-gray-600">Cancelar</button>
          <button @click="doDelete" :disabled="deleting" class="text-xs px-4 py-2 rounded-lg bg-red-700 text-white hover:bg-red-600 disabled:opacity-50">
            {{ deleting ? 'Eliminando…' : 'Eliminar' }}
          </button>
        </div>
        <p v-if="deleteError" class="text-xs text-red-400 mt-3">{{ deleteError }}</p>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const tree = ref([])
const loading = ref(true)
const error = ref(null)
const search = ref('')
const filterMode = ref('')
const expandedResources = ref(new Set())
const expandedDataset = ref(null)
const copiedId = ref(null)
const paramsModal = ref(null)
const toDelete = ref(null)
const deleting = ref(false)
const deleteError = ref('')

async function loadTree() {
  loading.value = true
  error.value = null
  try {
    const resp = await fetch('/api/datasets/tree')
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    tree.value = await resp.json()
  } catch (e) {
    error.value = `No se pudo cargar: ${e.message}`
  } finally {
    loading.value = false
  }
}

onMounted(loadTree)

const filteredTree = computed(() => {
  let result = tree.value
  if (search.value.trim()) {
    const q = search.value.toLowerCase()
    result = result.filter(r => r.displayName.toLowerCase().includes(q))
  }
  if (filterMode.value === 'empty') result = result.filter(r => !r.versions[0]?.recordCount)
  else if (filterMode.value === 'data') result = result.filter(r => r.versions[0]?.recordCount > 0)
  return result
})

const summary = computed(() => {
  const resources = filteredTree.value.length
  const versions = filteredTree.value.reduce((n, r) => n + r.versions.length, 0)
  return `${resources} recursos · ${versions} datasets`
})

function toggleResource(id) {
  const s = new Set(expandedResources.value)
  s.has(id) ? s.delete(id) : s.add(id)
  expandedResources.value = s
}

function expandAll() {
  expandedResources.value = new Set(filteredTree.value.map(r => r.nodeId))
}

function collapseAll() {
  expandedResources.value = new Set()
  expandedDataset.value = null
}

function toggleDataset(id) {
  expandedDataset.value = expandedDataset.value === id ? null : id
}

function formatDate(iso) {
  const d = new Date(iso)
  return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric' })
    + ' ' + d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
}

function buildQuery(ver) {
  const fields = (ver.fields || []).slice(0, 12).join('\n      ')
  return `{\n  ${ver.queryName}(limit: 20) {\n    total\n    items {\n      ${fields}\n    }\n  }\n}`
}

function openSandbox(ver) {
  window.open(`/graphql/data?query=${encodeURIComponent(buildQuery(ver))}`, '_blank')
}

async function copyQuery(ver) {
  await navigator.clipboard.writeText(buildQuery(ver))
  copiedId.value = ver.datasetId
  setTimeout(() => (copiedId.value = null), 2000)
}

function openParams(res, ver) {
  paramsModal.value = {
    resourceName: res.resourceName,
    resourceParams: res.resourceParams || {},
    version: ver?.version ?? null,
    isLatest: ver?.isLatest ?? false,
    executionParams: ver?.executionParams ?? null,
  }
}

function confirmDelete(ver, resourceName) {
  toDelete.value = { ...ver, resourceName }
  deleteError.value = ''
}

async function doDelete() {
  if (!toDelete.value?.datasetId) return
  deleting.value = true
  deleteError.value = ''
  try {
    const resp = await fetch(`/api/datasets/${toDelete.value.datasetId}`, { method: 'DELETE' })
    if (!resp.ok) {
      const body = await resp.json().catch(() => ({}))
      throw new Error(body.detail || `HTTP ${resp.status}`)
    }
    if (expandedDataset.value === toDelete.value.datasetId) expandedDataset.value = null
    toDelete.value = null
    await loadTree()
  } catch (e) {
    deleteError.value = `Error: ${e.message}`
  } finally {
    deleting.value = false
  }
}
</script>
