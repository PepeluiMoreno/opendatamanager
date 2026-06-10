<template>
  <div class="p-6 flex flex-col gap-6 h-full">

    <!-- ── Maestro: suscriptores (FilterBar + datatable) ──────────────── -->
    <div class="flex flex-col min-h-0">
      <div class="flex items-center justify-end mb-3">
        <button @click="openCreateApp" class="btn btn-primary text-sm py-1 px-3">+ Subscriber</button>
      </div>

      <FilterBar :canClear="!!q || estadoFiltro !== 'todos'" :count="filteredApps.length" :total="applications.length"
                 @clear="q=''; estadoFiltro='todos'">
        <input v-model="q" type="text" placeholder="Buscar suscriptor…" class="input text-sm flex-1 min-w-[200px]" />
        <select v-model="estadoFiltro" class="input text-sm">
          <option value="todos">Todos</option>
          <option value="activos">Activos</option>
          <option value="inactivos">Inactivos</option>
        </select>
      </FilterBar>

      <div v-if="loading" class="text-gray-400 text-center py-8">Loading…</div>
      <div v-else-if="error" class="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm">{{ error }}</div>
      <div v-else-if="applications.length === 0" class="text-gray-400 text-sm py-8 text-center">
        Aún no hay suscriptores. Pulsa «New».
      </div>

      <div v-else class="bg-gray-800 rounded-xl overflow-hidden max-h-[42vh] overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="bg-gray-700/60 text-gray-300 sticky top-0">
            <tr>
              <th class="text-left px-4 py-3">Suscriptor</th>
              <th class="text-left px-4 py-3">Modo</th>
              <th class="text-center px-4 py-3">Suscripciones</th>
              <th class="text-left px-4 py-3">Estado</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="app in filteredApps" :key="app.id" @click="selectedAppId = app.id"
                :class="['border-t border-gray-700/60 cursor-pointer transition-colors',
                         selectedAppId === app.id ? 'bg-purple-900/25' : 'hover:bg-gray-700/30']">
              <td class="px-4 py-3">
                <div class="font-bold text-purple-300 truncate">{{ app.name }}</div>
                <div v-if="app.description" class="text-xs text-gray-400 mt-0.5 truncate max-w-md">{{ app.description }}</div>
              </td>
              <td class="px-4 py-3">
                <span class="text-xs font-mono px-2 py-0.5 rounded" :class="modeClass(app.consumptionMode)">
                  {{ app.consumptionMode === 'both' ? 'webhook + graphql' : app.consumptionMode }}
                </span>
              </td>
              <td class="px-4 py-3 text-center text-gray-300">{{ subsForApp(app.id).length }}</td>
              <td class="px-4 py-3">
                <span :class="app.active ? 'text-green-400' : 'text-red-400'" class="text-xs font-medium">
                  {{ app.active ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
            </tr>
            <tr v-if="filteredApps.length === 0">
              <td colspan="4" class="px-4 py-6 text-center text-gray-500">Sin resultados.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ── Detalle: suscripciones de la aplicación seleccionada ─────────── -->
    <section class="flex-1 flex flex-col min-h-0 rounded-xl border border-gray-700 bg-gray-800">
      <div v-if="!selectedApp" class="flex-1 flex items-center justify-center text-gray-500 text-sm">
        Selecciona un suscriptor para ver su cabecera y recursos autorizados.
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
            <button @click="toggleActive(selectedApp)" class="btn text-sm py-1 px-3" :class="selectedApp.active ? 'btn-secondary' : 'bg-emerald-600 hover:bg-emerald-500 text-white'">{{ selectedApp.active ? 'Desactivar' : 'Activar' }}</button>
            <button @click="openEditApp(selectedApp)" class="btn btn-secondary text-sm py-1 px-3">Edit app</button>
            <button @click="confirmDeleteApp(selectedApp)" class="btn btn-danger text-sm py-1 px-3">Delete app</button>
            <button @click="openNewSub" class="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-sm font-medium transition-colors">+ Subscription</button>
          </div>
        </div>

        <!-- #19 Cuota mensual de uso -->
        <div class="px-4 py-3 border-b border-gray-700 flex items-center gap-3 text-sm flex-shrink-0">
          <span class="text-gray-400">Uso del mes<span v-if="usoMensual"> ({{ usoMensual.periodo }})</span>:</span>
          <span v-if="usoMensual" class="text-white font-medium">{{ usoMensual.usados }} refrescos a demanda</span>
          <span v-else class="text-gray-600">—</span>
          <span v-if="usoMensual" class="text-xs text-gray-500 ml-1">· cuota diaria {{ usoMensual.cuotaDiaria }}/día</span>
        </div>
        <!-- Acceso M2M: principal + tokens (movido desde Approvals) -->
        <div class="px-4 py-3 border-b border-gray-700 flex-shrink-0">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs uppercase tracking-wide text-gray-500 font-medium">Acceso (token Bearer)</span>
            <div class="flex gap-2 items-center">
              <button v-if="principalSel" @click="emitirTok(principalSel)" class="btn text-xs py-1 px-2">Emitir token</button>
              <button v-else @click="crearAcceso(selectedApp)" class="btn btn-primary text-xs py-1 px-2">Crear acceso</button>
            </div>
          </div>
          <div v-if="!principalSel" class="text-xs text-gray-500">Sin acceso emitido. «Crear acceso» materializa el principal <span class="font-mono text-gray-400">{{ slugUsername(selectedApp.name) }}</span> y emite su token.</div>
          <div v-else>
            <div class="text-xs text-gray-400 mb-1">Principal: <span class="font-mono text-gray-300">{{ principalSel.username }}</span><span v-if="!principalSel.isActive" class="text-red-400 ml-2">(inactiva)</span></div>
            <div v-if="principalSel.tokens.length === 0" class="text-xs text-gray-500">Sin tokens.</div>
            <table v-else class="w-full text-xs">
              <thead class="text-left text-gray-500 border-b border-gray-700"><tr><th class="py-1 pr-3 font-medium">Token</th><th class="py-1 pr-3 font-medium">Último uso</th><th class="py-1 pr-3 font-medium">Estado</th><th class="py-1 font-medium text-right">Acciones</th></tr></thead>
              <tbody>
                <tr v-for="t in principalSel.tokens" :key="t.id" class="border-b border-gray-800">
                  <td class="py-1 pr-3 font-mono text-gray-300">{{ t.prefix }}…</td>
                  <td class="py-1 pr-3 text-gray-400">{{ t.lastUsedAt ? formatDate(t.lastUsedAt) : 'nunca' }}</td>
                  <td class="py-1 pr-3"><span v-if="t.activo" class="text-emerald-400">activo</span><span v-else-if="t.revokedAt" class="text-red-400">revocado</span><span v-else class="text-yellow-400">expirado</span></td>
                  <td class="py-1 text-right whitespace-nowrap">
                    <button v-if="t.activo" @click="rotarTok(principalSel, t)" title="Rotar" class="p-1.5 rounded transition-colors text-blue-400 hover:text-blue-300 hover:bg-blue-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg></button>
                    <button v-if="t.activo" @click="revocarTok(t)" title="Revocar" class="p-1.5 rounded transition-colors text-red-400 hover:text-red-300 hover:bg-red-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728A9 9 0 015.636 5.636"/></svg></button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="px-4 pt-3 pb-1 text-xs uppercase tracking-wide text-gray-500 font-medium flex-shrink-0">Recursos autorizados</div>

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
                  <button @click="confirmDeleteSub(sub)" title="Borrar suscripción" class="p-1.5 rounded transition-colors text-gray-500 hover:text-red-400 hover:bg-red-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
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
            <label class="block text-sm font-medium mb-2">Descripción</label>
            <textarea v-model="appForm.description" rows="5" class="input w-full"></textarea>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div><label class="block text-sm font-medium mb-1">Persona de contacto</label><input v-model="appForm.persona_contacto" type="text" class="input w-full" /></div>
            <div><label class="block text-sm font-medium mb-1">Email</label><input v-model="appForm.email" type="email" class="input w-full" /></div>
            <div><label class="block text-sm font-medium mb-1">Teléfono</label><input v-model="appForm.telefono" type="text" class="input w-full" /></div>
            <div><label class="block text-sm font-medium mb-1">Repositorio GitHub</label><input v-model="appForm.github_url" type="url" class="input w-full" placeholder="https://github.com/…" /></div>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Propósito</label>
            <input v-model="appForm.proposito" type="text" class="input w-full" />
          </div>
          <div>
            <label class="block text-sm font-medium mb-2">Modo de consumo</label>
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
          <div v-if="appForm.consumptionMode !== 'graphql'">
            <label class="block text-sm font-medium mb-2">Webhook URL</label>
            <input v-model="appForm.webhookUrl" type="url" class="input w-full" placeholder="https://tu-app/webhooks/odmgr" />
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
    <div v-if="tokenEmitido" class="fixed bottom-4 right-4 z-50 max-w-md rounded-xl border border-emerald-700 bg-emerald-950/95 backdrop-blur p-4 shadow-2xl">
      <h3 class="text-sm font-semibold text-emerald-300 mb-1">Token emitido para «{{ tokenEmitido.username }}»</h3>
      <p class="text-xs text-emerald-200/80 mb-2">Cópialo ahora: no se vuelve a mostrar.</p>
      <div class="flex items-center gap-2">
        <code class="flex-1 text-xs bg-gray-900 rounded px-3 py-2 break-all text-emerald-200">{{ tokenEmitido.token }}</code>
        <button @click="copiar(tokenEmitido.token)" class="btn text-xs whitespace-nowrap">Copiar</button>
        <button @click="tokenEmitido = null" class="text-gray-400 hover:text-white text-xs px-2">Ocultar</button>
      </div>
    </div>
    <ConfirmDialog v-if="confirmar" :title="confirmar.title" :message="confirmar.message"
      :confirmText="confirmar.confirmText || 'Confirmar'" cancelText="Cancelar"
      @confirm="okConfirm" @cancel="cerrarConfirm" />
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
const confirmar = ref(null)
function okConfirm() { const f = confirmar.value?.onConfirm; confirmar.value = null; if (f) f() }
function cerrarConfirm() { confirmar.value = null }

import { usePagination } from '../composables/usePagination.js'
import Paginator from '../components/Paginator.vue'
import FilterBar from '../components/FilterBar.vue'
import {
  fetchApplications, createApplication, updateApplication, deleteApplication, activateApplication, fetchUsoMensualAplicacion,
  fetchSubscriptions, subscribeResource, unsubscribeResource, fetchResources,
  fetchAplicacionesM2M, crearAplicacion, emitirTokenAplicacion, rotarTokenAplicacion, revocarTokenAplicacion,
} from '../api/graphql'

const applications  = ref([])
const subscriptions = ref([])
const resources     = ref([])
const loading       = ref(true)
const error         = ref(null)
const selectedAppId = ref('')
const aplicaciones  = ref([])
const tokenEmitido  = ref(null)
const q             = ref('')
const estadoFiltro  = ref('todos')

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
const appForm = ref({ name: '', description: '', webhookUrl: '', consumptionMode: 'webhook', active: true, persona_contacto: '', email: '', telefono: '', github_url: '', proposito: '' })

// Subscription state
const showSubModal  = ref(false)
const saving        = ref(false)
const subModalError = ref(null)
const subForm = ref({ resourceId: '', pinnedVersion: '', autoUpgrade: 'patch' })

const selectedApp = computed(() => applications.value.find(a => a.id === selectedAppId.value) || null)
const usoMensual = ref(null)
watch(selectedAppId, async (id) => {
  usoMensual.value = null
  if (!id) return
  const d = await fetchUsoMensualAplicacion(id)
  usoMensual.value = d?.usoMensualAplicacion || null
})
function subsForApp(id) { return subscriptions.value.filter(s => s.applicationId === id) }
const subsSeleccionada = computed(() => selectedApp.value ? subsForApp(selectedApp.value.id) : [])
const { page: aPage, perPage: aPerPage, total: aTotal, paged: pagedSubs } = usePagination(subsSeleccionada, 25)

onMounted(load)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [appRes, subRes, resRes, accRes] = await Promise.all([
      fetchApplications(), fetchSubscriptions(), fetchResources(), fetchAplicacionesM2M(),
    ])
    applications.value  = appRes?.applications        ?? []
    subscriptions.value = subRes?.resourceSubscriptions ?? []
    resources.value     = resRes?.resources           ?? []
    aplicaciones.value  = accRes?.aplicacionesM2m     ?? []
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
  appForm.value = { name: '', description: '', webhookUrl: '', consumptionMode: 'webhook', active: true, persona_contacto: '', email: '', telefono: '', github_url: '', proposito: '' }
  appModalError.value = null
  showAppModal.value = true
}
function openEditApp(app) {
  editingApp.value = app
  appForm.value = {
    name: app.name, description: app.description || '', webhookUrl: app.webhookUrl || '',
    consumptionMode: app.consumptionMode || 'webhook', active: app.active,
    persona_contacto: app.personaContacto || '', email: app.email || '', telefono: app.telefono || '',
    github_url: app.githubUrl || '', proposito: app.proposito || '',
  }
  appModalError.value = null
  showAppModal.value = true
}
function closeAppModal() { showAppModal.value = false; editingApp.value = null }
async function submitApp() {
  appModalError.value = null
  try {
    const f = appForm.value
    const input = {
      name: f.name, description: f.description,
      webhookUrl: f.consumptionMode === 'graphql' ? null : (f.webhookUrl || null),
      consumptionMode: f.consumptionMode, active: f.active,
      personaContacto: f.persona_contacto || null, email: f.email || null,
      telefono: f.telefono || null, githubUrl: f.github_url || null, proposito: f.proposito || null,
    }
    if (editingApp.value) await updateApplication(editingApp.value.id, input)
    else                  await createApplication(input)
    closeAppModal()
    await load()
  } catch (e) { appModalError.value = e.message || 'Failed to save application' }
}
function confirmDeleteApp(app) { appToDelete.value = app; hardDeleteFlag.value = false; showDeleteAppModal.value = true }
async function toggleActive(app) {
  const nuevo = !app.active
  try { await activateApplication(app.id, nuevo); app.active = nuevo } catch (e) { /* graphql.js maneja el error */ }
}

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
  confirmar.value = {
    title: 'Borrar suscripción',
    message: `Quitar la suscripción de «${selectedApp.value?.name}» a «${resourceName(sub.resourceId)}».`,
    onConfirm: async () => { try { await unsubscribeResource(sub.id); await load() } catch (e) { error.value = e.message || 'Error deleting subscription' } },
  }
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

// ── #34 Acceso M2M (principal + tokens) por aplicación ──
function slugUsername(name) {
  return 'app-' + String(name || '').toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '')
}
const principalSel = computed(() => {
  if (!selectedApp.value) return null
  const u = slugUsername(selectedApp.value.name)
  return aplicaciones.value.find(a => a.username === u) || null
})
const filteredApps = computed(() => {
  const s = q.value.trim().toLowerCase()
  return applications.value.filter(a => {
    if (estadoFiltro.value === 'activos' && !a.active) return false
    if (estadoFiltro.value === 'inactivos' && a.active) return false
    if (!s) return true
    return (a.name || '').toLowerCase().includes(s) || (a.description || '').toLowerCase().includes(s)
  })
})
function copiar(t) { try { navigator.clipboard?.writeText(t) } catch { /* no-op */ } }
async function reloadAcc() { const d = await fetchAplicacionesM2M(); aplicaciones.value = d?.aplicacionesM2m || [] }
async function crearAcceso(app) {
  try { const d = await crearAplicacion(app.name, null); const r = d?.crearAplicacion; if (r) tokenEmitido.value = { username: slugUsername(app.name), token: r.token }; await reloadAcc() }
  catch (e) { error.value = e.message || 'No se pudo crear el acceso' }
}
async function emitirTok(p) {
  try { const d = await emitirTokenAplicacion(p.usuarioId, null); const r = d?.emitirTokenAplicacion; if (r) tokenEmitido.value = { username: p.username, token: r.token }; await reloadAcc() }
  catch (e) { error.value = e.message || 'No se pudo emitir el token' }
}
function rotarTok(p, tok) {
  confirmar.value = { title: 'Rotar token', confirmText: 'Rotar',
    message: `Rotar ${tok.prefix}… El token actual quedará revocado de inmediato.`,
    onConfirm: async () => { const d = await rotarTokenAplicacion(tok.id, null); const r = d?.rotarTokenAplicacion; if (r) tokenEmitido.value = { username: p.username, token: r.token }; await reloadAcc() } }
}
function revocarTok(tok) {
  confirmar.value = { title: 'Revocar token', confirmText: 'Revocar',
    message: `Revocar ${tok.prefix}… Es inmediato e irreversible.`,
    onConfirm: async () => { await revocarTokenAplicacion(tok.id); await reloadAcc() } }
}
</script>
