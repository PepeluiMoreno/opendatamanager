<template>
  <div class="space-y-6">
    <!-- Secciones por grupo -->
    <div v-for="grp in groupedParams" :key="grp.key" class="space-y-3">
      <h4 class="text-sm font-semibold uppercase tracking-wide text-blue-300 border-b border-gray-700 pb-1">
        {{ grp.label }}
      </h4>

      <div
        v-for="param in grp.params"
        :key="param.id || param.paramName"
        class="bg-gray-800/60 rounded-lg p-3"
      >
        <!-- Cabecera del campo: nombre + tipo + tip + ayuda -->
        <div class="flex items-center gap-2 mb-1">
          <label :for="param.paramName" class="font-medium text-gray-100">
            {{ labelFor(param) }}
          </label>
          <span v-if="param.required" class="text-red-400 text-xs">*</span>
          <span class="text-xs bg-gray-600 px-2 py-0.5 rounded">{{ param.dataType }}</span>

          <!-- Tip (tooltip corto) -->
          <Tooltip v-if="tipFor(param)" :text="tipFor(param)" />

          <!-- Botón de ayuda extensa (modal) -->
          <button
            v-if="hasHelp(param)"
            type="button"
            class="ml-auto text-xs text-blue-400 hover:text-blue-300 underline"
            @click="helpParam = param"
          >
            Más info
          </button>
        </div>

        <!-- Hint inline -->
        <p v-if="param.hint" class="text-xs text-gray-400 mb-2">{{ param.hint }}</p>

        <!-- Control según tipo -->
        <!-- enum -->
        <select
          v-if="isEnum(param)"
          :id="param.paramName"
          class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
          :value="value(param.paramName)"
          @change="set(param.paramName, $event.target.value)"
        >
          <option v-for="opt in enumOptions(param)" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </option>
        </select>

        <!-- boolean -->
        <label v-else-if="param.dataType === 'boolean'" class="inline-flex items-center gap-2 cursor-pointer">
          <input
            type="checkbox"
            class="rounded bg-gray-900 border-gray-700"
            :checked="!!value(param.paramName)"
            @change="set(param.paramName, $event.target.checked)"
          />
          <span class="text-sm text-gray-300">{{ value(param.paramName) ? 'Sí' : 'No' }}</span>
        </label>

        <!-- json -->
        <textarea
          v-else-if="param.dataType === 'json'"
          :id="param.paramName"
          rows="3"
          class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm font-mono"
          :value="value(param.paramName)"
          @input="set(param.paramName, $event.target.value)"
          placeholder='{ "clave": "valor" }'
        ></textarea>

        <!-- número -->
        <input
          v-else-if="param.dataType === 'integer' || param.dataType === 'number'"
          :id="param.paramName"
          type="number"
          :step="param.dataType === 'integer' ? 1 : 'any'"
          class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
          :value="value(param.paramName)"
          @input="set(param.paramName, $event.target.value)"
        />

        <!-- string (por defecto) -->
        <input
          v-else
          :id="param.paramName"
          type="text"
          class="w-full bg-gray-900 border border-gray-700 rounded px-3 py-2 text-sm"
          :value="value(param.paramName)"
          @input="set(param.paramName, $event.target.value)"
        />
      </div>
    </div>

    <!-- Modal de ayuda extensa -->
    <div
      v-if="helpParam"
      class="fixed inset-0 z-[10000] flex items-center justify-center bg-black/60 p-4"
      @click.self="helpParam = null"
    >
      <div class="bg-gray-900 border border-gray-700 rounded-xl max-w-lg w-full p-5 shadow-2xl">
        <div class="flex items-center justify-between mb-3">
          <h3 class="text-lg font-semibold text-gray-100">{{ labelFor(helpParam) }}</h3>
          <button class="text-gray-400 hover:text-white" @click="helpParam = null">✕</button>
        </div>

        <p v-if="helpParam.helpMd" class="text-sm text-gray-300 whitespace-pre-line mb-4">{{ helpParam.helpMd }}</p>
        <p v-else-if="helpParam.description" class="text-sm text-gray-300 mb-4">{{ helpParam.description }}</p>

        <!-- Tabla de valores posibles (enum enriquecido) -->
        <div v-if="isEnum(helpParam)" class="mt-2">
          <h4 class="text-xs font-semibold uppercase text-blue-300 mb-2">Valores posibles</h4>
          <table class="w-full text-sm">
            <tbody>
              <tr v-for="opt in enumOptions(helpParam)" :key="opt.value" class="border-t border-gray-800 align-top">
                <td class="py-2 pr-3 font-mono text-blue-200 whitespace-nowrap">{{ opt.value }}</td>
                <td class="py-2 text-gray-300">
                  <span class="font-medium">{{ opt.label }}</span>
                  <span v-if="opt.help" class="block text-gray-400">{{ opt.help }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import Tooltip from './Tooltip.vue'

const props = defineProps({
  // Esquema del fetcher: lista de FetcherParam (paramName, dataType, group,
  // required, defaultValue, enumValues, description, hint, helpMd, visibleWhen)
  paramsDef: { type: Array, default: () => [] },
  // Objeto { paramName: valor } con la configuración actual del recurso
  modelValue: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

const helpParam = ref(null)

// Etiquetas legibles para los grupos conocidos (fallback: capitaliza el código)
const GROUP_LABELS = {
  descubrimiento: 'Descubrimiento',
  envio_busqueda: 'Envío de la búsqueda',
  extraccion: 'Extracción de resultados',
  paginacion: 'Paginación',
  http: 'HTTP',
  peticion: 'Petición (qué se envía)',
  navegacion: 'Navegación',
  format: 'Formato',
  excel: 'Excel',
  pagination: 'Paginación',
  navigation: 'Navegación',
  behavior: 'Comportamiento',
}
const GROUP_ORDER = ['http', 'descubrimiento', 'envio_busqueda', 'peticion', 'navegacion', 'paginacion', 'extraccion', 'format', 'excel', 'behavior']

function groupLabel(key) {
  if (GROUP_LABELS[key]) return GROUP_LABELS[key]
  if (!key) return 'General'
  return key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')
}

function value(name) {
  if (props.modelValue[name] !== undefined && props.modelValue[name] !== null) return props.modelValue[name]
  const def = props.paramsDef.find(p => p.paramName === name)
  return def && def.defaultValue !== undefined && def.defaultValue !== null ? def.defaultValue : ''
}

function set(name, val) {
  emit('update:modelValue', { ...props.modelValue, [name]: val })
}

// ── Visibilidad condicional (visible_when) ──────────────────────────────
function isVisible(param) {
  const cond = param.visibleWhen
  if (!cond || !cond.param) return true
  const current = value(cond.param)
  if (Array.isArray(cond.in)) return cond.in.includes(current)
  if (cond.equals !== undefined) return current === cond.equals
  return true
}

// ── Agrupación ──────────────────────────────────────────────────────────
const groupedParams = computed(() => {
  const visible = props.paramsDef.filter(isVisible)
  const byGroup = {}
  for (const p of visible) {
    const k = p.group || ''
    ;(byGroup[k] = byGroup[k] || []).push(p)
  }
  const keys = Object.keys(byGroup).sort((a, b) => {
    const ia = GROUP_ORDER.indexOf(a), ib = GROUP_ORDER.indexOf(b)
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib)
  })
  return keys.map(k => ({ key: k, label: groupLabel(k), params: byGroup[k] }))
})

// ── Enums (admite strings o {value,label,help}) ─────────────────────────
function isEnum(param) {
  return Array.isArray(param.enumValues) && param.enumValues.length > 0
}
function enumOptions(param) {
  return (param.enumValues || []).map(v =>
    typeof v === 'object' && v !== null
      ? { value: v.value, label: v.label || v.value, help: v.help || '' }
      : { value: v, label: String(v), help: '' }
  )
}

// ── Ayuda ────────────────────────────────────────────────────────────────
function labelFor(param) {
  return param.paramName
}
function tipFor(param) {
  // El tooltip corto resume; si no hay hint, usa description recortada
  return param.hint || param.description || ''
}
function hasHelp(param) {
  return !!(param.helpMd || param.description || isEnum(param))
}
</script>
