<template>
  <div>
    <!-- filtros (los aporta la vista) -->
    <slot name="filters" />

    <div v-if="items.length === 0" class="p-8 text-center text-gray-400">
      <slot name="empty">No hay registros.</slot>
    </div>

    <template v-else>
      <div class="overflow-x-auto" :class="scrollClass">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10 bg-gray-800">
            <tr class="text-left text-gray-400 border-b border-gray-700">
              <th v-if="selectable" class="py-3 px-3 w-8">
                <input type="checkbox" class="w-4 h-4 accent-blue-500 cursor-pointer"
                       :checked="allPageSelected" @change="togglePage" />
              </th>
              <slot name="columns" />
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in paged" :key="keyOf(item)"
                class="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors"
                :class="{ 'bg-blue-900/10': selectable && selected.has(keyOf(item)) }">
              <td v-if="selectable" class="py-3 px-3">
                <input type="checkbox" class="w-4 h-4 accent-blue-500 cursor-pointer"
                       :checked="selected.has(keyOf(item))" @change="toggleOne(item)" />
              </td>
              <slot name="cells" :item="item" />
            </tr>
          </tbody>
        </table>
      </div>

      <Paginator v-model:page="page" v-model:perPage="perPageRef" :total="total" />

      <!-- barra de acciones colectivas (patrón estándar: Acción… + Aplicar) -->
      <div v-if="selectable && selected.size > 0"
           class="flex items-center gap-2 mt-2 px-3 py-2 rounded-lg bg-blue-900/20 border border-blue-800">
        <span class="text-sm text-blue-200"><b>{{ selected.size }}</b> seleccionados</span>
        <select v-if="bulkActions.length" v-model="bulkAction" class="input text-xs py-1 px-2">
          <option value="">Acción…</option>
          <option v-for="a in bulkActions" :key="a.value" :value="a.value">{{ a.label }}</option>
        </select>
        <slot name="bulk-extra" :action="bulkAction" />
        <button @click="aplicar" :disabled="!bulkAction || busy"
                class="text-xs px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-40">
          {{ busy ? 'Aplicando…' : 'Aplicar' }}
        </button>
        <button @click="clearSelection" class="text-xs px-2 py-1.5 rounded border border-gray-600 text-gray-300 hover:bg-gray-700">Limpiar</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { usePagination } from '../composables/usePagination.js'
import Paginator from './Paginator.vue'

const props = defineProps({
  items: { type: Array, required: true },
  rowKey: { type: String, default: 'id' },
  perPage: { type: Number, default: 25 },
  selectable: { type: Boolean, default: true },
  bulkActions: { type: Array, default: () => [] },   // [{ value, label, danger }]
  scrollClass: { type: String, default: 'max-h-[calc(100vh-260px)] overflow-y-auto' },
})
const emit = defineEmits(['bulk'])

const itemsRef = computed(() => props.items)
const { page, perPage: perPageRef, total, paged } = usePagination(itemsRef, props.perPage)

function keyOf(item) { return item[props.rowKey] }

// selección
const selected = ref(new Set())
const busy = ref(false)
const bulkAction = ref('')
function clearSelection() { selected.value = new Set(); bulkAction.value = '' }
function toggleOne(item) { const k = keyOf(item); const s = new Set(selected.value); s.has(k) ? s.delete(k) : s.add(k); selected.value = s }
const allPageSelected = computed(() => paged.value.length > 0 && paged.value.every(i => selected.value.has(keyOf(i))))
function togglePage() { const s = new Set(selected.value); const on = !allPageSelected.value; paged.value.forEach(i => on ? s.add(keyOf(i)) : s.delete(keyOf(i))); selected.value = s }
const itemsSeleccionados = computed(() => props.items.filter(i => selected.value.has(keyOf(i))))

// si la lista cambia de tamaño (filtros), descartar selección obsoleta
watch(total, () => { const valid = new Set(props.items.map(keyOf)); selected.value = new Set([...selected.value].filter(k => valid.has(k))) })

function aplicar() {
  if (!bulkAction.value) return
  busy.value = true
  emit('bulk', {
    action: bulkAction.value,
    items: itemsSeleccionados.value,
    done: () => { busy.value = false; clearSelection() },
    cancel: () => { busy.value = false },
  })
}

defineExpose({ clearSelection })
</script>
