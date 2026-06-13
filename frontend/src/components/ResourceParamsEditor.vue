<template>
  <div class="rpe">
    <div v-if="!fetcher" class="rpe-empty">Elige un fetcher para configurar sus parámetros.</div>

    <template v-else>
      <div v-for="f in fields" :key="f.name" class="rpe-field" :class="{ wide: isWide(f.def) }">
        <div class="rpe-head">
          <label>
            {{ f.name }}
            <span v-if="f.required" class="rpe-req">*</span>
          </label>
          <div class="rpe-actions">
            <label class="rpe-ext" :title="'Marca el parámetro como aportado externamente'">
              <input type="checkbox" :checked="isExternal(f.name)" @change="toggleExternal(f.name)"> externo
            </label>
            <button v-if="!f.required" type="button" class="rpe-rm" @click="removeParam(f.name)" title="Quitar parámetro">✕</button>
          </div>
        </div>
        <p v-if="f.def.description" class="rpe-desc">{{ f.def.description }}</p>

        <!-- enum -->
        <div v-if="f.def.dataType === 'enum' && f.def.enumValues">
          <EnumRadioGroup
            :options="enumOpts(f.def.enumValues)"
            :model-value="getParamValue(f.name)"
            clearable
            @update:model-value="v => updateParamValue(f.name, v)" />
          <EnumMetaPreview :filters="selectedEnumMeta(f.name, f.def.enumValues, 'filters')" />
        </div>

        <!-- json_filter_map -->
        <FilterMapEditor
          v-else-if="f.def.dataType === 'json_filter_map'"
          :model-value="getParamValue(f.name) || '{}'"
          :enum-values="f.def.enumValues || {}"
          @update:model-value="v => updateParamValue(f.name, v)" />

        <!-- overpass_query -->
        <div v-else-if="f.def.dataType === 'overpass_query'" class="rpe-overpass">
          <span class="rpe-summary" :title="getParamValue(f.name)">{{ overpassSummary(f.name) }}</span>
          <button type="button" class="rpe-btn" @click="overpassFor = f.name">Editar consulta</button>
        </div>

        <!-- bbox -->
        <div v-else-if="f.def.dataType === 'bbox'" class="rpe-bbox">
          <input v-for="(part, i) in parseBbox(getParamValue(f.name))" :key="i"
                 :value="part" @input="e => updateBbox(f.name, i, e.target.value)"
                 :placeholder="['sur','oeste','norte','este'][i]">
        </div>

        <!-- default -->
        <input v-else class="rpe-inp"
               :value="getParamValue(f.name)"
               @input="e => updateParamValue(f.name, e.target.value)"
               :placeholder="f.def.defaultValue ? ('por defecto: ' + f.def.defaultValue) : ''">
      </div>

      <div v-if="availableOptional.length" class="rpe-add">
        <select v-model="selectedOptional" class="rpe-inp">
          <option value="">＋ Añadir parámetro opcional…</option>
          <option v-for="p in availableOptional" :key="p.paramName" :value="p.paramName">{{ p.paramName }}</option>
        </select>
        <button type="button" class="rpe-btn" :disabled="!selectedOptional" @click="addSelectedOptional">Añadir</button>
      </div>
    </template>

    <OverpassQueryModal
      v-if="overpassFor"
      :model-value="getParamValue(overpassFor)"
      :presets="overpassPresetsOf(overpassFor)"
      @update:model-value="v => updateParamValue(overpassFor, v)"
      @close="overpassFor = null" />
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import EnumRadioGroup from './EnumRadioGroup.vue'
import EnumMetaPreview from './EnumMetaPreview.vue'
import FilterMapEditor from './FilterMapEditor.vue'
import OverpassQueryModal from './OverpassQueryModal.vue'

const props = defineProps({
  fetcher:    { type: Object, default: null },   // fetcher con paramsDef + presets
  presetId:   { type: String, default: '' },
  modelValue: { type: Array,  default: () => [] }, // [{key,value,isExternal}]
})
const emit = defineEmits(['update:modelValue'])

const params = computed(() => props.modelValue || [])
function setParams(next) { emit('update:modelValue', next) }
function entry(name) { return params.value.find(p => p.key === name) }
function getParamValue(name) { return entry(name)?.value ?? '' }
function updateParamValue(name, val) {
  let found = false
  const next = params.value.map(p => { if (p.key === name) { found = true; return { ...p, value: val } } return p })
  if (!found) next.push({ key: name, value: val, isExternal: false })
  setParams(next)
}
function isExternal(name) { return !!entry(name)?.isExternal }
function toggleExternal(name) {
  let found = false
  const next = params.value.map(p => { if (p.key === name) { found = true; return { ...p, isExternal: !p.isExternal } } return p })
  if (!found) next.push({ key: name, value: '', isExternal: true })
  setParams(next)
}
function removeParam(name) { setParams(params.value.filter(p => p.key !== name)) }
function addParam(name, def) { if (entry(name)) return; setParams([...params.value, { key: name, value: def ?? '', isExternal: false }]) }

const preset = computed(() => (props.fetcher?.presets || []).find(pr => pr.id === props.presetId) || null)
const presetParamNames = computed(() => new Set(Object.keys(preset.value?.params || {})))
const paramsDef = computed(() => props.fetcher?.paramsDef || [])
const requiredParams = computed(() => paramsDef.value.filter(p => p.required === true && !presetParamNames.value.has(p.paramName)))
const optionalParams = computed(() => paramsDef.value.filter(p => p.required !== true && !presetParamNames.value.has(p.paramName)))
const availableOptional = computed(() => {
  const cur = new Set(params.value.map(p => p.key))
  return optionalParams.value.filter(p => !cur.has(p.paramName))
})

function defOf(name) { return paramsDef.value.find(p => p.paramName === name) || {} }
const fields = computed(() => {
  const reqNames = new Set(requiredParams.value.map(p => p.paramName))
  const required = requiredParams.value.map(p => ({ name: p.paramName, def: p, required: true }))
  const optional = params.value.map(p => p.key).filter(n => !reqNames.has(n)).map(n => ({ name: n, def: defOf(n), required: false }))
  return [...required, ...optional]
})

function isWide(def) { return def.dataType === 'json_filter_map' || def.dataType === 'overpass_query' || def.dataType === 'bbox' }
function enumOpts(vals) { if (!vals) return []; return (Array.isArray(vals) ? vals : []).map(v => typeof v === 'string' ? { value: v, label: v } : v) }
function selectedEnumMeta(name, vals, field) {
  const sel = getParamValue(name)
  if (!sel || !vals) return null
  return enumOpts(vals).find(o => o.value === sel)?.[field] ?? null
}
function overpassPresetsOf(name) { return defOf(name).enumValues || {} }
function overpassSummary(name) {
  const raw = getParamValue(name)
  if (!raw) return 'sin condiciones'
  try {
    const b = JSON.parse(raw)
    if (!Array.isArray(b) || !b.length) return 'sin condiciones'
    return b.map(x => x.preset || `(${x.pairs?.length || 0} pares)`).join(' + ')
  } catch { return String(raw).slice(0, 60) }
}
function parseBbox(v) { const p = String(v || '').split(',').map(s => s.trim()); while (p.length < 4) p.push(''); return p }
function updateBbox(name, i, v) { const c = parseBbox(getParamValue(name)); c[i] = v; updateParamValue(name, c.join(',')) }

const overpassFor = ref(null)
const selectedOptional = ref('')
function addSelectedOptional() {
  if (!selectedOptional.value) return
  addParam(selectedOptional.value, defOf(selectedOptional.value).defaultValue)
  selectedOptional.value = ''
}
</script>

<style scoped>
.rpe { display: flex; flex-direction: column; gap: .9rem; }
.rpe-empty { font-size: .8rem; color: #9ca3af; padding: .4rem 0; }
.rpe-field { display: flex; flex-direction: column; gap: .35rem; }
.rpe-head { display: flex; align-items: center; justify-content: space-between; gap: .5rem; }
.rpe-head label { font-size: .72rem; font-weight: 600; color: #cbd5e1; text-transform: none; }
.rpe-req { color: #f87171; margin-left: .15rem; }
.rpe-actions { display: flex; align-items: center; gap: .6rem; }
.rpe-ext { font-size: .68rem; color: #9ca3af; display: flex; align-items: center; gap: .25rem; cursor: pointer; }
.rpe-rm { color: #9ca3af; font-size: .8rem; border: 0; background: none; cursor: pointer; }
.rpe-rm:hover { color: #f87171; }
.rpe-desc { font-size: .68rem; color: #6b7280; margin: 0; }
.rpe-inp { width: 100%; background: #111827; border: 1px solid #374151; border-radius: .4rem; padding: .35rem .5rem; font-size: .78rem; color: #e5e7eb; }
.rpe-overpass { display: flex; align-items: center; gap: .5rem; }
.rpe-summary { flex: 1; font-size: .72rem; color: #9ca3af; font-family: monospace; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rpe-bbox { display: grid; grid-template-columns: repeat(4, 1fr); gap: .35rem; }
.rpe-bbox input { background: #111827; border: 1px solid #374151; border-radius: .4rem; padding: .3rem .4rem; font-size: .74rem; color: #e5e7eb; }
.rpe-add { display: flex; gap: .5rem; padding-top: .2rem; }
.rpe-btn { font-size: .74rem; background: #2563eb; color: #fff; border: 0; border-radius: .4rem; padding: .35rem .7rem; cursor: pointer; }
.rpe-btn:disabled { opacity: .5; cursor: default; }
.rpe-btn:hover:not(:disabled) { background: #3b82f6; }
</style>
