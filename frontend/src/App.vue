<template>
  <!-- Mobile/tablet: stacked layout with slide-over sidebar -->
  <div class="flex h-screen bg-gray-900 overflow-hidden">
    <BackendStatus />

    <!-- Mobile overlay -->
    <transition name="fade">
      <div
        v-if="sidebarOpen"
        class="fixed inset-0 z-20 bg-black/60 lg:hidden"
        @click="sidebarOpen = false"
      />
    </transition>

    <!-- Sidebar: always visible on lg+, slide-over on mobile/tablet -->
    <aside
      class="fixed inset-y-0 left-0 z-30 transition-transform duration-200 lg:static lg:translate-x-0"
      :class="sidebarOpen ? 'translate-x-0' : '-translate-x-full'"
    >
      <Sidebar @close="sidebarOpen = false" />
    </aside>

    <!-- Main content -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Mobile topbar -->
      <header class="flex items-center gap-3 px-4 py-3 bg-gray-800 border-b border-gray-700 lg:hidden flex-shrink-0">
        <button
          @click="sidebarOpen = true"
          class="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-gray-700 transition-colors"
          aria-label="Abrir menú"
        >
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>
        <span class="text-sm font-semibold text-blue-400">OpenDataManager</span>
      </header>

      <div class="flex-1 overflow-auto">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import Sidebar from './components/Sidebar.vue'
import BackendStatus from './components/BackendStatus.vue'

const sidebarOpen = ref(false)
</script>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
