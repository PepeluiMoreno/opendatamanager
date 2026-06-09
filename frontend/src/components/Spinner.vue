<template>
  <div class="flex flex-col items-center justify-center gap-2 py-8 text-gray-400 text-sm">
    <span class="inline-block rounded-full border-2 border-gray-600 border-t-blue-400 animate-spin"
          :style="{ width: size + 'px', height: size + 'px' }"></span>
    <span v-if="text">{{ text }}</span>
  </div>
</template>

<script setup>
defineProps({
  text: { type: String, default: 'Loading…' },
  size: { type: Number, default: 24 },
})
</script>
