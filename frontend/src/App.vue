<template>
  <div class="flex h-screen bg-gray-900">
    <BackendStatus />
    <Sidebar />
    <div class="flex-1 overflow-auto">
      <router-view />
    </div>
  </div>
</template>

<script setup>
import Sidebar from './components/Sidebar.vue'
import BackendStatus from './components/BackendStatus.vue'
</script>
