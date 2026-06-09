<template>
  <div class="flex items-center gap-2 flex-wrap mb-3">
    <slot />
    <button v-if="canClear" @click="$emit('clear')"
            class="text-xs text-yellow-400 hover:text-yellow-300 underline">Limpiar filtros</button>
    <span v-if="count !== null && count !== undefined" class="text-xs text-gray-500 ml-auto">
      {{ count }}<span v-if="total !== null && total !== undefined"> / {{ total }}</span>
    </span>
  </div>
</template>

<script setup>
defineProps({
  canClear: { type: Boolean, default: false },
  count: { type: [Number, String], default: null },
  total: { type: [Number, String], default: null },
})
defineEmits(['clear'])
</script>
