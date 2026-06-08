<template>
  <div v-if="total > 0" class="flex items-center justify-between gap-3 px-1 py-2 text-xs text-gray-400">
    <div class="flex items-center gap-2">
      <span>Filas:</span>
      <select :value="perPage" @change="$emit('update:perPage', Number($event.target.value)); $emit('update:page', 1)"
              class="bg-gray-800 border border-gray-700 rounded px-1.5 py-0.5 text-gray-200">
        <option v-for="n in opciones" :key="n" :value="n">{{ n }}</option>
      </select>
    </div>
    <div class="flex items-center gap-3">
      <span>{{ desde }}–{{ hasta }} de {{ total }}</span>
      <div class="flex items-center gap-1">
        <button @click="$emit('update:page', 1)" :disabled="page <= 1"
                class="px-1.5 py-0.5 rounded disabled:opacity-30 hover:bg-gray-700">«</button>
        <button @click="$emit('update:page', page - 1)" :disabled="page <= 1"
                class="px-1.5 py-0.5 rounded disabled:opacity-30 hover:bg-gray-700">‹</button>
        <span class="px-1">{{ page }} / {{ paginas }}</span>
        <button @click="$emit('update:page', page + 1)" :disabled="page >= paginas"
                class="px-1.5 py-0.5 rounded disabled:opacity-30 hover:bg-gray-700">›</button>
        <button @click="$emit('update:page', paginas)" :disabled="page >= paginas"
                class="px-1.5 py-0.5 rounded disabled:opacity-30 hover:bg-gray-700">»</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  total: { type: Number, required: true },
  page: { type: Number, required: true },
  perPage: { type: Number, default: 25 },
  opciones: { type: Array, default: () => [10, 25, 50, 100] },
})
defineEmits(['update:page', 'update:perPage'])
const paginas = computed(() => Math.max(1, Math.ceil(props.total / props.perPage)))
const desde = computed(() => props.total === 0 ? 0 : (props.page - 1) * props.perPage + 1)
const hasta = computed(() => Math.min(props.page * props.perPage, props.total))
</script>
