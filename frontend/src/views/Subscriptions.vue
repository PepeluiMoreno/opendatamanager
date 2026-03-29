<template>
  <div class="p-6 space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">Suscripciones</h1>
        <p class="text-gray-400 text-sm mt-1">Gestiona qué aplicaciones reciben notificaciones de cada resource</p>
      </div>
      <button @click="openNew" class="btn btn-primary">+ Nueva suscripción</button>
    </div>

    <!-- Error -->
    <div v-if="error" class="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm">{{ error }}</div>

    <!-- Table -->
    <div class="bg-gray-800 rounded-lg overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-700 text-gray-300 text-xs uppercase">
          <tr>
            <th class="px-4 py-3 text-left">Aplicación</th>
            <th class="px-4 py-3 text-left">Resource</th>
            <th class="px-4 py-3 text-left">Modo</th>
            <th class="px-4 py-3 text-left">Auto-upgrade</th>
            <th class="px-4 py-3 text-left">Versión actual</th>
            <th class="px-4 py-3 text-left">Última notif.</th>
            <th class="px-4 py-3 text-center">Acción</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="px-4 py-8 text-center text-gray-400">Cargando...</td>
          </tr>
          <tr v-else-if="!subscriptions.length">
            <td colspan="7" class="px-4 py-8 text-center text-gray-400">No hay suscripciones. Crea la primera.</td>
          </tr>
          <tr
            v-for="sub in subscriptions"
            :key="sub.id"
            class="border-t border-gray-700 hover:bg-gray-750"
          >
            <td class="px-4 py-3">
              <div class="font-medium">{{ appName(sub.applicationId) }}</div>
              <span
                class="text-xs px-1.5 py-0.5 rounded"
                :class="modeClass(appMode(sub.applicationId))"
              >{{ appMode(sub.applicationId) }}</span>
            </td>
            <td class="px-4 py-3">
              <div class="font-medium">{{ resourceName(sub.resourceId) }}</div>
              <div class="text-xs text-gray-400">{{ resourcePublisher(sub.resourceId) }}</div>
            </td>
            <td class="px-4 py-3 text-gray-300">{{ sub.pinnedVersion || '—' }}</td>
            <td class="px-4 py-3">
              <span class="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">{{ sub.autoUpgrade }}</span>
            </td>
            <td class="px-4 py-3 text-gray-300">{{ sub.currentVersion || '—' }}</td>
            <td class="px-4 py-3 text-gray-400 text-xs">{{ formatDate(sub.notifiedAt) }}</td>
            <td class="px-4 py-3 text-center">
              <button
                @click="confirmDelete(sub)"
                class="text-red-400 hover:text-red-300 text-xs"
              >Eliminar</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal nueva suscripción -->
    <div v-if="showModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-lg space-y-4">
        <h2 class="text-xl font-bold">Nueva suscripción</h2>

        <div>
          <label class="block text-sm font-medium mb-1">Aplicación *</label>
          <select v-model="form.applicationId" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
            <option value="">— Selecciona —</option>
            <option v-for="app in applications" :key="app.id" :value="app.id">
              {{ app.name }} ({{ app.consumptionMode }})
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-medium mb-1">Resource *</label>
          <select v-model="form.resourceId" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
            <option value="">— Selecciona —</option>
            <option v-for="res in resources" :key="res.id" :value="res.id">
              {{ res.name }} — {{ res.publisher }}
            </option>
          </select>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium mb-1">Versión anclada</label>
            <input
              v-model="form.pinnedVersion"
              type="text"
              placeholder="ej. 1.2.* ó vacío"
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 text-sm"
            />
            <p class="text-xs text-gray-400 mt-1">Vacío = sin restricción de versión</p>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Auto-upgrade</label>
            <select v-model="form.autoUpgrade" class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500">
              <option value="patch">patch — solo correcciones</option>
              <option value="minor">minor — cambios de campo</option>
              <option value="none">none — manual</option>
            </select>
          </div>
        </div>

        <div v-if="modalError" class="p-2 bg-red-900 border border-red-700 rounded text-red-200 text-sm">{{ modalError }}</div>

        <div class="flex justify-end gap-3 pt-2">
          <button @click="showModal = false" class="btn btn-secondary">Cancelar</button>
          <button
            @click="submitNew"
            :disabled="saving || !form.applicationId || !form.resourceId"
            class="btn btn-primary"
          >{{ saving ? 'Guardando...' : 'Suscribir' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import {
  fetchSubscriptions,
  subscribeResource,
  unsubscribeResource,
  fetchResources,
  fetchApplications,
} from '../api/graphql'

const subscriptions = ref([])
const resources = ref([])
const applications = ref([])
const loading = ref(true)
const error = ref(null)
const showModal = ref(false)
const saving = ref(false)
const modalError = ref(null)

const form = ref({ applicationId: '', resourceId: '', pinnedVersion: '', autoUpgrade: 'patch' })

onMounted(load)

async function load() {
  loading.value = true
  error.value = null
  try {
    const [subRes, resRes, appRes] = await Promise.all([
      fetchSubscriptions(),
      fetchResources(),
      fetchApplications(),
    ])
    subscriptions.value = subRes?.datasetSubscriptions ?? []
    resources.value = resRes?.resources ?? []
    applications.value = appRes?.applications ?? []
  } catch (e) {
    error.value = e.message || 'Error cargando datos'
  } finally {
    loading.value = false
  }
}

function openNew() {
  form.value = { applicationId: '', resourceId: '', pinnedVersion: '', autoUpgrade: 'patch' }
  modalError.value = null
  showModal.value = true
}

async function submitNew() {
  saving.value = true
  modalError.value = null
  try {
    await subscribeResource(
      form.value.applicationId,
      form.value.resourceId,
      form.value.pinnedVersion || null,
      form.value.autoUpgrade,
    )
    showModal.value = false
    await load()
  } catch (e) {
    modalError.value = e.message || 'Error al crear la suscripción'
  } finally {
    saving.value = false
  }
}

async function confirmDelete(sub) {
  const appLabel = appName(sub.applicationId)
  const resLabel = resourceName(sub.resourceId)
  if (!confirm(`¿Eliminar suscripción de "${appLabel}" a "${resLabel}"?`)) return
  try {
    await unsubscribeResource(sub.id)
    await load()
  } catch (e) {
    error.value = e.message || 'Error al eliminar'
  }
}

// Lookups
function appName(id) { return applications.value.find(a => a.id === id)?.name ?? id }
function appMode(id) { return applications.value.find(a => a.id === id)?.consumptionMode ?? '' }
function resourceName(id) { return resources.value.find(r => r.id === id)?.name ?? id }
function resourcePublisher(id) { return resources.value.find(r => r.id === id)?.publisher ?? '' }

function modeClass(mode) {
  return {
    graphql:  'bg-blue-900 text-blue-300',
    webhook:  'bg-purple-900 text-purple-300',
    both:     'bg-teal-900 text-teal-300',
  }[mode] ?? 'bg-gray-700 text-gray-300'
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z').toLocaleString('es-ES', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}
</script>
