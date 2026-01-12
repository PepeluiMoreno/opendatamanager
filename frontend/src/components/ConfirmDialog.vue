<template>
  <div class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
    <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md shadow-xl">
      <div class="flex items-start justify-between mb-4">
        <h3 class="text-xl font-bold text-white">{{ title }}</h3>
        <button @click="$emit('cancel')" class="text-gray-400 hover:text-white text-2xl leading-none">
          ×
        </button>
      </div>

      <div class="mb-6">
        <p class="text-gray-300">{{ message }}</p>
      </div>

      <div class="flex justify-end space-x-3">
        <button
          @click="$emit('cancel')"
          class="btn btn-secondary"
        >
          {{ cancelText }}
        </button>
        <button
          @click="$emit('confirm')"
          :class="dangerMode ? 'btn btn-danger' : 'btn btn-primary'"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: 'Confirm Action'
  },
  message: {
    type: String,
    required: true
  },
  confirmText: {
    type: String,
    default: 'Confirm'
  },
  cancelText: {
    type: String,
    default: 'Cancel'
  },
  dangerMode: {
    type: Boolean,
    default: true
  }
})

defineEmits(['confirm', 'cancel'])
</script>
