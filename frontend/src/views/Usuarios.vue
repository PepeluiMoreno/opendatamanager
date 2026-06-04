<template>
  <div class="p-6 max-w-5xl mx-auto">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-100">👥 Usuarios</h1>
      <button class="bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded-lg" @click="abrirCrear">
        + Nuevo usuario
      </button>
    </div>

    <p v-if="error" class="text-sm text-red-400 mb-4">{{ error }}</p>

    <div class="bg-gray-800 rounded-xl overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-700/60 text-gray-300">
          <tr>
            <th class="text-left px-4 py-3">Usuario</th>
            <th class="text-left px-4 py-3">Email</th>
            <th class="text-left px-4 py-3">Roles</th>
            <th class="text-left px-4 py-3">Estado</th>
            <th class="text-left px-4 py-3">Último acceso</th>
            <th class="px-4 py-3"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in usuarios" :key="u.id" class="border-t border-gray-700/60 text-gray-200">
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
            <td class="px-4 py-3 text-right">
              <button class="text-blue-400 hover:text-blue-300 text-xs underline" @click="abrirEditar(u)">Editar</button>
            </td>
          </tr>
          <tr v-if="!usuarios.length">
            <td colspan="6" class="px-4 py-6 text-center text-gray-500">Sin usuarios.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Modal crear/editar -->
    <div v-if="form" class="fixed inset-0 z-[9000] flex items-center justify-center bg-black/60 p-4" @click.self="form = null">
      <div class="bg-gray-900 border border-gray-700 rounded-xl max-w-md w-full p-5">
        <h3 class="text-lg font-semibold text-gray-100 mb-4">{{ form.id ? `Editar ${form.username}` : 'Nuevo usuario' }}</h3>

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
        </div>

        <p v-if="formError" class="text-sm text-red-400 mt-3">{{ formError }}</p>

        <div class="flex justify-end gap-2 mt-5">
          <button class="text-sm text-gray-400 hover:text-gray-200 px-3 py-2" @click="form = null">Cancelar</button>
          <button class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded" :disabled="guardando" @click="guardar">
            {{ guardando ? 'Guardando…' : 'Guardar' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const usuarios = ref([])
const rolesDisponibles = ref([])
const error = ref('')
const form = ref(null)
const formError = ref('')
const guardando = ref(false)

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
  form.value = { id: null, username: '', email: '', password: '', roles: ['lector'], is_active: true }
}

function abrirEditar(u) {
  formError.value = ''
  form.value = { id: u.id, username: u.username, email: u.email || '', password: '', roles: [...u.roles], is_active: u.is_active }
}

async function guardar() {
  formError.value = ''
  guardando.value = true
  try {
    if (form.value.id) {
      const body = { email: form.value.email, roles: form.value.roles, is_active: form.value.is_active }
      if (form.value.password) body.password = form.value.password
      await api(`/${form.value.id}`, { method: 'PATCH', body: JSON.stringify(body) })
    } else {
      await api('', { method: 'POST', body: JSON.stringify({
        username: form.value.username, password: form.value.password,
        email: form.value.email || null, roles: form.value.roles, is_active: true,
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

onMounted(cargar)
</script>
