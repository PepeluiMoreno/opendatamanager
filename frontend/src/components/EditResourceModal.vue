<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
      <div class="flex items-start justify-between mb-6">
        <div>
          <h2 class="text-2xl font-bold text-blue-400">{{ Fetcher.name }}</h2>
          <p class="text-sm text-gray-400 mt-1">{{ Fetcher.id }}</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-white text-2xl">
          ×
        </button>
      </div>

      <!-- Resource Type Info -->
      <div class="mb-6 p-4 bg-gray-700 rounded">
        <h3 class="font-semibold mb-2">Fetcher Information</h3>
        <div class="grid grid-cols-1 gap-4 text-sm">
          <div>
            <span class="text-gray-400">Name:</span>
            <span class="ml-2">{{ Fetcher.name }}</span>
          </div>
          <div>
            <span class="text-gray-400">Description:</span>
            <span class="ml-2">{{ Fetcher.description || 'No description' }}</span>
          </div>
        </div>
      </div>

      <!-- Parameters List -->
      <div v-if="Fetcher.paramsDef && Fetcher.paramsDef.length > 0">
        <h3 class="text-xl font-semibold mb-4">Parameters</h3>
        
        <!-- Required Parameters -->
        <div v-if="requiredParams.length > 0" class="mb-6">
          <h4 class="text-lg font-medium mb-3 text-red-400 flex items-center">
            Required Parameters
            <span class="ml-2 text-xs bg-red-900 px-2 py-1 rounded">{{ requiredParams.length }}</span>
          </h4>
          <div class="space-y-3">
            <div
              v-for="param in requiredParams"
              :key="param.id"
              class="border border-red-600 rounded p-4 bg-red-950 bg-opacity-20"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center space-x-3 mb-2">
                    <h5 class="font-semibold">{{ param.paramName }}</h5>
                    <span class="text-xs bg-red-600 px-2 py-1 rounded">Required</span>
                    <span class="text-xs bg-gray-600 px-2 py-1 rounded">{{ param.dataType }}</span>
                  </div>
                  <p v-if="getFieldHelp(param.paramName)" class="text-sm text-gray-300">
                    {{ getFieldHelp(param.paramName) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Optional Parameters -->
        <div v-if="optionalParams.length > 0" class="mb-6">
          <h4 class="text-lg font-medium mb-3 text-blue-400 flex items-center">
            Optional Parameters
            <span class="ml-2 text-xs bg-blue-900 px-2 py-1 rounded">{{ optionalParams.length }}</span>
          </h4>
          <div class="space-y-3">
            <div
              v-for="param in optionalParams"
              :key="param.id"
              class="border border-blue-600 rounded p-4 bg-blue-950 bg-opacity-20"
            >
              <div class="flex items-start justify-between">
                <div class="flex-1">
                  <div class="flex items-center space-x-3 mb-2">
                    <h5 class="font-semibold">{{ param.paramName }}</h5>
                    <span class="text-xs bg-blue-600 px-2 py-1 rounded">Optional</span>
                    <span class="text-xs bg-gray-600 px-2 py-1 rounded">{{ param.dataType }}</span>
                  </div>
                  <p v-if="getFieldHelp(param.paramName)" class="text-sm text-gray-300">
                    {{ getFieldHelp(param.paramName) }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- No Parameters -->
        <div v-if="Fetcher.paramsDef.length === 0" class="text-center py-8 text-gray-400">
          This resource type has no parameters configured
        </div>
      </div>

      <!-- No parameters at all -->
      <div v-else class="text-center py-8 text-gray-400">
        This resource type has no parameters configured
      </div>

      <!-- Resources Using This Fetcher -->
      <div v-if="Fetcher.resources && Fetcher.resources.length > 0" class="mt-6 pt-6 border-t border-gray-600">
        <h4 class="text-lg font-medium mb-3">Resources Using This Fetcher</h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
          <router-link
            v-for="resource in Fetcher.resources"
            :key="resource.id"
            :to="`/resources/${resource.id}`"
            class="p-3 bg-gray-700 rounded hover:bg-gray-600 transition-colors"
          >
            <div class="font-medium">{{ resource.name }}</div>
            <div class="text-sm text-gray-400">{{ resource.publisher }}</div>
            <div class="text-xs text-gray-500 mt-1">
              {{ resource.active ? 'Active' : 'Inactive' }}
            </div>
          </router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  Fetcher: {
    type: Object,
    required: true
  }
})

defineEmits(['close'])

// Field metadata for common parameters
const fieldMetadata = {
  'url': {
    label: 'URL',
    description: 'The base URL for the resource or API endpoint'
  },
  'timeout': {
    label: 'Timeout',
    description: 'Request timeout in seconds'
  },
  'headers': {
    label: 'Headers',
    description: 'HTTP headers in JSON format'
  },
  'method': {
    label: 'HTTP Method',
    description: 'HTTP method (GET, POST, PUT, DELETE)'
  },
  'max_retries': {
    label: 'Max Retries',
    description: 'Maximum number of retry attempts for failed requests'
  },
  'delay_between_requests': {
    label: 'Delay Between Requests',
    description: 'Delay in seconds between consecutive requests'
  },
  'page_size': {
    label: 'Page Size',
    description: 'Number of records to fetch per page'
  },
  'max_pages': {
    label: 'Max Pages',
    description: 'Maximum number of pages to fetch'
  },
  'rows_selector': {
    label: 'Rows Selector',
    description: 'CSS selector for extracting data rows from HTML'
  },
  'pagination_type': {
    label: 'Pagination Type',
    description: 'Type of pagination: "links" or "form"'
  },
  'has_header': {
    label: 'Has Header',
    description: 'Whether the first row contains column headers'
  },
  'clean_html': {
    label: 'Clean HTML',
    description: 'Whether to clean HTML formatting from extracted text'
  }
}

// Computed properties
const requiredParams = computed(() => {
  return props.Fetcher.paramsDef?.filter(p => p.required) || []
})

const optionalParams = computed(() => {
  return props.Fetcher.paramsDef?.filter(p => !p.required) || []
})

function getFieldHelp(paramName) {
  return fieldMetadata[paramName]?.description
}
</script>