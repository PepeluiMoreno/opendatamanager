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
                  <button @click="aprobarSol(s)" class="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1">Aprobar</button>
                  <button @click="rechazarSol(s)" class="text-red-400 hover:text-red-300 text-xs px-2 py-1">Rechazar</button>
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
                  <button @click="aprobarRec(r)" class="text-emerald-400 hover:text-emerald-300 text-xs px-2 py-1">Aprobar</button>
                  <button @click="rechazarRec(r)" class="text-red-400 hover:text-red-300 text-xs px-2 py-1">Rechazar</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'
import {
  fetchSolicitudesIngreso, aprobarSolicitudIngreso, rechazarSolicitudIngreso,
  fetchRecursosPropuestos, aprobarRecurso, rechazarRecurso,
} from '../api/graphql'

const { puede } = useAuth()

const solicitudes = ref([])
const recursos = ref([])
const cargandoSol = ref(false)
const cargandoRec = ref(false)
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

onMounted(() => { cargarSolicitudes(); cargarRecursos() })
</script>
