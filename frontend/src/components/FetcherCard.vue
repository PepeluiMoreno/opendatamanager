<template>
  <div class="card hover:border-blue-500 transition-all cursor-pointer" @click="$emit('select', Fetcher)">
    <div class="flex items-start justify-between mb-3">
      <h3 class="text-lg font-bold text-blue-400 leading-snug">{{ Fetcher.name || Fetcher.code }}</h3>
      <span class="text-2xl ml-3 shrink-0">🔧</span>
    </div>

    <p v-if="Fetcher.description" class="text-sm text-gray-400 leading-relaxed mb-3">
      {{ Fetcher.description }}
    </p>

    <div v-if="sourcesCount !== undefined" class="pt-3 border-t border-gray-700">
      <div class="flex items-center justify-between text-sm">
        <span class="text-gray-400">Active Sources:</span>
        <span class="font-bold text-blue-400">{{ sourcesCount }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  Fetcher: {
    type: Object,
    required: true
  },
  sourcesCount: {
    type: Number,
    default: undefined
  }
})

defineEmits(['select'])
</script>