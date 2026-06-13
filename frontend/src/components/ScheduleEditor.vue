<template>
  <div class="sched">
    <div class="row">
      <label>Periodicidad</label>
      <select v-model="mode" @change="onMode" class="sinp">
        <option value="manual">Manual (sin programación)</option>
        <option value="cada_n">Cada N minutos</option>
        <option value="horaria">Cada hora</option>
        <option value="diaria">Diaria</option>
        <option value="semanal">Semanal</option>
        <option value="mensual_dia">Mensual (día del mes)</option>
        <option value="mensual_semana">Mensual (día de la semana)</option>
        <option value="custom">Avanzado (cron)</option>
      </select>
    </div>

    <div v-if="mode === 'cada_n'" class="row">
      <label>Cada</label>
      <input type="number" min="1" max="59" v-model.number="every" @input="emit_" class="sinp narrow"> minutos
    </div>

    <div v-if="mode === 'horaria'" class="row">
      <label>En el minuto</label>
      <input type="number" min="0" max="59" v-model.number="minute" @input="emit_" class="sinp narrow"> de cada hora
    </div>

    <div v-if="mode === 'semanal'" class="row">
      <label>Días</label>
      <div class="dows">
        <button v-for="(d,i) in DOW" :key="i" type="button" :class="['dow',{on:weekdays.includes(i)}]" @click="toggleDow(i)">{{ d }}</button>
      </div>
    </div>

    <div v-if="mode === 'mensual_dia'" class="row">
      <label>Día del mes</label>
      <input type="number" min="1" max="28" v-model.number="monthDay" @input="emit_" class="sinp narrow">
    </div>

    <div v-if="mode === 'mensual_semana'" class="row">
      <label>El</label>
      <select v-model.number="nth" @change="emit_" class="sinp">
        <option :value="1">primer</option><option :value="2">segundo</option>
        <option :value="3">tercer</option><option :value="4">cuarto</option>
      </select>
      <select v-model.number="nthDow" @change="emit_" class="sinp">
        <option v-for="(d,i) in DOW_FULL" :key="i" :value="i">{{ d }}</option>
      </select>
      <span>de cada mes</span>
    </div>

    <div v-if="needsTime" class="row">
      <label>Hora de ejecución</label>
      <input type="time" v-model="time" @input="emit_" class="sinp time">
    </div>

    <div v-if="mode === 'custom'" class="row">
      <label>Cron</label>
      <input type="text" v-model="raw" @input="onRaw" placeholder="0 2 1-7 * 5" class="sinp mono">
    </div>

    <p class="summary">{{ summary }}</p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({ modelValue: { type: String, default: '' } })
const emit = defineEmits(['update:modelValue'])

const DOW = ['Dom','Lun','Mar','Mié','Jue','Vie','Sáb']
const DOW_FULL = ['domingo','lunes','martes','miércoles','jueves','viernes','sábado']
const NTH = ['', 'primer', 'segundo', 'tercer', 'cuarto']
const NTH_DOM = { 1:'1-7', 2:'8-14', 3:'15-21', 4:'22-28' }

const mode = ref('manual')
const minute = ref(0)
const hour = ref(4)
const every = ref(15)
const weekdays = ref([1])
const monthDay = ref(1)
const nth = ref(1)
const nthDow = ref(5)
const raw = ref('')

const time = computed({
  get: () => `${String(hour.value).padStart(2,'0')}:${String(minute.value).padStart(2,'0')}`,
  set: (v) => { const [h,m] = String(v).split(':'); hour.value = +h||0; minute.value = +m||0 },
})
const needsTime = computed(() => ['diaria','semanal','mensual_dia','mensual_semana'].includes(mode.value))

function pad(n){ return String(n).padStart(2,'0') }

function build() {
  const m = minute.value || 0, h = hour.value || 0
  switch (mode.value) {
    case 'manual': return ''
    case 'cada_n': return `*/${Math.max(1, every.value||1)} * * * *`
    case 'horaria': return `${m} * * * *`
    case 'diaria': return `${m} ${h} * * *`
    case 'semanal': return `${m} ${h} * * ${(weekdays.value.length?weekdays.value:[1]).slice().sort((a,b)=>a-b).join(',')}`
    case 'mensual_dia': return `${m} ${h} ${Math.min(28, Math.max(1, monthDay.value||1))} * *`
    case 'mensual_semana': return `${m} ${h} ${NTH_DOM[nth.value]||'1-7'} * ${nthDow.value}`
    case 'custom': return raw.value.trim()
  }
  return ''
}

const summary = computed(() => {
  const c = build()
  if (mode.value === 'manual' || !c) return 'No se ejecuta automáticamente (manual).'
  if (mode.value === 'cada_n') return `Cada ${every.value} minutos.`
  if (mode.value === 'horaria') return `Cada hora, en el minuto ${minute.value}.`
  const at = `a las ${pad(hour.value)}:${pad(minute.value)}`
  if (mode.value === 'diaria') return `Todos los días ${at}.`
  if (mode.value === 'semanal') { const ds = weekdays.value.slice().sort((a,b)=>a-b).map(i=>DOW_FULL[i]).join(', '); return `Cada ${ds} ${at}.` }
  if (mode.value === 'mensual_dia') return `El día ${monthDay.value} de cada mes ${at}.`
  if (mode.value === 'mensual_semana') return `El ${NTH[nth.value]} ${DOW_FULL[nthDow.value]} de cada mes ${at}.`
  return `Cron: ${c}`
})

function emit_() { emit('update:modelValue', build()) }
function onMode() { emit_() }
function onRaw() { emit('update:modelValue', raw.value.trim()) }
function toggleDow(i) { const s = new Set(weekdays.value); s.has(i) ? s.delete(i) : s.add(i); weekdays.value = [...s]; emit_() }

// Parsear un cron entrante al modo humano más cercano
function parse(expr) {
  raw.value = expr || ''
  if (!expr || !expr.trim()) { mode.value = 'manual'; return }
  const p = expr.trim().split(/\s+/)
  if (p.length !== 5) { mode.value = 'custom'; return }
  const [mi, ho, dom, mon, dow] = p
  const setT = () => { minute.value = +mi||0; hour.value = +ho||0 }
  if (mon !== '*') { mode.value = 'custom'; return }
  if (/^\*\/\d+$/.test(mi) && ho==='*' && dom==='*' && dow==='*') { mode.value='cada_n'; every.value = +mi.split('/')[1]||15; return }
  if (/^\d+$/.test(mi) && ho==='*' && dom==='*' && dow==='*') { mode.value='horaria'; minute.value=+mi; return }
  if (/^\d+$/.test(mi) && /^\d+$/.test(ho)) {
    if (dom==='*' && dow==='*') { mode.value='diaria'; setT(); return }
    if (dom==='*' && /^[0-6](,[0-6])*$/.test(dow)) { mode.value='semanal'; setT(); weekdays.value=dow.split(',').map(Number); return }
    if (/^\d+$/.test(dom) && dow==='*') { mode.value='mensual_dia'; setT(); monthDay.value=+dom; return }
    const nthEntry = Object.entries(NTH_DOM).find(([,r])=>r===dom)
    if (nthEntry && /^[0-6]$/.test(dow)) { mode.value='mensual_semana'; setT(); nth.value=+nthEntry[0]; nthDow.value=+dow; return }
  }
  mode.value = 'custom'
}

watch(() => props.modelValue, (v) => { if (v !== build()) parse(v) }, { immediate: true })
</script>

<style scoped>
.sched{display:flex;flex-direction:column;gap:.7rem}
.row{display:flex;align-items:center;gap:.6rem;flex-wrap:wrap;font-size:.8rem;color:#cbd5e1}
.row > label{min-width:7.5rem;font-size:.72rem;font-weight:600;color:#9ca3af}
.sinp{background:#111827;border:1px solid #374151;border-radius:.4rem;padding:.35rem .5rem;font-size:.8rem;color:#e5e7eb}
.sinp.narrow{width:4.5rem;text-align:center}
.sinp.time{width:7rem}
.sinp.mono{font-family:monospace;flex:1;min-width:10rem}
.dows{display:flex;gap:.3rem;flex-wrap:wrap}
.dow{width:2.2rem;height:2.2rem;border-radius:999px;border:1px solid #374151;background:#1f2937;color:#9ca3af;font-size:.7rem;font-weight:700;cursor:pointer}
.dow.on{background:#2563eb;border-color:#3b82f6;color:#fff}
.summary{margin:.2rem 0 0;font-size:.78rem;color:#3FE0CB}
</style>
