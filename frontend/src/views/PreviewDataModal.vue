<template>
  <div
    v-if="showPreviewModal"
    class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
    @click.self="showPreviewModal = false"
  >
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-6xl max-h-[90vh] overflow-y-auto">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold">Test Result - {{ previewResource?.name }}</h2>
        <button @click="showPreviewModal = false" class="text-gray-400 hover:text-white text-2xl">×</button>
      </div>

      <!-- External params inputs -->
      <div v-if="externalParams.length" class="mb-4 p-3 bg-gray-700 rounded-lg space-y-2">
        <p class="text-xs font-semibold text-yellow-300 mb-2">Runtime variables</p>
        <div v-for="param in externalParams" :key="param.key" class="flex items-center gap-3">
          <label class="text-xs text-gray-300 w-32 shrink-0 font-mono">{{ param.key }}</label>
          <input
            :value="previewParams[param.key]"
            @input="updateParam(param.key, $event.target.value)"
            type="text"
            :placeholder="param.value || `Enter ${param.key}...`"
            class="input flex-1 text-xs"
          />
        </div>
        <div class="flex justify-end pt-1">
          <button @click="onRunPreview" class="btn btn-primary text-xs py-1 px-3">Run with these values</button>
        </div>
      </div>

      <div v-if="loadingPreview" class="text-gray-400 text-center py-8">
        Testing resource... Fetching up to 100 records
      </div>

      <div v-else-if="previewError" class="p-4 bg-red-900 border border-red-700 rounded text-red-200 mb-4">
        {{ previewError }}
      </div>

      <div v-else-if="previewData">
        <div class="mb-4 text-sm text-gray-400">
          Showing first {{ getRecordCount(previewData) }} record(s)
        </div>
        <pre class="bg-gray-900 p-4 rounded text-xs overflow-x-auto text-green-400">{{ JSON.stringify(previewData, null, 2) }}</pre>
      </div>

      <div class="flex justify-end mt-4">
        <button @click="showPreviewModal = false" class="btn btn-secondary">Close</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  previewResource: { default: null },
  loadingPreview: { type: Boolean, default: false },
  previewError: { default: null },
  previewData: { default: null },
  getRecordCount: { type: Function, required: true },
  onRunPreview: { type: Function, default: () => {} },
})

const showPreviewModal = defineModel('showPreviewModal', { required: true })
const previewParams = defineModel('previewParams', { default: () => ({}) })

const externalParams = computed(() =>
  (props.previewResource?.params || []).filter(p => p.isExternal)
)

function updateParam(key, value) {
  previewParams.value = { ...previewParams.value, [key]: value }
}
</script>
