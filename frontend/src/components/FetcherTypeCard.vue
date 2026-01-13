<template>
  <div class="card hover:border-blue-500 transition-all cursor-pointer" @click="$emit('select', Fetcher)">
    <div class="flex items-start justify-between mb-4">
      <div>
        <h3 class="text-xl font-bold text-blue-400">{{ Fetcher.code }}</h3>
        <div class="text-xs text-gray-500 mt-1">{{ Fetcher.id }}</div>
      </div>
      <span class="text-3xl">🔧</span>
    </div>

    <div class="space-y-3">
      <div>
        <span class="text-gray-400 text-sm font-medium">Class Path:</span>
        <code class="block mt-1 text-xs bg-gray-900 p-3 rounded text-green-400 break-all font-mono">
          {{ Fetcher.classPath }}
        </code>
      </div>

      <div v-if="Fetcher.description">
        <span class="text-gray-400 text-sm font-medium">Description:</span>
        <p class="mt-1 text-gray-300 text-sm leading-relaxed">
          {{ Fetcher.description }}
        </p>
      </div>

      <div v-if=" resourcesCount !== undefined" class="pt-3 border-t border-gray-700">
        <div class="flex items-center justify-between text-sm">
          <span class="text-gray-400">Active  Resources:</span>
          <span class="font-bold text-blue-400">{{  resourcesCount }}</span>
        </div>
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
   resourcesCount: {
    type: Number,
    default: undefined
  }
})

defineEmits(['select'])
</script>
