<template>
  <div class="p-6 space-y-6" style="min-height:100%">
    <div v-if="accionError" class="bg-red-900/40 border border-red-700 text-red-200 text-sm rounded-lg px-3 py-2">
      {{ accionError }}
      <button @click="accionError=''" class="float-right text-red-300 hover:text-white">✕</button>
    </div>

    <!-- Token recién emitido (display-once) -->
    <div v-if="tokenEmitido" class="card border border-emerald-700 bg-emerald-950/30 p-4">
      <h3 class="text-sm font-semibold text-emerald-300 mb-1">Token emitido para «{{ tokenEmitido.username }}»</h3>
      <p class="text-xs text-gray-400 mb-2">
        Cópialo ahora: <strong>no se volverá a mostrar</strong>. El suscriptor lo usará como
        <code>Authorization: Bearer …</code>.
      </p>
      <div class="flex items-center gap-2">
        <code class="flex-1 text-xs bg-gray-900 rounded px-3 py-2 break-all text-emerald-200">{{ tokenEmitido.token }}</code>
        <button @click="copiar(tokenEmitido.token)" class="btn text-xs whitespace-nowrap">Copiar</button>
        <button @click="tokenEmitido = null" class="text-gray-400 hover:text-white text-xs px-2">Ocultar</button>
      </div>
    </div>

    <!-- §12 Solicitudes de alta de suscriptores -->
    <section v-if="puede('aplicaciones.aprobar')">
      <div class="text-xs uppercase tracking-wide text-gray-500 font-medium mb-2">Solicitudes de alta de suscriptores</div>
      <FilterBar :canClear="!!solQ || estadoFiltro !== 'pendiente'" :count="solicitudesFiltradas.length" :total="solicitudes.length"
                 @clear="solQ=''; estadoFiltro='pendiente'">
        <input v-model="solQ" type="text" placeholder="Buscar suscriptor…" class="input text-sm w-64 max-w-[40%]" />
        <select v-model="estadoFiltro" class="input text-sm">
          <option value="">Todas</option>
          <option value="pendiente">Pendientes</option>
          <option value="aprobada">Admitidas</option>
          <option value="rechazada">Rechazadas</option>
          <option value="anulada">Anuladas</option>
        </select>
      </FilterBar>

      <div v-if="cargandoSol" class="text-gray-400 text-center py-8">Cargando…</div>
      <div v-else-if="solicitudesFiltradas.length === 0" class="text-gray-400 text-sm py-8 text-center">No hay solicitudes.</div>
      <div v-else class="bg-gray-800 rounded-xl overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-700/60 text-gray-300">
            <tr>
              <th class="text-left px-4 py-3">Subscriber</th>
              <th class="text-left px-4 py-3">Contact</th>
              <th class="text-left px-4 py-3">Purpose</th>
              <th class="text-left px-4 py-3">GitHub</th>
              <th class="text-left px-4 py-3">Requested</th>
              <th class="text-left px-4 py-3">Status</th>
              <th class="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in solicitudesFiltradas" :key="s.id" class="border-t border-gray-700/60 hover:bg-gray-700/30 align-top">
              <td class="px-4 py-3 text-white font-medium">{{ s.nombre }}<span v-if="s.yaRegistrada" class="ml-2 px-1.5 py-0.5 rounded text-[10px] bg-amber-900/40 text-amber-300 font-normal align-middle" title="Ya existe un suscriptor con este nombre: es una re-alta (re-llaveo), no uno nuevo">re-alta</span><span v-if="s.descripcion" class="block text-xs text-gray-500 font-normal">{{ s.descripcion }}</span><span v-if="s.consumptionMode" class="block text-xs text-gray-500 font-normal">modo: {{ s.consumptionMode }}</span><span v-if="s.webhookUrl" class="block text-xs text-gray-600 font-normal break-all">{{ s.webhookUrl }}</span></td>
              <td class="px-4 py-3 text-gray-300">
                <span v-if="s.personaContacto">{{ s.personaContacto }}</span>
                <span v-if="s.email" class="block text-xs text-gray-400">{{ s.email }}</span>
                <span v-if="s.telefono" class="block text-xs text-gray-500">{{ s.telefono }}</span>
                <span v-if="!s.personaContacto && !s.email && !s.telefono">{{ s.contacto || '—' }}</span>
              </td>
              <td class="px-4 py-3 text-gray-400">{{ s.proposito || '—' }}</td>
              <td class="px-4 py-3">
                <a v-if="s.githubUrl" :href="s.githubUrl" target="_blank" rel="noopener" class="text-blue-400 hover:text-blue-300 underline text-xs break-all">{{ s.githubUrl }}</a>
                <span v-else class="text-gray-500">—</span>
              </td>
              <td class="px-4 py-3 text-gray-400">{{ fecha(s.createdAt) }}</td>
              <td class="px-4 py-3">
                <span :class="s.estado==='aprobada' ? 'text-emerald-400' : s.estado==='rechazada' ? 'text-red-400' : s.estado==='anulada' ? 'text-gray-400' : 'text-yellow-400'">{{ estadoLabel(s.estado) }}</span>
                <span v-if="s.estado==='rechazada' && s.motivo" class="block text-xs text-gray-500">{{ s.motivo }}</span>
              </td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <button v-if="(s.estado || 'pendiente')==='pendiente'" @click="aprobarSol(s)" title="Aprobar" class="p-1.5 rounded transition-colors text-emerald-400 hover:text-emerald-300 hover:bg-emerald-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg></button>
                <button v-if="(s.estado || 'pendiente')==='pendiente'" @click="rechazarSol(s)" title="Rechazar" class="p-1.5 rounded transition-colors text-red-400 hover:text-red-300 hover:bg-red-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636"/></svg></button>
                <button @click="eliminarSol(s)" title="Eliminar" class="act-icon danger"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- §11 Recursos propuestos -->
    <section v-if="puede('recursos.aprobar')">
      <div class="text-xs uppercase tracking-wide text-gray-500 font-medium mb-2">Recursos propuestos</div>
      <div v-if="cargandoRec" class="text-gray-400 text-center py-8">Cargando…</div>
      <div v-else-if="recursos.length === 0" class="text-gray-400 text-sm py-8 text-center">No hay recursos pendientes de aprobación.</div>
      <div v-else class="bg-gray-800 rounded-xl overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-700/60 text-gray-300">
            <tr>
              <th class="text-left px-4 py-3">Resource</th>
              <th class="text-left px-4 py-3">Publisher</th>
              <th class="text-left px-4 py-3">Species</th>
              <th class="text-left px-4 py-3">Proposed</th>
              <th class="text-right px-4 py-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in recursos" :key="r.id" class="border-t border-gray-700/60 hover:bg-gray-700/30 align-top">
              <td class="px-4 py-3">
                <div class="text-white font-medium">{{ r.name }}</div>
                <div class="text-xs text-gray-500">{{ r.description || '' }}</div>
              </td>
              <td class="px-4 py-3 text-gray-300">{{ r.publisher || '—' }}</td>
              <td class="px-4 py-3 text-gray-400">{{ r.fetcher?.code || '—' }}</td>
              <td class="px-4 py-3 text-gray-400">{{ fecha(r.createdAt) }}</td>
              <td class="px-4 py-3 text-right whitespace-nowrap">
                <button @click="aprobarRec(r)" title="Aprobar" class="p-1.5 rounded transition-colors text-emerald-400 hover:text-emerald-300 hover:bg-emerald-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg></button>
                <button @click="rechazarRec(r)" title="Rechazar" class="p-1.5 rounded transition-colors text-red-400 hover:text-red-300 hover:bg-red-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636"/></svg></button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

  </div>
    <div v-if="rechazo" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50" @click.self="cerrarRechazo">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md shadow-xl">
        <h3 class="text-lg font-bold text-white mb-1">Rechazar</h3>
        <p class="text-sm text-gray-300 mb-3">Vas a rechazar «{{ rechazo.nombre }}». Indica el motivo (opcional):</p>
        <textarea v-model="rechazo.motivo" rows="3" class="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200" placeholder="Motivo del rechazo…"></textarea>
        <div class="flex justify-end gap-2 mt-4">
          <button @click="cerrarRechazo" class="btn btn-secondary">Cancelar</button>
          <button @click="confirmarRechazo" class="btn btn-danger">Rechazar</button>
        </div>
      </div>
    </div>
    <ConfirmDialog v-if="confirmar" :title="confirmar.title" :message="confirmar.message"
      :confirmText="confirmar.confirmText || 'Confirmar'" cancelText="Cancelar"
      @confirm="okConfirm" @cancel="cerrarConfirm" />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
import FilterBar from '../components/FilterBar.vue'
const confirmar = ref(null)
const rechazo = ref(null)
const accionError = ref('')
function cerrarRechazo() { rechazo.value = null }
async function confirmarRechazo() {
  const r = rechazo.value; rechazo.value = null
  if (!r) return
  accionError.value = ''
  try {
    if (r.tipo === 'sol') await _rechazarSol(r.id, r.motivo); else await _rechazarRec(r.id, r.motivo)
  } catch (e) {
    accionError.value = 'No se pudo rechazar: ' + (e?.message || e)
  }
}
function okConfirm() { const f = confirmar.value?.onConfirm; confirmar.value = null; if (f) f() }
function cerrarConfirm() { confirmar.value = null }

import { useAuth } from '../composables/useAuth'
import {
  fetchSolicitudesIngreso, aprobarSolicitudIngreso, rechazarSolicitudIngreso,
  fetchRecursosPropuestos, aprobarRecurso, rechazarRecurso,
  eliminarSolicitudIngreso,
} from '../api/graphql'

const { puede } = useAuth()

const solicitudes = ref([])
const recursos = ref([])
const cargandoSol = ref(false)
const cargandoRec = ref(false)
const tokenEmitido = ref(null)
const estadoFiltro = ref('pendiente')
const solQ = ref('')
const solicitudesFiltradas = computed(() => {
  const q = solQ.value.trim().toLowerCase()
  return solicitudes.value.filter(x => {
    if (estadoFiltro.value && (x.estado || 'pendiente') !== estadoFiltro.value) return false
    if (!q) return true
    return (x.nombre || '').toLowerCase().includes(q) || (x.email || '').toLowerCase().includes(q)
      || (x.personaContacto || '').toLowerCase().includes(q) || (x.proposito || '').toLowerCase().includes(q)
  })
})

function estadoLabel(e) { return e === 'aprobada' ? 'Admitida' : e === 'rechazada' ? 'Rechazada' : e === 'anulada' ? 'Anulada' : 'Pendiente' }
async function eliminarSol(s) {
  if (!window.confirm(`¿Eliminar la solicitud de «${s.nombre}»?`)) return
  accionError.value = ''
  try { await eliminarSolicitudIngreso(s.id); solicitudes.value = solicitudes.value.filter(x => x.id !== s.id) }
  catch (e) { accionError.value = 'No se pudo eliminar la solicitud: ' + (e?.message || e) }
}

function fecha(s) {
  if (!s) return '—'
  try { return new Date(s).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' }) } catch { return s }
}
function copiar(t) { try { navigator.clipboard?.writeText(t) } catch { /* no-op */ } }

async function cargarSolicitudes() {
  if (!puede('aplicaciones.aprobar')) return
  cargandoSol.value = true
  try { const d = await fetchSolicitudesIngreso(false); solicitudes.value = d?.solicitudesIngreso || [] }
  finally { cargandoSol.value = false }
}
async function cargarRecursos() {
  if (!puede('recursos.aprobar')) return
  cargandoRec.value = true
  try { const d = await fetchRecursosPropuestos(); recursos.value = d?.recursosPropuestos || [] }
  finally { cargandoRec.value = false }
}

async function aprobarSol(s) {
  accionError.value = ''
  try {
    const d = await aprobarSolicitudIngreso(s.id)
    const r = d?.aprobarSolicitudIngreso
    if (r) tokenEmitido.value = { username: r.username, token: r.token }
    solicitudes.value = solicitudes.value.filter(x => x.id !== s.id)
    await cargarSolicitudes()
  } catch (e) {
    accionError.value = 'No se pudo aprobar la solicitud: ' + (e?.message || e)
  }
}
function rechazarSol(s) { rechazo.value = { tipo: 'sol', id: s.id, nombre: s.nombre, motivo: '' } }
async function _rechazarSol(s_id, motivo) {
  await rechazarSolicitudIngreso(s_id, motivo || null)
  solicitudes.value = solicitudes.value.filter(x => x.id !== s_id)
  await cargarSolicitudes()
}
async function aprobarRec(r) {
  accionError.value = ''
  try {
    await aprobarRecurso(r.id)
    await cargarRecursos()
  } catch (e) {
    accionError.value = 'No se pudo aprobar el recurso: ' + (e?.message || e)
  }
}
function rechazarRec(r) { rechazo.value = { tipo: 'rec', id: r.id, nombre: r.name, motivo: '' } }
async function _rechazarRec(r_id, motivo) {
  await rechazarRecurso(r_id, motivo || null)
  await cargarRecursos()
}

onMounted(() => { cargarSolicitudes(); cargarRecursos() })
</script>
