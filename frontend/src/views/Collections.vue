<template>
  <div class="p-6 max-w-6xl mx-auto">
    <div class="mb-6">
      <h1 class="text-2xl font-bold text-gray-100">🛰️ Collections</h1>
      <p class="text-sm text-gray-400 mt-1">
        Naves nodriza: recursos que <strong>descubren</strong> otros recursos. Cada
        Colección rastrea su fuente (proceso de <em>discovering</em>), propone
        <strong>candidatos</strong> y, al promoverlos, gana <strong>miembros</strong>.
      </p>
    </div>

    <div v-if="cargando" class="text-gray-400 text-sm py-12 text-center">Cargando colecciones…</div>

    <div v-else-if="colecciones.length === 0" class="text-gray-500 text-sm py-12 text-center">
      Aún no hay colecciones. Un recurso se vuelve Colección cuando su especie
      declara el modo «descubrir» (hoy, Web Tree).
    </div>

    <div v-else class="overflow-x-auto rounded-lg border border-gray-700">
      <table class="min-w-full text-sm">
        <thead class="bg-gray-800 text-gray-300">
          <tr>
            <th class="text-left px-4 py-2 font-medium">Colección</th>
            <th class="text-left px-4 py-2 font-medium">Publisher</th>
            <th class="text-right px-4 py-2 font-medium">Candidatos pendientes</th>
            <th class="text-right px-4 py-2 font-medium">Miembros</th>
            <th class="text-left px-4 py-2 font-medium">Último rastreo</th>
            <th class="text-right px-4 py-2 font-medium">Acciones</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700">
          <tr v-for="c in colecciones" :key="c.id" class="hover:bg-gray-800/50">
            <td class="px-4 py-3">
              <div class="font-medium text-gray-100">{{ c.name }}</div>
              <div class="text-xs text-gray-500">{{ c.fetcher?.code }}</div>
            </td>
            <td class="px-4 py-3 text-gray-300">{{ c.publisherObj?.acronimo || c.publisher || '—' }}</td>
            <td class="px-4 py-3 text-right">
              <span :class="c.candidatosPendientes > 0 ? 'text-yellow-400 font-semibold' : 'text-gray-500'">
                {{ c.candidatosPendientes }}
              </span>
            </td>
            <td class="px-4 py-3 text-right text-gray-300">{{ c.miembros }}</td>
            <td class="px-4 py-3 text-gray-400">{{ formatoFecha(c.ultimoDescubrimiento) }}</td>
            <td class="px-4 py-3 text-right whitespace-nowrap">
              <router-link
                :to="`/resources/${c.id}/candidates`"
                class="text-blue-400 hover:text-blue-300 text-xs font-medium mr-3">
                Ver candidatos →
              </router-link>
              <router-link
                :to="`/resources/${c.id}/test`"
                class="text-gray-400 hover:text-gray-200 text-xs">
                Abrir
              </router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchCollections } from '../api/graphql.js'

const colecciones = ref([])
const cargando = ref(true)

function formatoFecha(iso) {
  if (!iso) return 'Nunca'
  try {
    return new Date(iso).toLocaleString('es-ES', { dateStyle: 'medium', timeStyle: 'short' })
  } catch {
    return iso
  }
}

async function cargar() {
  cargando.value = true
  try {
    const data = await fetchCollections()
    colecciones.value = data?.collections || []
  } finally {
    cargando.value = false
  }
}

onMounted(cargar)
</script>
