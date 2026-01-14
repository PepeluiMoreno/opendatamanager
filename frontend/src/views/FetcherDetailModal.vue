<template>
	<!-- Fetcher Details Modal -->
	    <div
	      v-if="selectedfetcher"
	      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
	      @click.self="selectedfetcher = null"
	    >
	      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-3xl max-h-[90vh] overflow-y-auto">
	        <div class="flex items-start justify-between mb-6">
	          <div>
	            <h2 class="text-2xl font-bold text-blue-400">{{ selectedfetcher.code }}</h2>
	            <p class="text-sm text-gray-400 mt-1">{{ selectedfetcher.id }}</p>
	          </div>
	          <div class="flex items-center space-x-2">
	            <button @click="editfetcher(selectedfetcher)" class="btn btn-secondary text-sm">
	              Edit
	            </button>
	            <button @click="confirmDelete(selectedfetcher)" class="btn bg-red-800 hover:bg-red-700 text-sm">
	              Delete
	            </button>
	            <button @click="selectedfetcher = null" class="text-gray-400 hover:text-white text-2xl ml-2">
	              ×
	            </button>
	          </div>
	        </div>
</template>

<script setup lang="ts">
defineProps<{
	editfetcher: (fetcher: any) => void;
	confirmDelete: (fetcher: any) => void;
}>()
const selectedfetcher = defineModel<null>('selectedfetcher', { required: true })
</script>
