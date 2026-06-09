<template>
  <div class="p-6 space-y-6" style="min-height:100%">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Collections</h1>
      </div>
    </div>

    <!-- Filtro (son recursos de recursos) -->
    <div class="flex items-center gap-3 flex-wrap">
      <input v-model="search" type="text" placeholder="Buscar por nombre o publisher…" class="flex-1 min-w-48 bg-gray-700 border border-gray-600 rounded-md px-3 py-1.5 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"/>
      <select v-model="tipoFilter" class="bg-gray-700 border border-gray-600 rounded-md px-2 py-1.5 text-sm text-white focus:outline-none focus:border-blue-500">
        <option value="">Tipo: todos</option>
        <option v-for="t in tiposDisponibles" :key="t" :value="t">{{ t }}</option>
      </select>
      <button v-if="search || tipoFilter" @click="search='';tipoFilter=''" class="text-xs text-yellow-400 hover:text-yellow-300 underline">Limpiar filtros</button>
      <span class="text-xs text-gray-500 ml-auto">{{ filtered.length }} / {{ colecciones.length }}</span>
    </div>

    <!-- Tabla -->
    <div class="card">
      <div v-if="cargando" class="p-8"><Spinner /></div>
      <div v-else-if="filtered.length === 0" class="p-8 text-center text-gray-400">
        <template v-if="colecciones.length === 0">Aún no hay colecciones. Un recurso se vuelve Colección cuando su especie declara el modo «descubrir» (hoy, Web Tree).</template>
        <template v-else>Sin resultados. <button @click="search='';tipoFilter=''" class="text-yellow-400 hover:text-yellow-300 underline">Limpiar filtros</button></template>
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
import { ref, computed, onMounted } from 'vue'
import { fetchCollections } from '../api/graphql.js'
import { usePagination } from '../composables/usePagination.js'
import Paginator from '../components/Paginator.vue'
import Spinner from '../components/Spinner.vue'

const colecciones = ref([])
const cargando = ref(true)
const search = ref('')
const tipoFilter = ref('')
const tiposDisponibles = computed(() => [...new Set(colecciones.value.map(c => c.fetcher?.code).filter(Boolean))].sort())
const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return colecciones.value.filter(c => {
    if (tipoFilter.value && c.fetcher?.code !== tipoFilter.value) return false
    if (q) {
      const pub = c.publisherObj?.acronimo || c.publisherObj?.nombre || c.publisher || ''
      if (!(`${c.name||''} ${pub}`.toLowerCase().includes(q))) return false
    }
    return true
  })
})
const { page, perPage, total, paged } = usePagination(filtered, 25)

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
