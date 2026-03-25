<template>
  <div class="flex items-center justify-between gap-4 py-3 min-h-[72px]">
    <!-- Label + description -->
    <div class="min-w-0">
      <p class="text-sm font-medium text-gray-200">{{ label }}</p>
      <p class="text-xs text-gray-500 mt-0.5 leading-snug">{{ cfg.description }}</p>
      <!-- Limit hint for numbers -->
      <p v-if="!isBool && lim" class="text-xs text-gray-600 mt-0.5">
        range {{ lim.min }}–{{ lim.max }}
        <span v-if="lim.reason" class="text-gray-700">· {{ lim.reason }}</span>
      </p>
    </div>

    <!-- Control -->
    <div class="flex items-center gap-2 flex-shrink-0">
      <!-- Boolean toggle -->
      <template v-if="isBool">
        <button type="button" @click="toggleBool"
          :class="localValue ? 'bg-blue-500' : 'bg-gray-600'"
          class="relative inline-flex h-5 w-10 items-center rounded-full transition-colors focus:outline-none">
          <span :class="localValue ? 'translate-x-5' : 'translate-x-1'"
            class="inline-block h-4 w-4 transform rounded-full bg-white transition-transform"></span>
        </button>
        <span class="text-xs text-gray-400 w-6">{{ localValue ? 'on' : 'off' }}</span>
      </template>

      <!-- Number input -->
      <template v-else-if="isNumber">
        <input
          v-model.number="localValue"
          type="number"
          :min="lim?.min ?? 0"
          :max="lim?.max"
          :step="lim?.step ?? 1"
          @change="clampAndCommit"
          class="w-20 text-sm bg-gray-700 border border-gray-600 text-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-blue-500 text-right"
          :class="{ 'border-red-600': outOfRange }"
        />
        <span class="text-xs text-gray-500 w-8">{{ unit }}</span>
      </template>

      <!-- String input -->
      <template v-else>
        <input v-model="localValue" type="text" @blur="commit" @keydown.enter="commit"
          class="w-40 text-sm bg-gray-700 border border-gray-600 text-gray-200 rounded px-2 py-1.5 focus:outline-none focus:border-blue-500" />
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  cfg:     { type: Object, required: true },
  sysInfo: { type: Object, default: null },
})
const emit = defineEmits(['save'])

const localValue = ref(props.cfg.value)
watch(() => props.cfg.value, v => { localValue.value = v })

const isBool   = computed(() => typeof props.cfg.value === 'boolean')
const isNumber = computed(() => typeof props.cfg.value === 'number')

const label = computed(() =>
  props.cfg.key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
)

const unit = computed(() => {
  const k = props.cfg.key
  if (k.includes('timeout'))   return 'sec'
  if (k.includes('days'))      return 'days'
  if (k.includes('processes')) return 'max'
  if (k.includes('page_size')) return 'rows'
  if (k.includes('pages'))     return 'pages'
  return ''
})

// Smart limits derived from backend hardware
const lim = computed(() => {
  const s = props.sysInfo
  if (!s) return null
  const ram  = s.ram_total_gb  ?? 4
  const ramMb = s.ram_total_mb ?? 4096
  const cpu  = s.cpu_logical   ?? 2

  // Each concurrent fetcher buffers its full dataset in RAM.
  // Conservatively assume ~512 MB peak per fetcher.
  const maxByRam = Math.max(1, Math.floor(ram / 0.5))
  const maxByCpu = cpu * 2

  switch (props.cfg.key) {
    case 'max_concurrent_processes':
      return {
        min: 1,
        max: Math.min(maxByRam, maxByCpu),
        step: 1,
        reason: `≤ RAM÷0.5GB (${maxByRam}) and CPU×2 (${maxByCpu})`,
      }
    case 'default_fetch_timeout':
      return { min: 10, max: 600, step: 10, reason: '10s–600s' }
    case 'max_pages_per_run':
      return { min: 0, max: 50000, step: 100, reason: '0 = unlimited' }
    case 'default_page_size':
      // Each page briefly held in memory: assume ~5 KB/record
      return {
        min: 10,
        max: Math.min(5000, Math.floor(ramMb / 5)),
        step: 10,
        reason: `≤ RAM÷5MB (${Math.min(5000, Math.floor(ramMb / 5))})`,
      }
    case 'log_retention_days':
      return { min: 1, max: 365, step: 1 }
    case 'execution_retention_days':
      return { min: 7, max: 730, step: 1 }
    default:
      return { min: 0, max: 99999, step: 1 }
  }
})

const outOfRange = computed(() => {
  if (!lim.value || !isNumber.value) return false
  return localValue.value < lim.value.min || (lim.value.max && localValue.value > lim.value.max)
})

function clampAndCommit() {
  if (lim.value) {
    if (localValue.value < lim.value.min) localValue.value = lim.value.min
    if (lim.value.max && localValue.value > lim.value.max) localValue.value = lim.value.max
  }
  emit('save', props.cfg.key, localValue.value)
}

function toggleBool() {
  localValue.value = !localValue.value
  emit('save', props.cfg.key, localValue.value)
}

function commit() {
  emit('save', props.cfg.key, localValue.value)
}
</script>
