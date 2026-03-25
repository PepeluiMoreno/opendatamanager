<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-8">
      <div>
        <h1 class="text-3xl font-bold">Settings</h1>
        <p v-if="sysInfo" class="text-xs text-gray-500 mt-1">
          Backend: {{ sysInfo.ram_total_gb }} GB RAM
          ({{ sysInfo.source === 'cgroup' ? 'container limit' : 'host' }}) ·
          {{ sysInfo.cpu_logical }} logical CPUs · {{ sysInfo.cpu_physical }} physical
        </p>
      </div>
      <transition name="fade">
        <span v-if="saved" class="text-xs text-green-400 font-medium">Saved</span>
      </transition>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-16">Loading...</div>

    <div v-else class="space-y-6">

      <!-- Concurrency -->
      <section class="card p-5">
        <h2 class="text-sm font-semibold text-gray-300 mb-1 flex items-center gap-2">
          <span>⚡</span> Concurrency
        </h2>
        <p class="text-xs text-gray-600 mb-4">Controls how many processes run in parallel and fetcher limits.</p>
        <div class="grid grid-cols-2 gap-x-10 divide-y-0">
          <SettingRow
            v-for="k in concurrencyKeys" :key="k"
            :cfg="get(k)" :sysInfo="sysInfo"
            @save="save"
            class="border-t border-gray-700 first:border-t-0 col-span-1"
          />
        </div>
      </section>

      <!-- Retention + Behaviour: shared card, 2-column grid so rows align -->
      <section class="card p-5">
        <div class="grid grid-cols-2 gap-x-10">

          <!-- Left header -->
          <div class="mb-4">
            <h2 class="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span>🗄️</span> Data retention
            </h2>
            <p class="text-xs text-gray-600 mt-0.5">How long to keep logs and execution history.</p>
          </div>
          <!-- Right header -->
          <div class="mb-4">
            <h2 class="text-sm font-semibold text-gray-300 flex items-center gap-2">
              <span>🔧</span> Behaviour
            </h2>
            <p class="text-xs text-gray-600 mt-0.5">Runtime behaviour and notifications.</p>
          </div>

          <!-- Rows interleaved: left col then right col per row -->
          <template v-for="i in retBehRows" :key="i">
            <!-- Left -->
            <div class="border-t border-gray-700">
              <SettingRow
                v-if="retentionKeys[i]"
                :cfg="get(retentionKeys[i])" :sysInfo="sysInfo"
                @save="save"
              />
              <div v-else class="min-h-[72px]"></div>
            </div>
            <!-- Right -->
            <div class="border-t border-gray-700">
              <SettingRow
                v-if="behaviourKeys[i]"
                :cfg="get(behaviourKeys[i])" :sysInfo="sysInfo"
                @save="save"
              />
              <div v-else class="min-h-[72px]"></div>
            </div>
          </template>

        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { fetchAppConfig, setConfig } from '../api/graphql.js'
import SettingRow from '../components/SettingRow.vue'

const config  = ref([])
const sysInfo = ref(null)
const loading = ref(true)
const saved   = ref(false)

const concurrencyKeys = ['max_concurrent_processes', 'default_fetch_timeout', 'max_pages_per_run', 'default_page_size']
const retentionKeys   = ['log_retention_days', 'execution_retention_days']
const behaviourKeys   = ['auto_run_on_startup', 'notify_on_failure']

const retBehRows = Array.from({ length: Math.max(retentionKeys.length, behaviourKeys.length) }, (_, i) => i)

function get(key) {
  return config.value.find(c => c.key === key) ?? { key, value: null, description: '' }
}

async function save(key, value) {
  await setConfig(key, value)
  const idx = config.value.findIndex(c => c.key === key)
  if (idx !== -1) config.value[idx] = { ...config.value[idx], value }
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}

onMounted(async () => {
  try {
    const [cfgData, infoData] = await Promise.all([
      fetchAppConfig(),
      fetch('/api/system/info').then(r => r.json()),
    ])
    config.value  = cfgData?.appConfig ?? []
    sysInfo.value = infoData
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity 0.5s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
