<template>
  <div class="h-full flex flex-col">
    <div class="px-6 pt-6 pb-3 flex items-center gap-4 flex-shrink-0">
      <h1 class="text-xl font-bold text-white">📦 Subscribers</h1>
      <div class="flex gap-1">
        <button v-if="verActivos" @click="tab='activos'"
          class="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors"
          :class="tab==='activos' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-200'">Activos</button>
        <button v-if="verPendientes" @click="tab='pendientes'"
          class="px-3 py-1.5 text-sm font-medium rounded-lg transition-colors"
          :class="tab==='pendientes' ? 'bg-gray-700 text-white' : 'text-gray-400 hover:text-gray-200'">Pendientes</button>
      </div>
    </div>
    <div class="flex-1 min-h-0 overflow-hidden">
      <Applications v-if="tab==='activos'" />
      <Aprobaciones v-else-if="tab==='pendientes'" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import Applications from './Applications.vue'
import Aprobaciones from './Aprobaciones.vue'
import { useAuth } from '../composables/useAuth'

const { puede } = useAuth()
const verActivos = computed(() => puede('aplicaciones.gestionar'))
const verPendientes = computed(() => puede('aplicaciones.aprobar') || puede('recursos.aprobar'))
const tab = ref(puede('aplicaciones.gestionar') ? 'activos' : 'pendientes')
</script>
