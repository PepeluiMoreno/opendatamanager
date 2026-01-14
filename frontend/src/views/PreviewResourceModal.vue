<template>
	<!-- Preview Resource Modal -->
	    <div
	      v-if="showPreviewModal"
	      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
	      @click.self="showPreviewModal = false"
	    >
	      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-6xl max-h-[90vh] overflow-y-auto">
	        <div class="flex justify-between items-center mb-4">
	          <h2 class="text-2xl font-bold">Test Result - {{ previewResource?.name }}</h2>
	          <button @click="showPreviewModal = false" class="text-gray-400 hover:text-white text-2xl">
	            ×
	          </button>
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
	
	          <!-- JSON view -->
	          <pre class="bg-gray-900 p-4 rounded text-xs overflow-x-auto text-green-400">{{ JSON.stringify(previewData, null, 2) }}</pre>
	        </div>
	
	        <div class="flex justify-end mt-4">
	          <button @click="showPreviewModal = false" class="btn btn-secondary">
	            Close
	          </button>
	        </div>
	      </div>
	    </div>
</template>

<script setup lang="ts">
defineProps<{
	previewResource: null;
	loadingPreview: boolean;
	previewError: null;
	previewData: null;
	getRecordCount: (data: any) => any;
}>()
const showPreviewModal = defineModel<boolean>('showPreviewModal', { required: true })
</script>
