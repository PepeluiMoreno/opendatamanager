<template>
  <div class="inline-flex items-center relative group">
    <slot></slot>
    <div
      v-if="text"
      class="ml-2 cursor-help text-gray-400 hover:text-blue-400 transition-colors"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-4 w-4"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
      >
        <path
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2"
          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
      </svg>
    </div>

    <!-- Tooltip content -->
    <div
      v-if="text"
      class="absolute right-0 bottom-full mb-2 hidden group-hover:block z-[9999] w-64 pointer-events-none"
    >
      <div class="bg-gray-900 text-gray-200 text-xs rounded-lg py-2 px-3 border border-gray-700 shadow-xl">
        {{ text }}
        <!-- Arrow -->
        <div class="absolute top-full right-4 -mt-1">
          <div class="border-4 border-transparent border-t-gray-900"></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  text: {
    type: String,
    default: ''
  }
})
</script>

<style scoped>
/* Ensure tooltip appears above other content */
.group:hover > div {
  z-index: 1000;
}
</style>
