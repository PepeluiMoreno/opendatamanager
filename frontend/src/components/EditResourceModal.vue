<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
      <div class="flex items-start justify-between mb-6">
        <div>
          <h2 class="text-2xl font-bold text-blue-400">{{ Fetcher.name }}</h2>
          <p class="text-sm text-gray-400 mt-1">{{ Fetcher.id }}</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-white text-2xl">
          ×
        </button>
      </div>

      <!-- Resource Type Info -->
      <div class="mb-6 p-4 bg-gray-700 rounded">
        <h3 class="font-semibold mb-2">Fetcher Information</h3>
        <div class="grid grid-cols-1 gap-4 text-sm">
          <div>
            <span class="text-gray-400">Name:</span>
            <span class="ml-2">{{ Fetcher.name }}</span>
          </div>
          <div>
            <span class="text-gray-400">Description:</span>
            <span class="ml-2">{{ Fetcher.description || 'No description' }}</span>
          </div>
        </div>
      </div>

      <!-- Variante: bloque preset_params fijado sobre la especie -->
      <div v-if="presetEntries.length" class="mb-6 p-4 bg-purple-950 bg-opacity-30 border border-purple-800 rounded">
        <h3 class="text-sm font-semibold uppercase tracking-wide text-purple-300 mb-2">
          Variante — parámetros fijados (preset)
        </h3>
        <p class="text-xs text-gray-400 mb-3">
          Estos valores los aporta la variante sobre su especie ({{ Fetcher.classPath }});
          los recursos solo configuran el resto.
        </p>
        <table class="text-xs w-full">
          <tbody>
            <tr v-for="[k, v] in presetEntries" :key="k" class="border-t border-purple-900 align-top">
              <td class="py-1 pr-3 font-mono text-purple-300 whitespace-nowrap">{{ k }}</td>
              <td class="py-1 text-gray-300 font-mono break-all">{{ typeof v === 'object' ? JSON.stringify(v) : v }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Parameters List: agrupados por categoría de variación -->
      <div v-if="Fetcher.paramsDef && Fetcher.paramsDef.length > 0">
        <h3 class="text-xl font-semibold mb-4">Parameters</h3>
        <div v-for="grp in groupedParams" :key="grp.key" class="mb-6">
          <h4 class="text-sm font-semibold uppercase tracking-wide text-blue-300 border-b border-gray-600 pb-1 mb-3">
            {{ grp.label }}
            <span class="ml-2 text-xs font-normal text-gray-500">{{ grp.params.length }}</span>
          </h4>
          <div class="space-y-2">
            <div
              v-for="param in grp.params"
              :key="param.id"
              class="border rounded p-3"
              :class="param.required ? 'border-red-700 bg-red-950 bg-opacity-20' : 'border-gray-600 bg-gray-700 bg-opacity-30'"
            >
              <div class="flex items-center space-x-3 mb-1">
                <h5 class="font-semibold">{{ param.paramName }}</h5>
                <span v-if="param.required" class="text-xs bg-red-600 px-2 py-0.5 rounded">Required</span>
                <span class="text-xs bg-gray-600 px-2 py-0.5 rounded">{{ param.dataType }}</span>
                <span v-if="presetMap[param.paramName] !== undefined"
                      class="text-xs bg-purple-900 text-purple-300 px-2 py-0.5 rounded"
                      :title="'Fijado por la variante: ' + presetMap[param.paramName]">preset</span>
                <span v-if="param.defaultValue !== null && param.defaultValue !== undefined" class="text-xs text-gray-400">
                  default: {{ param.defaultValue }}
                </span>
              </div>
              <p v-if="param.hint || param.description" class="text-sm text-gray-300">
                {{ param.hint || param.description }}
              </p>
              <p v-if="param.visibleWhen && param.visibleWhen.param" class="text-xs text-gray-500 mt-1">
                Visible cuando {{ param.visibleWhen.param }} ∈ [{{ (param.visibleWhen.in || [param.visibleWhen.equals]).join(', ') }}]
              </p>
              <table v-if="enumOptions(param).length" class="mt-2 text-xs w-full">
                <tbody>
                  <tr v-for="opt in enumOptions(param)" :key="opt.value" class="border-t border-gray-700 align-top">
                    <td class="py-1 pr-3 font-mono text-blue-300 whitespace-nowrap">{{ opt.value }}</td>
                    <td class="py-1 text-gray-300">
                      {{ opt.label }}
                      <span v-if="opt.help" class="block text-gray-500">{{ opt.help }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>

      <!-- No parameters at all -->
      <div v-else class="text-center py-8 text-gray-400">
        This resource type has no parameters configured
      </div>

      <!-- Resources Using This Fetcher -->
      <div v-if="Fetcher.resources && Fetcher.resources.length > 0" class="mt-6 pt-6 border-t border-gray-600">
        <h4 class="text-lg font-medium mb-3">Resources Using This Fetcher</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <router-link
            v-for="resource in Fetcher.resources"
            :key="resource.id"
            :to="`/resources/${resource.id}`"
            class="p-3 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
          >
            <div class="font-medium">{{ resource.name }}</div>
            <div class="text-sm text-gray-400">{{ resource.publisher }}</div>
            <div class="text-xs text-gray-500 mt-1">
              {{ resource.active ? 'Active' : 'Inactive' }}
            </div>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  Fetcher: {
    type: Object,
    required: true
  }
})

defineEmits(['close'])

// Agrupación por categoría de variación (mismo vocabulario que FetcherParamsForm)
const GROUP_LABELS = {
  http: 'HTTP', peticion: 'Petición (qué se envía)', navegacion: 'Navegación',
  paginacion: 'Paginación', extraccion: 'Extracción de resultados',
  descubrimiento: 'Descubrimiento', envio_busqueda: 'Envío de la búsqueda',
  behavior: 'Comportamiento', format: 'Formato', excel: 'Excel',
}
const GROUP_ORDER = ['http', 'descubrimiento', 'envio_busqueda', 'peticion', 'navegacion', 'paginacion', 'extraccion', 'format', 'excel', 'behavior']

const groupedParams = computed(() => {
  const byGroup = {}
  for (const p of props.Fetcher.paramsDef || []) {
    const k = p.group || ''
    ;(byGroup[k] = byGroup[k] || []).push(p)
  }
  const keys = Object.keys(byGroup).sort((a, b) => {
    const ia = GROUP_ORDER.indexOf(a), ib = GROUP_ORDER.indexOf(b)
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib)
  })
  return keys.map(k => ({
    key: k,
    label: GROUP_LABELS[k] || (k ? k.charAt(0).toUpperCase() + k.slice(1) : 'General'),
    params: byGroup[k],
  }))
})

const presetMap = computed(() => props.Fetcher.presetParams || {})
const presetEntries = computed(() => Object.entries(presetMap.value))

function enumOptions(param) {
  if (!Array.isArray(param.enumValues) || !param.enumValues.length) return []
  return param.enumValues.map(v =>
    typeof v === 'object' && v !== null
      ? { value: v.value, label: v.label || v.value, help: v.help || '' }
      : { value: v, label: String(v), help: '' }
  )
}
</script>