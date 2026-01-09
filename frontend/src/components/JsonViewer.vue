<template>
  <div class="json-viewer">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-lg font-bold">{{ title }}</h3>
      <div class="space-x-2">
        <button @click="copyToClipboard" class="btn btn-secondary text-xs py-1 px-3">
          {{ copied ? 'Copied!' : 'Copy' }}
        </button>
        <button @click="toggleExpand" class="btn btn-secondary text-xs py-1 px-3">
          {{ expanded ? 'Collapse' : 'Expand' }}
        </button>
      </div>
    </div>

    <div
      class="bg-gray-900 rounded overflow-auto border border-gray-700"
      :class="maxHeight"
    >
      <pre class="p-4 text-sm"><code :class="{ 'line-clamp-10': !expanded }">{{ formattedJson }}</code></pre>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  data: {
    type: [Object, Array, String],
    required: true
  },
  title: {
    type: String,
    default: 'JSON Data'
  },
  maxHeight: {
    type: String,
    default: 'max-h-96'
  }
})

const expanded = ref(false)
const copied = ref(false)

const formattedJson = computed(() => {
  if (typeof props.data === 'string') {
    try {
      return JSON.stringify(JSON.parse(props.data), null, 2)
    } catch {
      return props.data
    }
  }
  return JSON.stringify(props.data, null, 2)
})

function toggleExpand() {
  expanded.value = !expanded.value
}

async function copyToClipboard() {
  try {
    await navigator.clipboard.writeText(formattedJson.value)
    copied.value = true
    setTimeout(() => {
      copied.value = false
    }, 2000)
  } catch (err) {
    console.error('Failed to copy:', err)
  }
}
</script>

<style scoped>
.line-clamp-10 {
  display: -webkit-box;
  -webkit-line-clamp: 10;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>
