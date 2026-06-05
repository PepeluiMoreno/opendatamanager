<template>
  <div class="p-6 max-w-3xl mx-auto space-y-6">
    <h1 class="text-2xl font-semibold text-white">👤 Mis datos</h1>

    <!-- Datos personales -->
    <section class="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-4">Datos personales</h2>
      <div v-if="cargando" class="text-gray-500 text-sm">Cargando…</div>
      <div v-else class="space-y-4">
        <div>
          <label class="block text-xs text-gray-400 mb-1">Usuario</label>
          <div class="text-white font-mono">{{ perfil.username }}</div>
          <div class="mt-1 flex flex-wrap gap-1">
            <span v-for="r in perfil.roles" :key="r" class="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">{{ r }}</span>
          </div>
        </div>
        <div>
          <label class="block text-xs text-gray-400 mb-1">Correo electrónico</label>
          <input v-model="perfil.email" type="email" placeholder="sin definir"
                 class="input w-full text-sm bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white" />
        </div>
        <label class="flex items-center gap-2 text-sm text-gray-300">
          <input v-model="perfil.notificar_email" type="checkbox" />
          Recibir avisos por correo (novedades y vencimiento de recursos)
        </label>
        <div class="flex items-center gap-3">
          <button @click="guardarPerfil" :disabled="guardando"
                  class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded">
            Guardar cambios
          </button>
          <span v-if="msgPerfil" class="text-sm" :class="okPerfil ? 'text-green-400' : 'text-red-400'">{{ msgPerfil }}</span>
        </div>
      </div>
    </section>

    <!-- Cambiar contraseña -->
    <section class="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-4">Cambiar contraseña</h2>
      <div class="space-y-3">
        <input v-model="pw.actual" type="password" placeholder="Contraseña actual"
               class="w-full text-sm bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white" />
        <input v-model="pw.nueva" type="password" placeholder="Nueva contraseña (mín. 8)"
               class="w-full text-sm bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white" />
        <input v-model="pw.confirmar" type="password" placeholder="Repite la nueva contraseña"
               class="w-full text-sm bg-gray-900 border border-gray-600 rounded px-3 py-2 text-white" />
        <div class="flex items-center gap-3">
          <button @click="cambiarPassword" :disabled="cambiandoPw"
                  class="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white text-sm px-4 py-2 rounded">
            Actualizar contraseña
          </button>
          <span v-if="msgPw" class="text-sm" :class="okPw ? 'text-green-400' : 'text-red-400'">{{ msgPw }}</span>
        </div>
      </div>
    </section>

    <!-- Historial de recursos -->
    <section class="bg-gray-800 rounded-lg p-5 border border-gray-700">
      <h2 class="text-sm font-semibold uppercase tracking-wide text-gray-400 mb-4">Historial de recursos solicitados</h2>
      <p v-if="!historial.length" class="text-gray-500 text-sm">Aún no has solicitado recursos.</p>
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="text-left text-gray-400 border-b border-gray-700">
            <th class="py-2 pr-3">Recurso</th>
            <th class="py-2 pr-3">Solicitado</th>
            <th class="py-2 pr-3">Disponible hasta</th>
            <th class="py-2 pr-3">Estado</th>
            <th class="py-2"></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in historial" :key="l.id" class="border-b border-gray-800">
            <td class="py-2 pr-3 text-white">{{ l.recurso }}</td>
            <td class="py-2 pr-3 text-gray-400">{{ fecha(l.solicitado) }}</td>
            <td class="py-2 pr-3 text-gray-300">{{ l.permanente ? 'permanente' : (l.concedido_hasta ? fecha(l.concedido_hasta) : '—') }}</td>
            <td class="py-2 pr-3">
              <span class="text-xs px-2 py-0.5 rounded"
                    :class="{'bg-green-900 text-green-300': l.estado==='activo','bg-gray-700 text-gray-300': l.estado!=='activo'}">{{ l.estado }}</span>
            </td>
            <td class="py-2 text-right">
              <button v-if="l.estado==='activo'" @click="liberar(l)" class="text-xs text-gray-400 hover:text-red-400" title="Libera el recurso para que ODM pueda recuperar el espacio">ya no lo necesito</button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'

const cargando = ref(true)
const guardando = ref(false)
const cambiandoPw = ref(false)
const perfil = reactive({ username: '', email: '', notificar_email: false, roles: [] })
const pw = reactive({ actual: '', nueva: '', confirmar: '' })
const historial = ref([])
const msgPerfil = ref(''); const okPerfil = ref(false)
const msgPw = ref(''); const okPw = ref(false)

function fecha(iso) {
  if (!iso) return '—'
  try { return new Date(iso).toLocaleString() } catch { return iso }
}

async function cargar() {
  cargando.value = true
  try {
    const r = await fetch('/api/mis-datos', { credentials: 'same-origin' })
    if (r.ok) { const d = await r.json(); perfil.username = d.username; perfil.email = d.email || ''; perfil.notificar_email = !!d.notificar_email; perfil.roles = d.roles || [] }
    const h = await fetch('/api/mis-datos/historial', { credentials: 'same-origin' })
    if (h.ok) historial.value = (await h.json()).solicitudes || []
  } finally { cargando.value = false }
}

async function guardarPerfil() {
  guardando.value = true; msgPerfil.value = ''
  try {
    const r = await fetch('/api/mis-datos', { method: 'PUT', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: perfil.email || null, notificar_email: perfil.notificar_email }) })
    okPerfil.value = r.ok; msgPerfil.value = r.ok ? 'Guardado.' : 'No se pudo guardar.'
  } finally { guardando.value = false }
}

async function cambiarPassword() {
  msgPw.value = ''
  if (pw.nueva.length < 8) { okPw.value = false; msgPw.value = 'La nueva debe tener al menos 8 caracteres.'; return }
  if (pw.nueva !== pw.confirmar) { okPw.value = false; msgPw.value = 'Las contraseñas no coinciden.'; return }
  cambiandoPw.value = true
  try {
    const r = await fetch('/api/mis-datos/password', { method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ actual: pw.actual, nueva: pw.nueva }) })
    okPw.value = r.ok
    msgPw.value = r.ok ? 'Contraseña actualizada.' : ((await r.json().catch(() => ({}))).detail || 'No se pudo cambiar.')
    if (r.ok) { pw.actual = pw.nueva = pw.confirmar = '' }
  } finally { cambiandoPw.value = false }
}

async function liberar(l) {
  const r = await fetch(`/api/mis-datos/historial/${l.id}/liberar`, { method: 'POST', credentials: 'same-origin' })
  if (r.ok) l.estado = 'liberado'
}

onMounted(cargar)
</script>
