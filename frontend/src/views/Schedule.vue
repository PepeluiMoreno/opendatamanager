<template>
  <div class="p-8">

    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-3xl font-bold">Schedule</h1>
        <p class="text-xs text-gray-500 mt-1">
          {{ scheduledResources.length }} active schedule{{ scheduledResources.length !== 1 ? 's' : '' }}
        </p>
      </div>
      <button
        v-if="!showForm"
        @click="openNew"
        class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-lg transition-colors"
      >
        <span class="text-lg leading-none">+</span> New schedule
      </button>
    </div>

    <!-- ── Create / Edit panel ─────────────────────────────────────────────── -->
    <div v-if="showForm" class="card mb-6 p-6">
      <div class="flex items-center justify-between mb-6">
        <h2 class="text-base font-semibold text-white">
          {{ editingId ? 'Edit schedule' : 'New schedule' }}
        </h2>
        <button @click="closeForm" class="text-gray-500 hover:text-gray-300 text-2xl leading-none">&times;</button>
      </div>

      <!-- Resource selector -->
      <div class="mb-6">
        <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">Resource</label>
        <div v-if="editingId" class="flex items-center gap-2 py-2">
          <span class="text-sm font-semibold text-white">{{ editingResource?.name }}</span>
          <span v-if="editingResource?.fetcher" class="text-xs bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded font-mono">
            {{ editingResource.fetcher.code }}
          </span>
          <span class="text-xs text-gray-600">· {{ editingResource?.publisher }}</span>
        </div>
        <select v-else v-model="form.resourceId"
          class="w-full bg-gray-700 border border-gray-600 text-gray-200 text-sm rounded-lg px-3 py-2.5 focus:outline-none focus:border-blue-500">
          <option value="">— Select a resource —</option>
          <option v-for="r in unscheduledResources" :key="r.id" :value="r.id">
            {{ r.name }}  ·  {{ r.publisher }}
            <template v-if="r.fetcher">  [{{ r.fetcher.code }}]</template>
          </option>
        </select>
      </div>

      <!-- Frequency selector -->
      <div class="mb-6">
        <label class="block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Frequency</label>
        <div class="flex gap-2 flex-wrap">
          <button
            v-for="m in MODES" :key="m.key"
            type="button"
            @click="setMode(m.key)"
            :class="[
              'px-4 py-2 text-sm rounded-lg border font-medium transition-colors',
              form.mode === m.key
                ? 'bg-blue-600 border-blue-500 text-white shadow-md'
                : 'bg-gray-800 border-gray-600 text-gray-400 hover:border-gray-500 hover:text-gray-200'
            ]"
          >{{ m.label }}</button>
        </div>
      </div>

      <!-- Conditional fields -->
      <div class="mb-6 px-5 py-4 bg-gray-800 border border-gray-700 rounded-xl min-h-[90px] flex items-start">

        <!-- Every N minutes -->
        <div v-if="form.mode === 'minutes'" class="flex items-center gap-3 flex-wrap">
          <span class="text-sm text-gray-300">Every</span>
          <input v-model.number="form.interval" type="number" min="1" max="59"
            class="w-20 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
          <span class="text-sm text-gray-300">minutes</span>
        </div>

        <!-- Hourly -->
        <div v-else-if="form.mode === 'hourly'" class="flex items-center gap-3 flex-wrap">
          <span class="text-sm text-gray-300">At minute</span>
          <input v-model.number="form.minute" type="number" min="0" max="59"
            class="w-20 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
          <span class="text-sm text-gray-300">past every hour &nbsp;→&nbsp; :{{ String(form.minute).padStart(2,'0') }} each hour</span>
        </div>

        <!-- Daily -->
        <div v-else-if="form.mode === 'daily'" class="flex items-center gap-3 flex-wrap">
          <span class="text-sm text-gray-300">Every day at</span>
          <div class="flex items-center gap-1">
            <input v-model.number="form.hour" type="number" min="0" max="23"
              class="w-16 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
            <span class="text-gray-400 font-bold text-lg">:</span>
            <input v-model.number="form.minute" type="number" min="0" max="59"
              class="w-16 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
          </div>
        </div>

        <!-- Weekly -->
        <div v-else-if="form.mode === 'weekly'" class="space-y-4 w-full">
          <div>
            <p class="text-xs text-gray-500 mb-2">Days of the week</p>
            <div class="flex gap-2 flex-wrap">
              <button
                v-for="(day, i) in WEEK_DAYS" :key="i"
                type="button"
                @click="toggleDay(i)"
                :class="[
                  'w-10 h-10 rounded-full text-xs font-bold border-2 transition-colors select-none',
                  form.weekdays.includes(i)
                    ? 'bg-blue-600 border-blue-400 text-white'
                    : 'bg-gray-700 border-gray-600 text-gray-400 hover:border-gray-500 hover:text-gray-200'
                ]"
              >{{ day }}</button>
            </div>
          </div>
          <div class="flex items-center gap-3">
            <span class="text-sm text-gray-300">At</span>
            <div class="flex items-center gap-1">
              <input v-model.number="form.hour" type="number" min="0" max="23"
                class="w-16 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
              <span class="text-gray-400 font-bold text-lg">:</span>
              <input v-model.number="form.minute" type="number" min="0" max="59"
                class="w-16 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
            </div>
          </div>
        </div>

        <!-- Monthly -->
        <div v-else-if="form.mode === 'monthly'" class="flex items-center gap-3 flex-wrap">
          <span class="text-sm text-gray-300">On day</span>
          <input v-model.number="form.monthDay" type="number" min="1" max="31"
            class="w-16 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
          <span class="text-sm text-gray-300">of the month at</span>
          <div class="flex items-center gap-1">
            <input v-model.number="form.hour" type="number" min="0" max="23"
              class="w-16 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
            <span class="text-gray-400 font-bold text-lg">:</span>
            <input v-model.number="form.minute" type="number" min="0" max="59"
              class="w-16 text-center font-semibold text-base bg-gray-700 border border-gray-600 text-white rounded-lg px-2 py-1.5 focus:outline-none focus:border-blue-500" />
          </div>
        </div>

        <!-- Custom cron -->
        <div v-else-if="form.mode === 'custom'" class="w-full space-y-2">
          <div class="flex items-center gap-3">
            <input v-model="form.cron" type="text" placeholder="* * * * *"
              class="flex-1 font-mono text-sm bg-gray-700 border text-gray-200 rounded-lg px-3 py-2.5 focus:outline-none focus:border-blue-500"
              :class="form.cron && !isValidCron(form.cron) ? 'border-red-600' : 'border-gray-600'" />
          </div>
          <p class="text-xs text-gray-600">
            <span class="font-mono text-gray-500">minute&nbsp;&nbsp;hour&nbsp;&nbsp;day-of-month&nbsp;&nbsp;month&nbsp;&nbsp;day-of-week</span>
            &nbsp;·&nbsp; * = any &nbsp;·&nbsp; */N = every N &nbsp;·&nbsp; 1,3,5 = list &nbsp;·&nbsp; 1-5 = range
          </p>
        </div>
      </div>

      <!-- Preview -->
      <div v-if="previewCron" class="mb-6 flex items-center gap-4 px-4 py-3 bg-blue-950/60 border border-blue-800/60 rounded-xl">
        <span class="w-2 h-2 rounded-full bg-blue-400 flex-shrink-0 animate-pulse"></span>
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium text-blue-200">{{ describeCron(previewCron) }}</p>
          <p v-if="previewNext" class="text-xs text-gray-400 mt-0.5">
            Next run: <span class="text-gray-300">{{ formatNextFull(previewNext) }}</span>
          </p>
        </div>
        <code class="text-xs font-mono text-gray-500 flex-shrink-0">{{ previewCron }}</code>
      </div>

      <!-- Validation hint -->
      <p v-if="formError" class="mb-4 text-xs text-red-400">{{ formError }}</p>

      <!-- Actions -->
      <div class="flex items-center gap-3">
        <button
          @click="saveForm"
          :disabled="!canSave || formSaving"
          class="px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium rounded-lg transition-colors"
        >{{ formSaving ? 'Saving...' : (editingId ? 'Update' : 'Create schedule') }}</button>
        <button @click="closeForm"
          class="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 text-sm rounded-lg transition-colors">
          Cancel
        </button>
      </div>
    </div>

    <!-- ── Scheduled tasks table ───────────────────────────────────────────── -->
    <div v-if="loading" class="text-gray-400 text-center py-16">Loading...</div>

    <div v-else-if="scheduledResources.length === 0 && !showForm"
      class="text-center py-20 text-gray-600">
      <p class="text-4xl mb-4">🕐</p>
      <p class="text-lg font-medium text-gray-500 mb-1">No scheduled tasks</p>
      <p class="text-sm mb-5">Create a schedule to automate resource dataset refresh</p>
      <button @click="openNew"
        class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition-colors">
        + Create your first schedule
      </button>
    </div>

    <div v-else-if="scheduledResources.length > 0" class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead>
          <tr class="border-b border-gray-700 bg-gray-800/50">
            <th class="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Resource</th>
            <th class="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Schedule</th>
            <th class="text-left px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Next run</th>
            <th class="text-right px-5 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-700/60">
          <tr
            v-for="res in scheduledResources" :key="res.id"
            class="hover:bg-gray-800/40 transition-colors"
          >
            <td class="px-5 py-4">
              <div class="flex items-center gap-2">
                <span class="font-medium text-white">{{ res.name }}</span>
                <span v-if="res.fetcher"
                  class="text-xs bg-gray-700/80 text-gray-400 px-1.5 py-0.5 rounded font-mono">
                  {{ res.fetcher.code }}
                </span>
                <span v-if="!res.active"
                  class="text-xs bg-yellow-900/60 text-yellow-500 px-1.5 py-0.5 rounded">
                  inactive
                </span>
              </div>
              <p class="text-xs text-gray-500 mt-0.5">{{ res.publisher }}</p>
            </td>
            <td class="px-5 py-4">
              <p class="text-gray-200 font-medium">{{ describeCron(res.schedule) }}</p>
              <code class="text-xs text-gray-600 mt-0.5">{{ res.schedule }}</code>
            </td>
            <td class="px-5 py-4">
              <span class="text-gray-300 text-xs">{{ formatNextFull(nextRun(res.schedule)) }}</span>
            </td>
            <td class="px-5 py-4">
              <div class="flex items-center justify-end gap-1">
                <button @click="openEdit(res)"
                  class="px-3 py-1.5 text-xs text-blue-400 hover:text-blue-300 hover:bg-gray-700 rounded-md transition-colors">
                  Edit
                </button>
                <button @click="confirmRemove(res)"
                  class="px-3 py-1.5 text-xs text-red-400 hover:text-red-300 hover:bg-gray-700 rounded-md transition-colors">
                  Remove
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

  </div>

  <!-- Confirm dialog -->
  <ConfirmDialog
    v-if="dialog.show"
    :title="dialog.title"
    :message="dialog.message"
    :confirmText="dialog.confirmText"
    :dangerMode="true"
    @confirm="handleDialogConfirm"
    @cancel="dialog.show = false"
  />
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue'
import { fetchResources, updateResource } from '../api/graphql.js'
import ConfirmDialog from '../components/ConfirmDialog.vue'

// ─── Constants ────────────────────────────────────────────────────────────────

const MODES = [
  { key: 'minutes', label: 'Every N min' },
  { key: 'hourly',  label: 'Hourly'      },
  { key: 'daily',   label: 'Daily'       },
  { key: 'weekly',  label: 'Weekly'      },
  { key: 'monthly', label: 'Monthly'     },
  { key: 'custom',  label: 'Custom cron' },
]

const WEEK_DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

// ─── State ────────────────────────────────────────────────────────────────────

const resources = ref([])
const loading   = ref(true)

const showForm    = ref(false)
const editingId   = ref(null)   // null = new, string = editing resource id
const formSaving  = ref(false)
const formError   = ref('')

const form = reactive({
  resourceId: '',
  mode:       'daily',
  interval:   15,   // for 'minutes'
  minute:     0,
  hour:       6,
  weekdays:   [1],  // default: Monday
  monthDay:   1,
  cron:       '',
})

// ─── Derived ──────────────────────────────────────────────────────────────────

const scheduledResources = computed(() =>
  resources.value.filter(r => r.schedule)
)

const unscheduledResources = computed(() =>
  resources.value.filter(r => !r.schedule)
)

const editingResource = computed(() =>
  editingId.value ? resources.value.find(r => r.id === editingId.value) : null
)

const previewCron = computed(() => {
  const c = buildCron()
  return c && isValidCron(c) ? c : null
})

const previewNext = computed(() => nextRun(previewCron.value))

const canSave = computed(() => {
  if (!editingId.value && !form.resourceId) return false
  return !!previewCron.value
})

// ─── Form helpers ─────────────────────────────────────────────────────────────

function resetForm() {
  form.resourceId = ''
  form.mode       = 'daily'
  form.interval   = 15
  form.minute     = 0
  form.hour       = 6
  form.weekdays   = [1]
  form.monthDay   = 1
  form.cron       = ''
  formError.value = ''
}

function setMode(mode) {
  form.mode = mode
}

function toggleDay(i) {
  const idx = form.weekdays.indexOf(i)
  if (idx === -1) {
    form.weekdays.push(i)
    form.weekdays.sort((a, b) => a - b)
  } else if (form.weekdays.length > 1) {
    form.weekdays.splice(idx, 1)
  }
}

function openNew() {
  resetForm()
  editingId.value = null
  showForm.value  = true
}

function openEdit(res) {
  resetForm()
  editingId.value = res.id
  parseCronIntoForm(res.schedule)
  showForm.value  = true
}

function closeForm() {
  showForm.value  = false
  editingId.value = null
  formError.value = ''
}

async function saveForm() {
  formError.value = ''
  const cron = buildCron()
  if (!cron || !isValidCron(cron)) {
    formError.value = 'Invalid schedule configuration.'
    return
  }
  const id = editingId.value || form.resourceId
  if (!id) {
    formError.value = 'Select a resource.'
    return
  }
  formSaving.value = true
  try {
    await updateResource(id, { schedule: cron })
    const res = resources.value.find(r => r.id === id)
    if (res) res.schedule = cron
    closeForm()
  } catch (e) {
    formError.value = 'Save failed: ' + e.message
  } finally {
    formSaving.value = false
  }
}

const dialog = ref({ show: false, title: '', message: '', confirmText: 'Confirm', _resolve: null })

function showConfirm(title, message, confirmText = 'Confirm') {
  return new Promise(resolve => {
    dialog.value = { show: true, title, message, confirmText, _resolve: resolve }
  })
}

function handleDialogConfirm() {
  dialog.value.show = false
  dialog.value._resolve?.(true)
}

async function confirmRemove(res) {
  const ok = await showConfirm('Eliminar programación', `¿Eliminar la programación de "${res.name}"?`, 'Eliminar')
  if (!ok) return
  await updateResource(res.id, { schedule: '' })
  res.schedule = null
}

// ─── Cron build / parse ───────────────────────────────────────────────────────

function buildCron() {
  const m = String(form.minute ?? 0)
  const h = String(form.hour ?? 0)
  switch (form.mode) {
    case 'minutes': return `*/${Math.max(1, form.interval ?? 15)} * * * *`
    case 'hourly':  return `${m} * * * *`
    case 'daily':   return `${m} ${h} * * *`
    case 'weekly': {
      const days = form.weekdays.length ? form.weekdays.join(',') : '1'
      return `${m} ${h} * * ${days}`
    }
    case 'monthly': return `${m} ${h} ${form.monthDay ?? 1} * *`
    case 'custom':  return form.cron.trim()
    default:        return ''
  }
}

function parseCronIntoForm(expr) {
  if (!expr || !isValidCron(expr)) return
  const [min, hour, dom, mon, dow] = expr.trim().split(/\s+/)

  if (min.startsWith('*/') && hour === '*' && dom === '*' && mon === '*' && dow === '*') {
    form.mode     = 'minutes'
    form.interval = parseInt(min.slice(2))
    return
  }
  if (!min.startsWith('*') && hour === '*' && dom === '*' && mon === '*' && dow === '*') {
    form.mode   = 'hourly'
    form.minute = parseInt(min)
    return
  }
  if (/^\d+$/.test(min) && /^\d+$/.test(hour) && dom === '*' && mon === '*' && dow === '*') {
    form.mode   = 'daily'
    form.hour   = parseInt(hour)
    form.minute = parseInt(min)
    return
  }
  if (/^\d+$/.test(min) && /^\d+$/.test(hour) && dom === '*' && mon === '*' && dow !== '*') {
    form.mode     = 'weekly'
    form.hour     = parseInt(hour)
    form.minute   = parseInt(min)
    form.weekdays = dow.split(',').map(Number)
    return
  }
  if (/^\d+$/.test(min) && /^\d+$/.test(hour) && /^\d+$/.test(dom) && mon === '*' && dow === '*') {
    form.mode     = 'monthly'
    form.hour     = parseInt(hour)
    form.minute   = parseInt(min)
    form.monthDay = parseInt(dom)
    return
  }
  // fallback
  form.mode = 'custom'
  form.cron = expr
}

// ─── Cron description ─────────────────────────────────────────────────────────

function isValidCron(expr) {
  return !!expr && expr.trim().split(/\s+/).length === 5
}

function pad(n) { return String(n).padStart(2, '0') }

function describeCron(expr) {
  if (!isValidCron(expr)) return ''
  const [min, hour, dom, mon, dow] = expr.trim().split(/\s+/)

  if (min.startsWith('*/') && hour === '*' && dom === '*' && mon === '*' && dow === '*')
    return `Every ${min.slice(2)} minutes`

  if (/^\d+$/.test(min) && hour === '*' && dom === '*' && mon === '*' && dow === '*')
    return `Hourly at :${pad(min)}`

  if (/^\d+$/.test(min) && /^\d+$/.test(hour) && dom === '*' && mon === '*' && dow === '*')
    return `Daily at ${pad(hour)}:${pad(min)}`

  if (/^\d+$/.test(min) && /^\d+$/.test(hour) && dom === '*' && mon === '*' && dow !== '*') {
    const dayNames = dow.split(',').map(d => WEEK_DAYS[+d] ?? d).join(', ')
    return `Weekly on ${dayNames} at ${pad(hour)}:${pad(min)}`
  }

  if (/^\d+$/.test(min) && /^\d+$/.test(hour) && /^\d+$/.test(dom) && mon === '*' && dow === '*')
    return `Monthly on day ${dom} at ${pad(hour)}:${pad(min)}`

  return expr
}

// ─── Next run calculation ─────────────────────────────────────────────────────

function matchField(value, field) {
  if (field === '*') return true
  if (field.startsWith('*/')) return value % parseInt(field.slice(2)) === 0
  if (field.includes(','))    return field.split(',').map(Number).includes(value)
  if (field.includes('-'))    { const [lo, hi] = field.split('-').map(Number); return value >= lo && value <= hi }
  return parseInt(field) === value
}

function nextRun(expr) {
  if (!isValidCron(expr)) return null
  const [min, hour, dom, mon, dow] = expr.trim().split(/\s+/)
  const t = new Date()
  t.setSeconds(0, 0)
  t.setMinutes(t.getMinutes() + 1)
  for (let i = 0; i < 60 * 24 * 35; i++) {
    if (
      matchField(t.getMinutes(),   min)  &&
      matchField(t.getHours(),     hour) &&
      matchField(t.getDate(),      dom)  &&
      matchField(t.getMonth() + 1, mon)  &&
      matchField(t.getDay(),       dow)
    ) return new Date(t)
    t.setMinutes(t.getMinutes() + 1)
  }
  return null
}

function formatNextFull(date) {
  if (!date) return '—'
  const diffMs = date - Date.now()
  const diffM  = Math.round(diffMs / 60000)
  const diffH  = Math.round(diffMs / 3600000)
  const diffD  = Math.round(diffMs / 86400000)

  const timeStr = date.toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit' })
  if (diffM  <  90) return `in ${diffM}m  (${timeStr})`
  if (diffH  <  24) return `in ${diffH}h  (${timeStr})`
  if (diffD  <   7) return `${date.toLocaleDateString(undefined, { weekday: 'short' })} ${timeStr}`
  return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

// ─── Init ─────────────────────────────────────────────────────────────────────

onMounted(async () => {
  try {
    const data = await fetchResources(false)
    resources.value = data?.resources ?? []
  } finally {
    loading.value = false
  }
})
</script>
