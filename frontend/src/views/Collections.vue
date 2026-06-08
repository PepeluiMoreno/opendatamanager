<template>
  <div class="p-6 space-y-6" style="min-height:100%">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Collections</h1>
        <p class="text-gray-400 text-sm mt-1">
          Naves nodriza: recursos que <strong>descubren</strong> otros recursos. Cada
          Colección rastrea su fuente (proceso de <em>discovering</em>), propone
          <strong>candidatos</strong> y, al promoverlos, gana <strong>miembros</strong>.
        </p>
      </div>
    </div>

    <!-- Tabla -->
    <div class="card">
      <div v-if="cargando" class="p-8 text-center text-gray-400">Cargando colecciones…</div>
      <div v-else-if="colecciones.length === 0" class="p-8 text-center text-gray-400">
        Aún no hay colecciones. Un recurso se vuelve Colección cuando su especie
        declara el modo «descubrir» (hoy, Web Tree).
      </div>
      <div v-else class="overflow-x-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10 bg-gray-800">
            <tr class="text-left text-gray-400 border-b border-gray-700">
              <th class="py-3 px-4 font-medium">Colección</th>
              <th class="py-3 px-4 font-medium">Publisher</th>
              <th class="py-3 px-4 font-medium text-right">Candidatos pendientes</th>
              <th class="py-3 px-4 font-medium text-right">Miembros</th>
              <th class="py-3 px-4 font-medium">Último rastreo</th>
              <th class="py-3 px-4 font-medium text-right">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in paged" :key="c.id"
                class="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
              <td class="py-3 px-4">
                <div class="text-white font-medium">{{ c.name }}</div>
                <div class="text-xs text-gray-500">{{ c.fetcher?.code }}</div>
              </td>
              <td class="py-3 px-4 text-gray-300">{{ c.publisherObj?.acronimo || c.publisher || '—' }}</td>
              <td class="py-3 px-4 text-right">
                <span :class="c.candidatosPendientes > 0 ? 'text-yellow-400 font-semibold' : 'text-gray-500'">
                  {{ c.candidatosPendientes }}
                </span>
              </td>
              <td class="py-3 px-4 text-right text-gray-300">{{ c.miembros }}</td>
              <td class="py-3 px-4 text-gray-400">{{ formatoFecha(c.ultimoDescubrimiento) }}</td>
              <td class="py-3 px-4">
                <div class="flex gap-2 justify-end whitespace-nowrap">
                  <router-link
                    :to="`/resources/${c.id}/candidates`"
                    class="text-blue-400 hover:text-blue-300 text-xs px-2 py-1 rounded hover:bg-blue-900/30">
                    Ver candidatos →
                  </router-link>
                  <router-link
                    :to="`/resources/${c.id}/test`"
                    class="text-gray-400 hover:text-gray-200 text-xs px-2 py-1 rounded hover:bg-gray-700/50">
                    Abrir
                  </router-link>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <Paginator v-if="!cargando" v-model:page="page" v-model:perPage="perPage" :total="total" />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchCollections } from '../api/graphql.js'
import { usePagination } from '../composables/usePagination.js'
import Paginator from '../components/Paginator.vue'

const colecciones = ref([])
const cargando = ref(true)
const { page, perPage, total, paged } = usePagination(colecciones, 25)

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
