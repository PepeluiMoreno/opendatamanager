<template>
  <div class="space-y-2">
    <!-- Filtros activos -->
    <div v-for="(entry, idx) in activeFilters" :key="entry.key"
         class="border border-gray-600 rounded p-2 bg-gray-900 space-y-1.5">
      <!-- Cabecera de categoría -->
      <div class="flex items-center justify-between">
        <span class="text-xs font-semibold text-blue-400 font-mono">{{ entry.key }}</span>
        <button type="button" @click="removeCategory(idx)"
                class="text-gray-500 hover:text-red-400 text-xs leading-none">✕</button>
      </div>
      <!-- Opción "cualquier valor" -->
      <label class="flex items-center gap-1.5 text-xs text-gray-400 cursor-pointer">
        <input type="checkbox"
               :checked="entry.values.length === 0"
               @change="toggleAny(idx, $event.target.checked)"
               class="w-3 h-3 accent-blue-500" />
        <span class="italic">cualquier valor</span>
      </label>
      <!-- Checkboxes de valores -->
      <div v-if="entry.values.length > 0 || !allEnumValues(entry.key)"
           class="grid grid-cols-2 gap-x-3 gap-y-0.5 max-h-32 overflow-y-auto pl-1">
        <label
          v-for="val in enumValues[entry.key] || []"
          :key="val"
          class="flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer truncate"
        >
          <input type="checkbox"
                 :checked="entry.values.includes(val)"
                 @change="toggleValue(idx, val, $event.target.checked)"
                 class="w-3 h-3 flex-shrink-0 accent-blue-500" />
          <span class="truncate">{{ val }}</span>
        </label>
      </div>
    </div>

    <!-- Añadir categoría -->
    <select
      v-if="availableCategories.length > 0"
      @change="addCategory($event.target.value); $event.target.value = ''"
      class="w-full px-2 py-1 text-xs bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 text-gray-400"
    >
      <option value="">+ Añadir filtro OSM...</option>
      <option v-for="cat in availableCategories" :key="cat" :value="cat">{{ cat }}</option>
    </select>

    <!-- Preview JSON compacto -->
    <div v-if="activeFilters.length > 0"
         class="text-xs font-mono text-gray-500 bg-gray-950 rounded px-2 py-1 truncate"
         :title="jsonPreview">
      {{ jsonPreview }}
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '{}' },
  // enumValues: { amenity: [...], building: [...], shop: [...], ... }
  enumValues: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

// Parse the incoming JSON string into a list of {key, values[]} entries
function parseValue(raw) {
  try {
    const obj = typeof raw === 'string' ? JSON.parse(raw || '{}') : (raw || {})
    return Object.entries(obj).map(([key, vals]) => ({
      key,
      values: Array.isArray(vals) ? vals : [],
    }))
  } catch {
    return []
  }
}

const activeFilters = ref(parseValue(props.modelValue))

// When parent updates modelValue from outside, sync (avoid loop)
watch(() => props.modelValue, (v) => {
  const parsed = parseValue(v)
  if (JSON.stringify(parsed) !== JSON.stringify(activeFilters.value)) {
    activeFilters.value = parsed
  }
})

const availableCategories = computed(() => {
  const used = new Set(activeFilters.value.map(e => e.key))
  return Object.keys(props.enumValues).filter(k => !used.has(k))
})

const jsonPreview = computed(() => {
  const obj = {}
  for (const e of activeFilters.value) {
    obj[e.key] = e.values.length > 0 ? e.values : null
  }
  return JSON.stringify(obj)
})

function emit_change() {
  emit('update:modelValue', jsonPreview.value)
}

function allEnumValues(key) {
  return props.enumValues[key] && props.enumValues[key].length > 0
}

function addCategory(key) {
  if (!key || activeFilters.value.find(e => e.key === key)) return
  activeFilters.value.push({ key, values: [] })
  emit_change()
}

function removeCategory(idx) {
  activeFilters.value.splice(idx, 1)
  emit_change()
}

function toggleAny(idx, checked) {
  if (checked) {
    activeFilters.value[idx].values = []
  } else {
    // If unchecking "any", pre-select first value to avoid empty state
    const available = props.enumValues[activeFilters.value[idx].key] || []
    activeFilters.value[idx].values = available.length ? [available[0]] : []
  }
  emit_change()
}

function toggleValue(idx, val, checked) {
  const entry = activeFilters.value[idx]
  if (checked) {
    if (!entry.values.includes(val)) entry.values.push(val)
  } else {
    entry.values = entry.values.filter(v => v !== val)
  }
  emit_change()
}
</script>
