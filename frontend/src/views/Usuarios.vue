<template>
  <div class="p-6">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-100">👥 Users</h1>
      <button class="bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg" @click="abrirCrear">
        + Nuevo usuario
      </button>
    </div>

    <p v-if="error" class="text-sm text-red-400 mb-4">{{ error }}</p>

    <div class="bg-gray-800 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-700/60 text-gray-300">
          <tr>
            <th class="text-left px-4 py-3">Username</th>
            <th class="text-left px-4 py-3">Email</th>
            <th class="text-left px-4 py-3">Roles</th>
            <th class="text-left px-4 py-3">Status</th>
            <th class="text-left px-4 py-3">Last access</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in pagedUsuarios" :key="u.id" class="border-t border-gray-700/60 text-gray-200">
            <td class="px-4 py-3 font-medium">{{ u.username }}</td>
            <td class="px-4 py-3 text-gray-400">{{ u.email || '—' }}</td>
            <td class="px-4 py-3">
              <span v-for="r in u.roles" :key="r" class="inline-block bg-gray-700 rounded px-2 py-0.5 text-xs mr-1">{{ r }}</span>
              <span v-if="!u.roles.length" class="text-gray-500 text-xs">sin rol</span>
            </td>
            <td class="px-4 py-3">
              <span :class="u.is_active ? 'text-green-400' : 'text-red-400'">{{ u.is_active ? 'Activo' : 'Inactivo' }}</span>
            </td>
            <td class="px-4 py-3 text-gray-400 text-xs">{{ u.last_login_at ? new Date(u.last_login_at).toLocaleString() : 'nunca' }}</td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <button @click="abrirEditar(u)" title="Editar" class="act-icon">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/></svg>
              </button>
              <button @click="confirmarBorrado(u)" title="Borrar" class="act-icon danger">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </td>
          </tr>
          <tr v-if="!usuarios.length">
            <td colspan="6" class="px-4 py-6 text-center text-gray-500">Sin usuarios.</td>
          </tr>
        </tbody>
      </table>
        <Paginator v-model:page="uPage" v-model:perPage="uPerPage" :total="uTotal" />
    </div>

    <!-- Drawer crear/editar -->
    <Drawer :model-value="!!form" @update:model-value="v => { if (!v) form = null }"
            :title="form ? (form.id ? `Editar ${form.username}` : 'Nuevo usuario') : ''"
            :icon="form && form.id ? '✎' : '＋'" :width="560">
      <template v-if="form">
        <div class="space-y-3">
          <div v-if="!form.id">
            <label class="block text-xs text-gray-400 mb-1">Usuario</label>
            <input v-model="form.username" type="text" class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-400 mb-1">Email (opcional)</label>
            <input v-model="form.email" type="email" class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-400 mb-1">{{ form.id ? 'Nueva contraseña (vacío = sin cambio; cierra sus sesiones)' : 'Contraseña' }}</label>
            <input v-model="form.password" type="password" autocomplete="new-password" class="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" />
          </div>
          <div>
            <label class="block text-xs text-gray-400 mb-1">Roles</label>
            <label v-for="r in rolesDisponibles" :key="r.code" class="flex items-start gap-2 py-1 cursor-pointer">
              <input type="checkbox" :value="r.code" v-model="form.roles" class="mt-0.5 rounded bg-gray-800 border-gray-700" />
              <span class="text-sm text-gray-200">{{ r.nombre }} <span class="text-xs text-gray-500">— {{ r.descripcion }}</span></span>
            </label>
          </div>
          <label v-if="form.id" class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="form.is_active" class="rounded bg-gray-800 border-gray-700" />
            <span class="text-sm text-gray-200">Activo</span>
          </label>
          <label class="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" v-model="form.notificar_email" class="rounded bg-gray-800 border-gray-700" />
            <span class="text-sm text-gray-200">Avisarme por email de novedades (altas/bajas de recursos)</span>
          </label>
          <p v-if="formError" class="text-sm text-red-400 mt-1">{{ formError }}</p>
        </div>
      </template>
      <template #footer>
        <div class="flex-1"></div>
        <button class="text-sm text-gray-400 hover:text-gray-200 px-3 py-2" @click="form = null">Cancelar</button>
        <button class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded" :disabled="guardando" @click="guardar">
          {{ guardando ? 'Guardando…' : 'Guardar' }}
        </button>
      </template>
    </Drawer>
    <ConfirmDialog v-if="confirmar" :title="confirmar.title" :message="confirmar.message"
      :confirmText="confirmar.confirmText || 'Confirmar'" cancelText="Cancelar"
      @confirm="okConfirm" @cancel="cerrarConfirm" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { usePagination } from '../composables/usePagination.js'
import Paginator from '../components/Paginator.vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import Drawer from '../components/Drawer.vue'

const usuarios = ref([])
const { page: uPage, perPage: uPerPage, total: uTotal, paged: pagedUsuarios } = usePagination(usuarios, 25)
const rolesDisponibles = ref([])
const error = ref('')
const form = ref(null)
const formError = ref('')
const guardando = ref(false)
const confirmar = ref(null)

async function api(path, options = {}) {
  const r = await fetch(`/api/usuarios${path}`, {
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!r.ok) {
    let detalle = `Error ${r.status}`
    try { detalle = (await r.json()).detail || detalle } catch { /* sin cuerpo */ }
    throw new Error(detalle)
  }
  return r.status === 204 ? null : r.json()
}

async function cargar() {
  error.value = ''
  try {
    usuarios.value = await api('')
    rolesDisponibles.value = await api('/roles')
  } catch (e) {
    error.value = e.message
  }
}

function abrirCrear() {
  formError.value = ''
  form.value = { id: null, username: '', email: '', password: '', roles: ['lector'], is_active: true, notificar_email: false }
}

function abrirEditar(u) {
  formError.value = ''
  form.value = { id: u.id, username: u.username, email: u.email || '', password: '', roles: [...u.roles], is_active: u.is_active, notificar_email: !!u.notificar_email }
}

async function guardar() {
  formError.value = ''
  guardando.value = true
  try {
    if (form.value.id) {
      const body = { email: form.value.email, roles: form.value.roles, is_active: form.value.is_active, notificar_email: form.value.notificar_email }
      if (form.value.password) body.password = form.value.password
      await api(`/${form.value.id}`, { method: 'PATCH', body: JSON.stringify(body) })
    } else {
      await api('', { method: 'POST', body: JSON.stringify({
        username: form.value.username, password: form.value.password,
        email: form.value.email || null, roles: form.value.roles, is_active: true, notificar_email: form.value.notificar_email,
      }) })
    }
    form.value = null
    await cargar()
  } catch (e) {
    formError.value = e.message
  } finally {
    guardando.value = false
  }
}

function confirmarBorrado(u) {
  confirmar.value = {
    title: 'Borrar usuario',
    message: `Borrar a «${u.username}» de forma permanente. Esta acción no se puede deshacer.`,
    confirmText: 'Borrar',
    onConfirm: async () => {
      try { await api(`/${u.id}`, { method: 'DELETE' }); await cargar() }
      catch (e) { error.value = e.message }
    },
  }
}
async function okConfirm() { const f = confirmar.value?.onConfirm; confirmar.value = null; if (f) await f() }
function cerrarConfirm() { confirmar.value = null }

onMounted(cargar)
</script>
