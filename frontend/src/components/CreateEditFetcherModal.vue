<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
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
                <div class="col-span-6">Parameter Name</div>
                <div class="col-span-2">Data Type</div>
                <div class="col-span-2 text-center">Required</div>
                <div class="col-span-2 text-center">Action</div>
              </div>

              <!-- Rows -->
              <div
                v-for="(param, index) in filteredParams"
                :key="`param-${index}`"
                class="grid grid-cols-12 gap-2 items-center p-2 border border-gray-600 rounded hover:bg-gray-700"
              >
                <!-- Parameter Name -->
                <div class="col-span-6">
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
                <div class="col-span-2 flex justify-center">
                  <label class="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      v-model="param.required"
                      class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500"
                    />
                  </label>
                </div>

                <!-- Delete Button -->
                <div class="col-span-2 text-center">
                  <button
                    type="button"
                    @click="removeParameter(parameters.indexOf(param))"
                    class="text-red-400 hover:text-red-300"
                    title="Remove parameter"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 inline" viewBox="0 0 20 20" fill="currentColor">
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

   <!-- ENUM Dialog -->
   <div v-if="showEnumDialog" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
     <div class="bg-gray-800 rounded-lg p-6 w-full max-w-xl max-h-[90vh] overflow-y-auto">
       <div class="flex items-start justify-between mb-4">
         <div>
           <h3 class="text-xl font-bold">ENUM Options</h3>
           <p class="text-sm text-gray-400 mt-1">Configure available options for enum parameter: {{ currentEnumParam?.paramName }}</p>
         </div>
         <button @click="closeEnumDialog" class="text-gray-400 hover:text-white text-2xl">
           ×
         </button>
       </div>

       <div class="space-y-3">
         <div v-for="(option, index) in enumOptions" :key="index" class="flex items-center space-x-2">
           <input
             v-model="enumOptions[index]"
             type="text"
             class="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 text-sm"
             placeholder="Option value"
           />
           <button
             @click="removeEnumOption(index)"
             class="text-red-400 hover:text-red-300 text-sm"
           >
            Remove
           </button>
         </div>
         
         <button
           @click="addEnumOption"
           class="w-full py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm font-medium transition-colors"
         >
           + Add Option
         </button>
       </div>

       <div class="flex justify-end space-x-3 mt-6">
         <button
           @click="closeEnumDialog"
           class="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white rounded text-sm"
         >
           Cancel
         </button>
         <button
           @click="saveEnumDialog"
           class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded text-sm"
         >
           Save ENUM
         </button>
       </div>
     </div>
   </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { createFetcher, updateFetcher } from '../api/graphql'

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
  description: ''
})

const parameters = ref([])
const submitting = ref(false)
const validationError = ref('')
const activeTab = ref('required')

// ENUM dialog state
const showEnumDialog = ref(false)
const currentEnumParam = ref(null)
const enumOptions = ref([''])

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
      description: newFetcher.description || ''
    }

    // Load existing parameters
    if (newFetcher.paramsDef && Array.isArray(newFetcher.paramsDef)) {
      parameters.value = newFetcher.paramsDef.map(p => ({
        paramName: p.paramName || '',
        dataType: p.dataType || 'string',
        required: p.required !== undefined ? p.required : true
      }))
    } else {
      parameters.value = []
    }
  } else {
    // Reset form for new fetcher
    formData.value = {
      name: '',
      description: ''
    }
    parameters.value = []
  }
}, { immediate: true })

function addParameter() {
  parameters.value.push({
    paramName: '',
    dataType: 'string',
    required: true
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
      description: formData.value.description || null,
      params: parameters.value
    }

    if (props.Fetcher) {
      // Update existing
      await updateFetcher(props.Fetcher.id, input)
      emit('saved', `Fetcher "${formData.value.name}" updated successfully`)
    } else {
      // Create new
      await createFetcher(input)
      emit('saved', `Fetcher "${formData.value.name}" created successfully`)
    }

  } catch (e) {
    validationError.value = e.message || 'Failed to save Fetcher'
  } finally {
    submitting.value = false
  }
}

// ENUM dialog functions
function onDataTypeChange(param, event) {
  if (event.target.value === 'enum') {
    currentEnumParam.value = param
    enumOptions.value = param.defaultValue ? param.defaultValue.split(',').map(opt => opt.trim()) : ['']
    showEnumDialog.value = true
  }
}

function closeEnumDialog() {
  showEnumDialog.value = false
  currentEnumParam.value = null
  enumOptions.value = ['']
}

function addEnumOption() {
  enumOptions.value.push('')
}

function removeEnumOption(index) {
  enumOptions.value.splice(index, 1)
}

function saveEnumDialog() {
  if (currentEnumParam.value) {
    const newValue = enumOptions.value.filter(opt => opt.trim()).join(',')
    currentEnumParam.value.defaultValue = newValue
    
    // Forzar reactividad: buscar el parámetro y actualizarlo en el array
    const paramIndex = parameters.value.findIndex(p => p === currentEnumParam.value)
    if (paramIndex !== -1) {
      parameters.value[paramIndex] = { ...parameters.value[paramIndex], defaultValue: newValue }
    }
  }
  closeEnumDialog()
}
</script>