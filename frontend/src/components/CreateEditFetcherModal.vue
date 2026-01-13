<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-6xl max-h-[90vh] overflow-y-auto">
      <div class="flex items-start justify-between mb-6">
        <h2 class="text-2xl font-bold">
          {{ Fetcher ? 'Edit Fetcher' : 'New Fetcher' }}
        </h2>
        <button @click="$emit('close')" class="text-gray-400 hover:text-white text-2xl">
          ×
        </button>
      </div>

      <form @submit.prevent="submitForm" class="space-y-6">
        <!-- Basic Info -->
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">Fetcher Name *</label>
            <input
              v-model="formData.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
              placeholder="e.g., API REST, HTML Forms"
            />
            <p class="text-xs text-gray-400 mt-1">Unique identifier for this Fetcher</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Class Path *</label>
            <input
              v-model="formData.classPath"
              type="text"
              required
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 font-mono text-sm"
              placeholder="e.g., app.fetchers.rest.RestFetcher"
            />
            <p class="text-xs text-gray-400 mt-1">Python class path for dynamic import</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Description</label>
            <textarea
              v-model="formData.description"
              rows="3"
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
              placeholder="Describe what this Fetcher does..."
            ></textarea>
          </div>
        </div>

        <!-- Parameters List with Tabs -->
        <div class="border-t border-gray-600 pt-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-xl font-semibold">Parameters Definition</h3>
              <div class="flex gap-2">
                <button
                  type="button"
                  @click="addParameter"
                  class="btn btn-secondary text-sm py-1 px-2"
                >
                  + Add Parameter
                </button>
              </div>
            </div>
              
          <div v-if="parameters.length === 0" class="text-center py-8 text-gray-400">
            No parameters configured yet. Add at least one parameter for this Fetcher.
          </div>

          <div v-else>
            <!-- Tabs -->
            <div class="flex space-x-1 mb-4 border-b border-gray-600">
              <button
                type="button"
                @click="activeTab = 'required'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'required'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Required ({{ requiredParams.length }})
              </button>
              <button
                type="button"
                @click="activeTab = 'optional'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'optional'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Optional ({{ optionalParams.length }})
              </button>
              <button
                type="button"
                @click="activeTab = 'all'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'all'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                All ({{ parameters.length }})
              </button>
            </div>

            <!-- Parameters Grid -->
            <div class="space-y-2">
              <!-- Header -->
              <div class="grid grid-cols-12 gap-2 text-xs font-medium text-gray-400 px-2">
                <div class="col-span-3">Parameter Name</div>
                <div class="col-span-2">Data Type</div>
                <div class="col-span-1 text-center">Required</div>
                <div class="col-span-3">Default Value / Enum</div>
                <div class="col-span-3 text-center">Actions</div>
              </div>

              <!-- Rows -->
              <div
                v-for="(param, index) in filteredParams"
                :key="`param-${index}`"
                class="grid grid-cols-12 gap-2 items-center p-2 border border-gray-600 rounded hover:bg-gray-700"
              >
                <!-- Parameter Name -->
                <div class="col-span-3">
                  <input
                    v-model="param.paramName"
                    type="text"
                    required
                    class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    placeholder="e.g., url, timeout"
                  />
                </div>

                <!-- Data Type -->
                <div class="col-span-2">
                   <select
                     v-model="param.dataType"
                     required
                     class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                     @change="onDataTypeChange(param, $event)"
                   >
                     <option value="string">String</option>
                     <option value="integer">Integer</option>
                     <option value="boolean">Boolean</option>
                     <option value="json">JSON</option>
                     <option value="enum">ENUM</option>
                   </select>
                </div>

                <!-- Required Checkbox -->
                <div class="col-span-1 flex justify-center">
                  <label class="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      v-model="param.required"
                      class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                    />
                  </label>
                </div>

                <!-- Default Value / Enum Values -->
                <div class="col-span-3">
                  <!-- Show enum values input if type is enum -->
                  <input
                    v-if="param.dataType === 'enum'"
                    :value="param.enumValuesString || ''"
                    @input="updateEnumValuesString(param, $event.target.value)"
                    type="text"
                    class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    placeholder="[option1, option2, option3]"
                  />
                  <!-- Show default value input for other types -->
                  <input
                    v-else
                    v-model="param.defaultValue"
                    type="text"
                    class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    placeholder="Optional default"
                  />
                </div>

                <!-- Actions -->
                <div class="col-span-3 flex justify-center gap-2">
                  <button
                    type="button"
                    @click="removeParameter(parameters.indexOf(param))"
                    class="text-red-400 hover:text-red-300"
                    title="Remove parameter"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Validation Error -->
        <div v-if="validationError" class="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm">
          {{ validationError }}
        </div>

        <!-- Form Actions -->
        <div class="flex justify-end space-x-3 pt-6 border-t border-gray-600">
          <button type="button" @click="$emit('close')" class="btn btn-secondary">
            Cancel
          </button>
          <button 
            type="submit" 
            :disabled="submitting || !isFormValid" 
            class="btn btn-primary"
          >
            {{ submitting ? 'Saving...' : (Fetcher ? 'Update' : 'Create') }}
          </button>
        </div>
       </form>
     </div>
   </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
  createFetcher,
  updateFetcher,
  createTypeFetcherParam,
  updateTypeFetcherParam,
  deleteTypeFetcherParam
} from '../api/graphql'

const props = defineProps({
  Fetcher: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'saved'])

// Form data
const formData = ref({
  name: '',
  classPath: '',
  description: ''
})

const parameters = ref([])
const submitting = ref(false)
const validationError = ref('')
const activeTab = ref('required')

// Computed properties
const requiredParams = computed(() => {
  return parameters.value.filter(p => p.required)
})

const optionalParams = computed(() => {
  return parameters.value.filter(p => !p.required)
})

const filteredParams = computed(() => {
  if (activeTab.value === 'required') {
    return requiredParams.value
  } else if (activeTab.value === 'optional') {
    return optionalParams.value
  }
  return parameters.value
})

const isFormValid = computed(() => {
  // Basic fields must be filled
  if (!formData.value.name.trim()) {
    return false
  }

  // At least one parameter must exist
  if (parameters.value.length === 0) {
    return false
  }
  
  // All parameter names must be unique and filled
  const paramNames = parameters.value.map(p => p.paramName?.trim()).filter(n => n)
  const uniqueNames = new Set(paramNames)
  if (uniqueNames.size !== paramNames.length) {
    return false
  }
  
  // All required fields in parameters must be filled
  for (const param of parameters.value) {
    if (!param.paramName?.trim() || !param.dataType) {
      return false
    }
  }
  
  return true
})

// Initialize form when Fetcher prop changes
watch(() => props.Fetcher, (newFetcher) => {
  if (newFetcher) {
    formData.value = {
      name: newFetcher.name || '',
      classPath: newFetcher.classPath || '',
      description: newFetcher.description || ''
    }

    // Load existing parameters
    if (newFetcher.paramsDef && Array.isArray(newFetcher.paramsDef)) {
      parameters.value = newFetcher.paramsDef.map(p => ({
        id: p.id || null,
        paramName: p.paramName || '',
        dataType: p.dataType || 'string',
        required: p.required !== undefined ? p.required : true,
        defaultValue: p.defaultValue || null,
        enumValues: p.enumValues || null,
        enumValuesString: p.enumValues && Array.isArray(p.enumValues) ? '[' + p.enumValues.join(', ') + ']' : ''
      }))
    } else {
      parameters.value = []
    }
  } else {
    // Reset form for new fetcher
    formData.value = {
      name: '',
      classPath: '',
      description: ''
    }
    parameters.value = []
  }
}, { immediate: true })

function addParameter() {
  parameters.value.push({
    id: null,
    paramName: '',
    dataType: 'string',
    required: true,
    defaultValue: null,
    enumValues: null,
    enumValuesString: ''
  })
}

function removeParameter(index) {
  parameters.value.splice(index, 1)
}

async function submitForm() {
  if (!isFormValid.value) {
    validationError.value = 'Please fill in all required fields correctly'
    return
  }

  try {
    submitting.value = true
    validationError.value = null

    const input = {
      name: formData.value.name,
      classPath: formData.value.classPath || null,
      description: formData.value.description || null
    }

    let fetcherId
    if (props.Fetcher) {
      // Update existing fetcher
      await updateFetcher(props.Fetcher.id, input)
      fetcherId = props.Fetcher.id
    } else {
      // Create new fetcher
      const result = await createFetcher(input)
      fetcherId = result.createFetcher.id
    }

    // Now sync parameters
    await syncParameters(fetcherId)

    emit('saved', `Fetcher "${formData.value.name}" ${props.Fetcher ? 'updated' : 'created'} successfully`)

  } catch (e) {
    validationError.value = e.message || 'Failed to save Fetcher'
  } finally {
    submitting.value = false
  }
}

async function syncParameters(fetcherId) {
  const existingParams = props.Fetcher?.paramsDef || []
  const existingParamIds = new Set(existingParams.map(p => p.id))
  const currentParamIds = new Set(parameters.value.filter(p => p.id).map(p => p.id))

  // Delete removed parameters
  for (const existingParam of existingParams) {
    if (!currentParamIds.has(existingParam.id)) {
      await deleteTypeFetcherParam(existingParam.id)
    }
  }

  // Create or update parameters
  for (const param of parameters.value) {
    const paramInput = {
      fetcherId: fetcherId,
      paramName: param.paramName,
      dataType: param.dataType,
      required: param.required,
      defaultValue: param.defaultValue || null,
      enumValues: param.enumValues || null
    }

    if (param.id && existingParamIds.has(param.id)) {
      // Update existing parameter
      const updateInput = {
        paramName: param.paramName,
        dataType: param.dataType,
        required: param.required,
        defaultValue: param.defaultValue || null,
        enumValues: param.enumValues || null
      }
      await updateTypeFetcherParam(param.id, updateInput)
    } else {
      // Create new parameter
      const result = await createTypeFetcherParam(paramInput)
      param.id = result.createTypeFetcherParam.id
    }
  }
}

// ENUM helper function
function updateEnumValuesString(param, value) {
  // Update the string as-is (let user type freely)
  param.enumValuesString = value

  // Parse to array for saving
  let cleanValue = value.trim()

  // Remove surrounding brackets if present
  if (cleanValue.startsWith('[')) {
    cleanValue = cleanValue.substring(1)
  }
  if (cleanValue.endsWith(']')) {
    cleanValue = cleanValue.substring(0, cleanValue.length - 1)
  }

  // Parse comma-separated values
  const values = cleanValue
    .split(',')
    .map(v => v.trim())
    .filter(v => v.length > 0)

  param.enumValues = values.length > 0 ? values : null
}
</script>