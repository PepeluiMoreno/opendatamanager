<template>
  <span class="relative inline-flex group align-middle ml-1">
    <span class="inline-flex items-center justify-center w-4 h-4 rounded-full border border-gray-500 text-gray-400 text-[10px] leading-none cursor-help select-none">?</span>
    <span class="pointer-events-none absolute left-1/2 -translate-x-1/2 bottom-full mb-1.5 w-64 z-[70] hidden group-hover:block bg-gray-900 border border-gray-600 text-gray-200 text-xs rounded-lg px-3 py-2 shadow-xl whitespace-normal text-left font-normal normal-case leading-snug">
      {{ text }}
    </span>
  </span>
</template>

<script setup>
defineProps({ text: { type: String, required: true } })
</script>
