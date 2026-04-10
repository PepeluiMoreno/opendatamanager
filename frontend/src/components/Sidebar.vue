<template>
  <div class="w-64 bg-gray-800 border-r border-gray-700 flex flex-col">
    <div class="p-6 border-b border-gray-700">
      <h1 class="text-xl font-bold text-blue-400">OpenDataManager</h1>
      <p class="text-xs text-gray-400 mt-1">Metadata-driven Backend</p>
    </div>

    <nav
      class="flex-1 p-4 space-y-2 relative transition-opacity duration-300"
      :class="status !== 'online' ? 'opacity-40 pointer-events-none select-none' : ''"
    >
      <router-link to="/" class="nav-item" :class="{ 'active': $route.path === '/' }">
        <span class="text-lg mr-3">📊</span>Dashboard
      </router-link>

      <router-link to="/publishers" class="nav-item" :class="{ 'active': $route.path === '/publishers' }">
        <span class="text-lg mr-3">🏛️</span>Publishers
      </router-link>

      <router-link to="/resources" class="nav-item" :class="{ 'active': $route.path.startsWith('/resources') }">
        <span class="text-lg mr-3">🔌</span>Resources
      </router-link>

      <router-link to="/fetchers" class="nav-item" :class="{ 'active': $route.path.startsWith('/fetchers') }">
        <span class="text-lg mr-3">🔧</span>Fetchers
      </router-link>

      <router-link to="/processes" class="nav-item" :class="{ 'active': $route.path === '/processes' }">
        <span class="text-lg mr-3">⚡</span>Processes
      </router-link>

      <router-link to="/explorer" class="nav-item" :class="{ 'active': $route.path === '/explorer' }">
        <span class="text-lg mr-3">🔍</span>Data Explorer
      </router-link>

      <router-link to="/applications" class="nav-item" :class="{ 'active': $route.path === '/applications' }">
        <span class="text-lg mr-3">📦</span>Applications
      </router-link>

      <router-link to="/subscriptions" class="nav-item" :class="{ 'active': $route.path === '/subscriptions' }">
        <span class="text-lg mr-3">🔗</span>Subscriptions
      </router-link>

      <router-link to="/schedule" class="nav-item" :class="{ 'active': $route.path === '/schedule' }">
        <span class="text-lg mr-3">🕐</span>Schedule
      </router-link>

      <router-link to="/settings" class="nav-item" :class="{ 'active': $route.path === '/settings' }">
        <span class="text-lg mr-3">⚙️</span>Settings
      </router-link>

      <router-link to="/trash" class="nav-item" :class="{ 'active': $route.path === '/trash' }">
        <span class="text-lg mr-3">🗑️</span>Trash
      </router-link>

      <!-- Offline overlay hint -->
      <div
        v-if="status !== 'online'"
        class="absolute inset-0 flex items-center justify-center"
      >
        <p class="text-xs text-gray-500 text-center px-4">
          Navigation unavailable<br>while backend is {{ status }}
        </p>
      </div>
    </nav>

    <!-- Backend status -->
    <div class="p-4 border-t border-gray-700">
      <!-- Disconnected banner -->
      <div
        v-if="status === 'offline'"
        class="mb-3 flex items-center gap-2 bg-red-900 border border-red-600 text-red-200 rounded-lg px-3 py-2 text-xs font-medium animate-pulse"
      >
        <svg class="w-4 h-4 flex-shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        </svg>
        Backend unreachable
      </div>

      <!-- Connecting indicator -->
      <div
        v-else-if="status === 'checking'"
        class="mb-3 flex items-center gap-2 bg-yellow-900 border border-yellow-700 text-yellow-200 rounded-lg px-3 py-2 text-xs font-medium"
      >
        <svg class="w-4 h-4 flex-shrink-0 animate-spin text-yellow-400" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
        Connecting...
      </div>

      <div class="flex items-center justify-between text-xs text-gray-500">
        <span>Backend</span>
        <span class="flex items-center gap-1.5">
          <span
            class="inline-flex h-2 w-2 rounded-full"
            :class="{
              'bg-green-400': status === 'online',
              'bg-red-500 animate-pulse': status === 'offline',
              'bg-yellow-400 animate-pulse': status === 'checking',
            }"
          ></span>
          <span :class="{
            'text-green-400': status === 'online',
            'text-red-400': status === 'offline',
            'text-yellow-400': status === 'checking',
          }">{{ status }}</span>
        </span>
      </div>

      <!-- RAM disponible -->
      <div v-if="ramTotal > 0" class="mt-3">
        <div class="flex items-center justify-between text-xs mb-1">
          <span class="text-gray-500">RAM disponible</span>
          <span :class="ramColor" class="font-mono tabular-nums">
            {{ ramAvailGb }} / {{ ramTotalGb }} GB
          </span>
        </div>
        <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-700"
            :class="ramColor === 'text-red-400' ? 'bg-red-500' : ramColor === 'text-yellow-400' ? 'bg-yellow-500' : 'bg-green-500'"
            :style="{ width: (100 - ramUsedPct) + '%' }"
          ></div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const status  = ref('checking')
const ramTotal = ref(0)   // MB
const ramAvail = ref(0)   // MB
let timer = null

const ramTotalGb  = computed(() => (ramTotal.value / 1024).toFixed(1))
const ramAvailGb  = computed(() => (ramAvail.value  / 1024).toFixed(1))
const ramUsedPct  = computed(() => ramTotal.value > 0
  ? Math.round((1 - ramAvail.value / ramTotal.value) * 100) : 0)
const ramColor    = computed(() => {
  const pct = 100 - ramUsedPct.value  // % libre
  if (pct < 15) return 'text-red-400'
  if (pct < 30) return 'text-yellow-400'
  return 'text-green-400'
})

let _healthFailures = 0
async function checkHealth() {
  try {
    const res = await fetch('/health', { signal: AbortSignal.timeout(8000) })
    if (res.ok) {
      _healthFailures = 0
      status.value = 'online'
    } else {
      if (++_healthFailures >= 2) status.value = 'offline'
    }
  } catch {
    if (++_healthFailures >= 2) status.value = 'offline'
  }
}

async function fetchSysInfo() {
  try {
    const res = await fetch('/api/system/info', { signal: AbortSignal.timeout(3000) })
    if (res.ok) {
      const d = await res.json()
      ramTotal.value = d.ram_total_mb  ?? 0
      ramAvail.value = d.ram_available_mb ?? 0
    }
  } catch {}
}

onMounted(() => {
  checkHealth()
  fetchSysInfo()
  timer = setInterval(() => { checkHealth(); fetchSysInfo() }, 15000)
})

onUnmounted(() => clearInterval(timer))
</script>

<style scoped>
.nav-item {
  @apply flex items-center px-4 py-3 rounded-lg text-gray-300 hover:bg-gray-700 hover:text-white transition-colors;
}

.nav-item.active {
  @apply bg-gray-700 text-white font-medium;
}
</style>
