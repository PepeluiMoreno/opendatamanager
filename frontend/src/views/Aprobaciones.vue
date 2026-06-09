<template>
  <div class="p-6 space-y-6" style="min-height:100%">
    <div>
      <h1 class="text-2xl font-bold text-white">Aprobaciones</h1>
      <p class="text-gray-400 text-sm mt-1">
        Bandeja de administración: solicitudes de alta de aplicaciones y recursos
        propuestos por ellas, pendientes de autorizar o rechazar.
      </p>
    </div>

    <!-- Token recién emitido (display-once) -->
    <div v-if="tokenEmitido" class="card border border-emerald-700 bg-emerald-950/30">
      <h3 class="text-sm font-semibold text-emerald-300 mb-1">Token emitido para «{{ tokenEmitido.username }}»</h3>
      <p class="text-xs text-gray-400 mb-2">
        Cópialo ahora: <strong>no se volverá a mostrar</strong>. La aplicación lo usará como
        <code>Authorization: Bearer …</code>.
      </p>
      <div class="flex items-center gap-2">
        <code class="flex-1 text-xs bg-gray-900 rounded px-3 py-2 break-all text-emerald-200">{{ tokenEmitido.token }}</code>
        <button @click="copiar(tokenEmitido.token)" class="btn text-xs whitespace-nowrap">Copiar</button>
        <button @click="tokenEmitido = null" class="text-gray-400 hover:text-white text-xs px-2">Ocultar</button>
      </div>
    </div>

    <!-- §12 Solicitudes de alta de aplicaciones -->
    <section v-if="puede('aplicaciones.aprobar')">
      <h2 class="text-lg font-semibold text-white mb-2">Solicitudes de alta de aplicaciones</h2>
      <div class="card">
        <div v-if="cargandoSol" class="p-6 text-center text-gray-400">Cargando…</div>
        <div v-else-if="solicitudes.length === 0" class="p-6 text-center text-gray-400">No hay solicitudes pendientes.</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="text-left text-gray-400 border-b border-gray-700">
              <tr><th class="py-2 px-4 font-medium">Aplicación</th><th class="py-2 px-4 font-medium">Contacto</th>
                <th class="py-2 px-4 font-medium">Propósito</th><th class="py-2 px-4 font-medium">Solicitada</th>
                <th class="py-2 px-4 font-medium text-right">Acciones</th></tr>
            </thead>
            <tbody>
              <tr v-for="s in solicitudes" :key="s.id" class="border-b border-gray-700/50 hover:bg-gray-700/30">
                <td class="py-2 px-4 text-white font-medium">{{ s.nombre }}</td>
                <td class="py-2 px-4 text-gray-300">{{ s.contacto || '—' }}</td>
                <td class="py-2 px-4 text-gray-400">{{ s.proposito || '—' }}</td>
                <td class="py-2 px-4 text-gray-400">{{ fecha(s.createdAt) }}</td>
                <td class="py-2 px-4 text-right whitespace-nowrap">
                  <button @click="aprobarSol(s)" title="Aprobar" class="p-1.5 rounded transition-colors text-emerald-400 hover:text-emerald-300 hover:bg-emerald-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg></button>
                  <button @click="rechazarSol(s)" title="Rechazar" class="p-1.5 rounded transition-colors text-red-400 hover:text-red-300 hover:bg-red-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- §11 Recursos propuestos -->
    <section v-if="puede('recursos.aprobar')">
      <h2 class="text-lg font-semibold text-white mb-2">Recursos propuestos</h2>
      <div class="card">
        <div v-if="cargandoRec" class="p-6 text-center text-gray-400">Cargando…</div>
        <div v-else-if="recursos.length === 0" class="p-6 text-center text-gray-400">No hay recursos pendientes de aprobación.</div>
        <div v-else class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead class="text-left text-gray-400 border-b border-gray-700">
              <tr><th class="py-2 px-4 font-medium">Recurso</th><th class="py-2 px-4 font-medium">Publisher</th>
                <th class="py-2 px-4 font-medium">Especie</th><th class="py-2 px-4 font-medium">Propuesto</th>
                <th class="py-2 px-4 font-medium text-right">Acciones</th></tr>
            </thead>
            <tbody>
              <tr v-for="r in recursos" :key="r.id" class="border-b border-gray-700/50 hover:bg-gray-700/30">
                <td class="py-2 px-4">
                  <div class="text-white font-medium">{{ r.name }}</div>
                  <div class="text-xs text-gray-500">{{ r.description || '' }}</div>
                </td>
                <td class="py-2 px-4 text-gray-300">{{ r.publisher || '—' }}</td>
                <td class="py-2 px-4 text-gray-400">{{ r.fetcher?.code || '—' }}</td>
                <td class="py-2 px-4 text-gray-400">{{ fecha(r.createdAt) }}</td>
                <td class="py-2 px-4 text-right whitespace-nowrap">
                  <button @click="aprobarRec(r)" title="Aprobar" class="p-1.5 rounded transition-colors text-emerald-400 hover:text-emerald-300 hover:bg-emerald-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg></button>
                  <button @click="rechazarRec(r)" title="Rechazar" class="p-1.5 rounded transition-colors text-red-400 hover:text-red-300 hover:bg-red-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg></button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- §12 Aplicaciones registradas y sus tokens -->
    <section v-if="puede('aplicaciones.aprobar')">
      <h2 class="text-lg font-semibold text-white mb-2">Aplicaciones y tokens</h2>
      <div class="card">
        <div v-if="cargandoApp" class="p-6 text-center text-gray-400">Cargando…</div>
        <div v-else-if="aplicaciones.length === 0" class="p-6 text-center text-gray-400">No hay aplicaciones registradas.</div>
        <div v-else class="space-y-4">
          <div v-for="app in aplicaciones" :key="app.usuarioId" class="border border-gray-700 rounded-lg p-3">
            <div class="flex items-center justify-between mb-2">
              <div>
                <span class="text-white font-medium">{{ app.username }}</span>
                <span v-if="!app.isActive" class="ml-2 text-xs text-red-400">(inactiva)</span>
                <span v-if="app.email" class="ml-2 text-xs text-gray-500">{{ app.email }}</span>
              </div>
              <button @click="emitirToken(app)" class="btn text-xs">Emitir token</button>
            </div>
            <div v-if="app.tokens.length === 0" class="text-xs text-gray-500">Sin tokens.</div>
            <table v-else class="w-full text-xs">
              <thead class="text-left text-gray-500 border-b border-gray-700">
                <tr><th class="py-1 pr-3 font-medium">Token</th><th class="py-1 pr-3 font-medium">Etiqueta</th>
                  <th class="py-1 pr-3 font-medium">Último uso</th><th class="py-1 pr-3 font-medium">Estado</th>
                  <th class="py-1 font-medium text-right">Acciones</th></tr>
              </thead>
              <tbody>
                <tr v-for="t in app.tokens" :key="t.id" class="border-b border-gray-800">
                  <td class="py-1 pr-3 font-mono text-gray-300">{{ t.prefix }}…</td>
                  <td class="py-1 pr-3 text-gray-400">{{ t.label || '—' }}</td>
                  <td class="py-1 pr-3 text-gray-400">{{ t.lastUsedAt ? fecha(t.lastUsedAt) : 'nunca' }}</td>
                  <td class="py-1 pr-3">
                    <span v-if="t.activo" class="text-emerald-400">activo</span>
                    <span v-else-if="t.revokedAt" class="text-red-400">revocado</span>
                    <span v-else class="text-yellow-400">expirado</span>
                  </td>
                  <td class="py-1 text-right whitespace-nowrap">
                    <button v-if="t.activo" @click="rotarToken(app, t)" title="Rotar" class="p-1.5 rounded transition-colors text-blue-400 hover:text-blue-300 hover:bg-blue-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/></svg></button>
                    <button v-if="t.activo" @click="revocarToken(t)" title="Revocar" class="p-1.5 rounded transition-colors text-red-400 hover:text-red-300 hover:bg-red-900/30"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728A9 9 0 015.636 5.636"/></svg></button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </section>
  </div>
    <ConfirmDialog v-if="confirmar" :title="confirmar.title" :message="confirmar.message"
      :confirmText="confirmar.confirmText || 'Confirmar'" cancelText="Cancelar"
      @confirm="okConfirm" @cancel="cerrarConfirm" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import ConfirmDialog from '../components/ConfirmDialog.vue'
const confirmar = ref(null)
function okConfirm() { const f = confirmar.value?.onConfirm; confirmar.value = null; if (f) f() }
function cerrarConfirm() { confirmar.value = null }

import { useAuth } from '../composables/useAuth'
import {
  fetchSolicitudesIngreso, aprobarSolicitudIngreso, rechazarSolicitudIngreso,
  fetchRecursosPropuestos, aprobarRecurso, rechazarRecurso,
  fetchAplicacionesM2M, emitirTokenAplicacion, rotarTokenAplicacion, revocarTokenAplicacion,
} from '../api/graphql'

const { puede } = useAuth()

const solicitudes = ref([])
const recursos = ref([])
const aplicaciones = ref([])
const cargandoSol = ref(false)
const cargandoRec = ref(false)
const cargandoApp = ref(false)
const tokenEmitido = ref(null)

function fecha(s) {
  if (!s) return '—'
  try { return new Date(s).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' }) } catch { return s }
}
function copiar(t) { try { navigator.clipboard?.writeText(t) } catch { /* no-op */ } }

async function cargarSolicitudes() {
  if (!puede('aplicaciones.aprobar')) return
  cargandoSol.value = true
  try { const d = await fetchSolicitudesIngreso(true); solicitudes.value = d?.solicitudesIngreso || [] }
  finally { cargandoSol.value = false }
}
async function cargarRecursos() {
  if (!puede('recursos.aprobar')) return
  cargandoRec.value = true
  try { const d = await fetchRecursosPropuestos(); recursos.value = d?.recursosPropuestos || [] }
  finally { cargandoRec.value = false }
}

async function aprobarSol(s) {
  const d = await aprobarSolicitudIngreso(s.id)
  const r = d?.aprobarSolicitudIngreso
  if (r) tokenEmitido.value = { username: r.username, token: r.token }
  await cargarSolicitudes()
}
async function rechazarSol(s) {
  const motivo = window.prompt(`Motivo del rechazo de «${s.nombre}»:`, '')
  if (motivo === null) return
  await rechazarSolicitudIngreso(s.id, motivo || null)
  await cargarSolicitudes()
}
async function aprobarRec(r) {
  await aprobarRecurso(r.id)
  await cargarRecursos()
}
async function rechazarRec(r) {
  const motivo = window.prompt(`Motivo del rechazo de «${r.name}»:`, '')
  if (motivo === null) return
  await rechazarRecurso(r.id, motivo || null)
  await cargarRecursos()
}

async function cargarAplicaciones() {
  if (!puede('aplicaciones.aprobar')) return
  cargandoApp.value = true
  try { const d = await fetchAplicacionesM2M(); aplicaciones.value = d?.aplicacionesM2m || [] }
  finally { cargandoApp.value = false }
}

async function emitirToken(app) {
  const label = window.prompt(`Etiqueta del nuevo token para «${app.username}» (opcional):`, '')
  if (label === null) return
  const d = await emitirTokenAplicacion(app.usuarioId, label || null)
  const r = d?.emitirTokenAplicacion
  if (r) tokenEmitido.value = { username: app.username, token: r.token }
  await cargarAplicaciones()
}
async function rotarToken(app, tok) {
  confirmar.value = {
    title: 'Rotar token', confirmText: 'Rotar',
    message: `Rotar el token ${tok.prefix}… El token actual quedará revocado de inmediato.`,
    onConfirm: async () => { const d = await rotarTokenAplicacion(tok.id, tok.label || null); const r = d?.rotarTokenAplicacion; if (r) tokenEmitido.value = { username: app.username, token: r.token }; await cargarAplicaciones() },
  }
}
async function revocarToken(tok) {
  confirmar.value = {
    title: 'Revocar token', confirmText: 'Revocar',
    message: `Revocar el token ${tok.prefix}… Es inmediato e irreversible.`,
    onConfirm: async () => { await revocarTokenAplicacion(tok.id); await cargarAplicaciones() },
  }
}

onMounted(() => { cargarSolicitudes(); cargarRecursos(); cargarAplicaciones() })
</script>
