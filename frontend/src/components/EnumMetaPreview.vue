<template>
  <div v-if="filters && Object.keys(filters).length"
       class="mt-1.5 flex flex-wrap gap-1">
    <span
      v-for="(vals, key) in filters"
      :key="key"
      class="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-xs bg-gray-800 border border-gray-600 font-mono"
      :title="`${key} = ${formatVals(vals)}`"
    >
      <span class="text-blue-400">{{ key }}</span>
      <span class="text-gray-500">=</span>
      <span class="text-green-400 max-w-[14ch] truncate">{{ formatVals(vals) }}</span>
    </span>
  </div>
</template>

<script setup>
defineProps({
  filters: { type: Object, default: null },
})

function formatVals(vals) {
  if (!vals || vals.length === 0) return '*'
  if (vals.length === 1) return vals[0]
  return vals.join(' | ')
}
</script>
