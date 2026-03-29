<template>
  <div class="p-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-3xl font-bold">Dashboard</h1>
      <button @click="loadAll" class="text-xs text-gray-500 hover:text-gray-300 px-3 py-1.5 border border-gray-700 rounded-lg transition-colors">
        ↻ Refresh
      </button>
    </div>

    <!-- Top KPI cards -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
      <div class="card py-4 px-5">
        <p class="text-xs text-gray-500 mb-1">Active resources</p>
        <p class="text-3xl font-bold text-blue-400">{{ stats.activeResources }}</p>
      </div>
      <div class="card py-4 px-5">
        <p class="text-xs text-gray-500 mb-1">Total extractions</p>
        <p class="text-3xl font-bold text-green-400">{{ stats.totalExecutions.toLocaleString() }}</p>
      </div>
      <div class="card py-4 px-5">
        <p class="text-xs text-gray-500 mb-1">Records extracted (all time)</p>
        <p class="text-3xl font-bold text-yellow-400">{{ fmtBig(stats.totalRecords) }}</p>
      </div>
      <div class="card py-4 px-5">
        <p class="text-xs text-gray-500 mb-1">Success rate</p>
        <p class="text-3xl font-bold" :class="stats.successRate >= 80 ? 'text-green-400' : 'text-red-400'">
          {{ stats.successRate }}%
        </p>
      </div>
    </div>

    <!-- Extraction stats table -->
    <div class="card overflow-hidden mb-6">
      <div class="flex items-center justify-between px-5 py-3 border-b border-gray-700">
        <h2 class="text-sm font-semibold text-gray-300">Extraction statistics per resource</h2>
        <span class="text-xs text-gray-600">{{ resourceStats.length }} resources</span>
      </div>

      <div v-if="loadingStats" class="text-center py-10 text-gray-500 text-sm">Loading…</div>

      <div v-else-if="resourceStats.length === 0" class="text-center py-10 text-gray-600 text-sm">
        No executions yet.
      </div>

      <div v-else class="max-h-96 overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10 bg-gray-800">
            <tr class="text-xs text-gray-500 uppercase tracking-wider">
              <th class="text-left px-5 py-3 font-medium">Resource</th>
              <th class="text-right px-4 py-3 font-medium">Last run</th>
              <th class="text-right px-4 py-3 font-medium">Last records</th>
              <th class="text-right px-4 py-3 font-medium">Trend</th>
              <th class="text-right px-4 py-3 font-medium">Total extracted</th>
              <th class="text-right px-4 py-3 font-medium">Runs</th>
              <th class="text-right px-5 py-3 font-medium">Duration</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-700/50">
          <tr v-for="r in resourceStats" :key="r.resource_id"
              class="hover:bg-gray-800/40 transition-colors">

            <!-- Resource name -->
            <td class="px-5 py-3">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-medium text-white truncate max-w-[220px]">{{ r.resource_name }}</span>
                <span v-if="!r.active" class="text-xs bg-yellow-900/60 text-yellow-500 px-1.5 py-0.5 rounded flex-shrink-0">inactive</span>
                <template v-if="r.last_execution_params">
                  <span v-for="(v, k) in r.last_execution_params" :key="k"
                    class="text-xs bg-blue-900/50 border border-blue-800 text-blue-300 px-1.5 py-0.5 rounded font-mono">
                    {{ k === 'bounding_value' ? (r.bounding_field || 'bounding') + '≤' + v : k + '=' + v }}
                  </span>
                </template>
              </div>
              <p class="text-xs text-gray-500 mt-0.5">{{ r.publisher }}</p>
            </td>

            <!-- Last run date + status -->
            <td class="px-4 py-3 text-right">
              <span v-if="r.last_run" class="text-xs text-gray-300">{{ fmtDate(r.last_run) }}</span>
              <span v-else class="text-xs text-gray-600">—</span>
              <br/>
              <span v-if="r.last_status" :class="statusClass(r.last_status)"
                class="text-xs font-medium">{{ r.last_status }}</span>
            </td>

            <!-- Last run records -->
            <td class="px-4 py-3 text-right">
              <span v-if="r.last_records != null" class="text-white font-semibold">{{ r.last_records.toLocaleString() }}</span>
              <span v-else class="text-gray-600">—</span>
            </td>

            <!-- Trend vs previous run -->
            <td class="px-4 py-3 text-right">
              <template v-if="r.trend != null">
                <span v-if="r.trend > 0" class="text-green-400 text-xs font-medium">▲ +{{ r.trend.toLocaleString() }}</span>
                <span v-else-if="r.trend < 0" class="text-red-400 text-xs font-medium">▼ {{ r.trend.toLocaleString() }}</span>
                <span v-else class="text-gray-500 text-xs">= same</span>
              </template>
              <span v-else class="text-gray-600 text-xs">—</span>
            </td>

            <!-- Total extracted -->
            <td class="px-4 py-3 text-right">
              <span v-if="r.total_records_extracted" class="text-blue-300 font-semibold">{{ fmtBig(r.total_records_extracted) }}</span>
              <span v-else class="text-gray-600">—</span>
            </td>

            <!-- Runs (success/total) -->
            <td class="px-4 py-3 text-right">
              <span class="text-gray-300">{{ r.successful_executions }}</span>
              <span class="text-gray-600">/{{ r.total_executions }}</span>
            </td>

            <!-- Last duration -->
            <td class="px-5 py-3 text-right text-xs text-gray-400">
              <span v-if="r.last_duration_s != null">{{ fmtDuration(r.last_duration_s) }}</span>
              <span v-else class="text-gray-600">—</span>
            </td>

          </tr>
          </tbody>
        </table>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const resourceStats = ref([])
const loadingStats  = ref(true)

const stats = computed(() => {
  const total   = resourceStats.value.reduce((s, r) => s + r.total_executions, 0)
  const success = resourceStats.value.reduce((s, r) => s + r.successful_executions, 0)
  const records = resourceStats.value.reduce((s, r) => s + r.total_records_extracted, 0)
  const active  = resourceStats.value.filter(r => r.active).length
  return {
    activeResources: active,
    totalExecutions: total,
    totalRecords: records,
    successRate: total > 0 ? Math.round((success / total) * 100) : 0,
  }
})

async function loadAll() {
  loadingStats.value = true
  try {
    const res = await fetch('/api/stats/resources')
    resourceStats.value = await res.json()
  } catch (e) {
    console.error(e)
  } finally {
    loadingStats.value = false
  }
}

// ─── Formatters ───────────────────────────────────────────────────────────────

function fmtBig(n) {
  if (!n) return '0'
  if (n >= 1_000_000) return (n / 1_000_000).toFixed(1) + 'M'
  if (n >= 1_000)     return (n / 1_000).toFixed(1) + 'K'
  return n.toLocaleString()
}

function fmtDate(iso) {
  if (!iso) return ''
  const d = new Date(/Z|[+-]\d{2}:?\d{2}$/.test(iso) ? iso : iso + 'Z')
  const diffH = Math.round((Date.now() - d) / 3600000)
  if (diffH < 24) return `${diffH}h ago`
  if (diffH < 168) return `${Math.round(diffH / 24)}d ago`
  return d.toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
}

function fmtDuration(s) {
  if (s == null) return ''
  if (s < 60)  return `${s}s`
  if (s < 3600) return `${Math.floor(s / 60)}m ${s % 60}s`
  return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m`
}

function statusClass(s) {
  return {
    completed: 'text-green-400',
    running:   'text-blue-400',
    failed:    'text-red-400',
    aborted:   'text-yellow-500',
  }[s] ?? 'text-gray-400'
}

onMounted(loadAll)
</script>
