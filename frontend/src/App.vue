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

      <div class="flex-1 overflow-auto relative">
        <router-view />
        <!-- Backend caído: overlay global. Evita que las vistas muestren "no hay
             datos" o errores por una indisponibilidad transitoria del backend. -->
        <transition name="fade">
          <div v-if="backendCaido" class="absolute inset-0 z-40 flex items-center justify-center bg-gray-900/85 backdrop-blur-sm">
            <div class="text-center px-6">
              <svg class="w-8 h-8 mx-auto mb-3 animate-spin text-red-400" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              <p class="text-gray-200 font-medium">Backend no disponible</p>
              <p class="text-gray-500 text-sm mt-1">Reconectando…</p>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>

  <!-- Overlay de inicio de sesión (bajo demanda; invitado por defecto) -->
  <Login v-if="mostrarLogin" />

  <!-- Únicos para toda la app -->
  <ConfirmHost />
  <ToastHost />
</template>

<script setup>
import { ref, computed } from 'vue'
import Sidebar from './components/Sidebar.vue'
import BackendStatus from './components/BackendStatus.vue'
import Login from './components/Login.vue'
import ConfirmHost from './components/ConfirmHost.vue'
import ToastHost from './components/ToastHost.vue'
import { useAuth } from './composables/useAuth'
import { useBackendStatus } from './composables/useBackendStatus'

const { mostrarLogin } = useAuth()
const sidebarOpen = ref(false)
const { isConnected } = useBackendStatus()
// false = caído (no null/checking, para no tapar en el arranque inicial).
const backendCaido = computed(() => isConnected.value === false)
</script>

<style>
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
