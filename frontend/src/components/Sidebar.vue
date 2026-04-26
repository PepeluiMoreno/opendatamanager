<template>
  <div class="w-64 h-full bg-gray-800 border-r border-gray-700 flex flex-col">
    <!-- Header -->
    <div class="flex items-center justify-between p-5 border-b border-gray-700">
      <div>
        <h1 class="text-lg font-bold text-blue-400 leading-tight">OpenDataManager</h1>
        <p class="text-xs text-gray-400 mt-0.5">Metadata-driven Backend</p>
        <p v-if="appVersion" class="text-xs text-gray-600 mt-0.5 font-mono">build {{ appVersion }}</p>
      </div>
      <!-- Close button — only shown on mobile/tablet -->
      <button
        @click="$emit('close')"
        class="lg:hidden p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-gray-700 transition-colors flex-shrink-0"
        aria-label="Cerrar menú"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    </div>

    <!-- Nav -->
    <nav
      class="flex-1 p-3 space-y-0.5 overflow-y-auto relative transition-opacity duration-300"
      :class="status !== 'online' ? 'opacity-40 pointer-events-none select-none' : ''"
    >
      <NavItem to="/" :active="$route.path === '/'">📊 Dashboard</NavItem>
      <NavItem to="/publishers" :active="$route.path === '/publishers'">🏛️ Publishers</NavItem>
      <NavItem to="/resources" :active="$route.path.startsWith('/resources')">🔌 Resources</NavItem>
      <NavItem to="/fetchers" :active="$route.path.startsWith('/fetchers')">🔧 Fetchers</NavItem>
      <NavItem to="/processes" :active="$route.path === '/processes'">⚡ Processes</NavItem>
      <NavItem to="/discovering" :active="$route.path === '/discovering'">🔎 Discovering</NavItem>
      <NavItem to="/explorer" :active="$route.path === '/explorer'">🔍 Data Explorer</NavItem>
      <NavItem to="/applications" :active="$route.path === '/applications'">📦 Applications</NavItem>
      <NavItem to="/subscriptions" :active="$route.path === '/subscriptions'">🔗 Subscriptions</NavItem>
      <NavItem to="/schedule" :active="$route.path === '/schedule'">🕐 Schedule</NavItem>
      <NavItem to="/settings" :active="$route.path === '/settings'">⚙️ Settings</NavItem>
      <NavItem to="/trash" :active="$route.path === '/trash'">🗑️ Trash</NavItem>

      <!-- Offline overlay -->
      <div
        v-if="status !== 'online'"
        class="absolute inset-0 flex items-center justify-center"
      >
        <p class="text-xs text-gray-500 text-center px-4">
          Navigation unavailable<br>while backend is {{ status }}
        </p>
      </div>
    </nav>

    <!-- Footer: backend status + RAM -->
    <div class="p-4 border-t border-gray-700 space-y-3">
      <div
        v-if="status === 'offline'"
        class="flex items-center gap-2 bg-red-900 border border-red-600 text-red-200 rounded-lg px-3 py-2 text-xs font-medium animate-pulse"
      >
        <svg class="w-4 h-4 flex-shrink-0 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
            d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/>
        </svg>
        Backend unreachable
      </div>

      <div
        v-else-if="status === 'checking'"
        class="flex items-center gap-2 bg-yellow-900 border border-yellow-700 text-yellow-200 rounded-lg px-3 py-2 text-xs font-medium"
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
          <span class="inline-flex h-2 w-2 rounded-full" :class="{
            'bg-green-400': status === 'online',
            'bg-red-500 animate-pulse': status === 'offline',
            'bg-yellow-400 animate-pulse': status === 'checking',
          }"/>
          <span :class="{
            'text-green-400': status === 'online',
            'text-red-400': status === 'offline',
            'text-yellow-400': status === 'checking',
          }">{{ status }}</span>
        </span>
      </div>

      <div v-if="ramTotal > 0">
        <div class="flex items-center justify-between text-xs mb-1">
          <span class="text-gray-500">RAM disponible</span>
          <span :class="ramColor" class="font-mono tabular-nums">{{ ramAvailGb }} / {{ ramTotalGb }} GB</span>
        </div>
        <div class="h-1.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            class="h-full rounded-full transition-all duration-700"
            :class="ramBarColor"
            :style="{ width: (100 - ramUsedPct) + '%' }"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import NavItem from './NavItem.vue'

defineEmits(['close'])

const status     = ref('checking')
const ramTotal   = ref(0)
const ramAvail   = ref(0)
const appVersion = ref('')
let timer = null

const ramTotalGb = computed(() => (ramTotal.value / 1024).toFixed(1))
const ramAvailGb = computed(() => (ramAvail.value  / 1024).toFixed(1))
const ramUsedPct = computed(() =>
  ramTotal.value > 0 ? Math.round((1 - ramAvail.value / ramTotal.value) * 100) : 0
)
const ramColor = computed(() => {
  const free = 100 - ramUsedPct.value
  return free < 15 ? 'text-red-400' : free < 30 ? 'text-yellow-400' : 'text-green-400'
})
const ramBarColor = computed(() => {
  const free = 100 - ramUsedPct.value
  return free < 15 ? 'bg-red-500' : free < 30 ? 'bg-yellow-500' : 'bg-green-500'
})

let _healthFailures = 0
async function checkHealth() {
  try {
    const res = await fetch('/health', { signal: AbortSignal.timeout(8000) })
    if (res.ok) { _healthFailures = 0; status.value = 'online' }
    else if (++_healthFailures >= 2) status.value = 'offline'
  } catch { if (++_healthFailures >= 2) status.value = 'offline' }
}
async function fetchSysInfo() {
  try {
    const res = await fetch('/api/system/info', { signal: AbortSignal.timeout(3000) })
    if (res.ok) { const d = await res.json(); ramTotal.value = d.ram_total_mb ?? 0; ramAvail.value = d.ram_available_mb ?? 0 }
  } catch {}
}
async function fetchVersion() {
  try {
    const res = await fetch('/api/version', { signal: AbortSignal.timeout(3000) })
    if (res.ok) { const d = await res.json(); const v = d.version ?? ''; appVersion.value = v.length > 7 ? v.slice(0, 7) : v }
  } catch {}
}

onMounted(() => {
  checkHealth(); fetchSysInfo(); fetchVersion()
  timer = setInterval(() => { checkHealth(); fetchSysInfo() }, 15000)
})
onUnmounted(() => clearInterval(timer))
</script>
