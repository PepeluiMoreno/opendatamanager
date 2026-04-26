<!-- Single navigation item — closes the sidebar on mobile after navigating -->
<template>
  <router-link
    :to="to"
    class="nav-item"
    :class="{ active }"
    @click="$emit('close')"
  >
    <slot />
  </router-link>
</template>

<script setup>
defineProps({ to: String, active: Boolean })
defineEmits(['close'])
</script>

<style scoped>
.nav-item {
  @apply flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm text-gray-300
         hover:bg-gray-700 hover:text-white transition-colors;
}
.nav-item.active {
  @apply bg-gray-700 text-white font-medium;
}
</style>
