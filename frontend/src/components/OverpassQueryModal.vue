<template>
  <!-- Backdrop -->
  <Teleport to="body">
    <div
      class="fixed inset-0 z-[60] flex items-center justify-center bg-black/70"
      @click.self="cancel"
    >
      <div
        class="relative bg-gray-900 border border-gray-700 rounded-xl shadow-2xl
               w-full max-w-5xl max-h-[90vh] flex flex-col overflow-hidden"
        @click.stop
      >
        <!-- ── Header ───────────────────────────────────────────────────── -->
        <div class="flex items-center justify-between px-5 py-3 border-b border-gray-700 flex-shrink-0">
          <div>
            <h3 class="font-semibold text-white">Overpass Query Builder</h3>
            <p class="text-xs text-gray-500 mt-0.5">
              Selecciona presets de la biblioteca o añade condiciones personalizadas
            </p>
          </div>
          <button @click="cancel" class="text-gray-500 hover:text-white text-xl leading-none">✕</button>
        </div>

        <!-- ── Body (dos columnas) ────────────────────────────────────────── -->
        <div class="flex flex-1 min-h-0 divide-x divide-gray-700">

          <!-- ══ Columna izquierda: biblioteca de presets ══════════════════ -->
          <div class="w-64 flex-shrink-0 flex flex-col overflow-hidden">
            <div class="px-3 py-2 border-b border-gray-800 flex-shrink-0">
              <span class="text-xs font-semibold uppercase tracking-wider text-gray-500">
                Biblioteca de presets
              </span>
            </div>
            <div class="flex-1 overflow-y-auto">
              <div
                v-for="(group, gname) in presetGroups"
                :key="gname"
                class="border-b border-gray-800 last:border-b-0"
              >
                <!-- Categoría -->
                <button
                  @click="toggleCategory(gname)"
                  class="w-full flex items-center justify-between px-3 py-2
                         hover:bg-gray-800/50 transition-colors"
                >
                  <span class="flex items-center gap-1.5">
                    <span :class="['w-2 h-2 rounded-full flex-shrink-0', groupBar(gname)]" />
                    <span class="text-xs font-semibold text-gray-300">{{ gname }}</span>
                  </span>
                  <span class="text-gray-600 text-xs">{{ openCategories[gname] ? '▲' : '▼' }}</span>
                </button>

                <!-- Presets de la categoría -->
                <div v-if="openCategories[gname]" class="pb-1">
                  <button
                    v-for="p in group"
                    :key="p.key"
                    @click="togglePreset(p.key)"
                    class="w-full text-left px-4 py-1.5 flex items-start justify-between gap-2
                           hover:bg-gray-800 transition-colors group"
                  >
                    <span class="flex-1 min-w-0">
                      <span :class="['text-xs leading-snug', isActive(p.key) ? categoryColor(p.key) : 'text-gray-400 group-hover:text-gray-200']">
                        {{ p.label }}
                      </span>
                      <span class="block text-gray-700 font-mono mt-0.5" style="font-size:9px;">
                        {{ pairSummary(p.key) }}
                      </span>
                    </span>
                    <span
                      :class="[
                        'flex-shrink-0 mt-0.5 w-4 h-4 rounded flex items-center justify-center text-xs font-bold transition-colors',
                        isActive(p.key)
                          ? 'bg-blue-600 text-white'
                          : 'border border-gray-600 text-gray-600 group-hover:border-gray-400 group-hover:text-gray-300'
                      ]"
                    >{{ isActive(p.key) ? '✓' : '+' }}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- ══ Columna derecha: bloques activos + query live ═════════════ -->
          <div class="flex-1 flex flex-col min-w-0 overflow-hidden">

            <!-- Bloques activos -->
            <div class="flex-1 overflow-y-auto p-3 space-y-2">
              <div v-if="!blocks.length" class="h-full flex flex-col items-center justify-center text-gray-600 gap-2">
                <span class="text-4xl">⊕</span>
                <span class="text-sm">Selecciona presets de la biblioteca</span>
                <span class="text-xs">o añade condiciones personalizadas abajo</span>
              </div>

              <div
                v-for="(block, idx) in blocks"
                :key="idx"
                class="flex items-start gap-2.5 p-2.5 rounded-lg border border-gray-700
                       bg-gray-800/50 group hover:border-gray-600 transition-colors"
              >
                <!-- Barra de color -->
                <div :class="['w-1 self-stretch rounded-full flex-shrink-0', categoryBar(block.preset)]" />

                <div class="flex-1 min-w-0 space-y-1.5">
                  <div class="flex items-center gap-2">
                    <span :class="['text-xs font-mono font-semibold', categoryColor(block.preset)]">
                      {{ block.preset || 'custom' }}
                    </span>
                    <span :class="[
                      'px-1.5 py-px rounded font-mono font-bold tracking-wider',
                      block.mode === 'or'
                        ? 'bg-orange-900/60 text-orange-400 border border-orange-800'
                        : 'bg-blue-900/60 text-blue-400 border border-blue-800'
                    ]" style="font-size:9px;">
                      {{ block.mode === 'or' ? 'OR' : 'AND' }}
                    </span>
                  </div>
                  <div class="flex flex-wrap gap-1">
                    <span
                      v-for="(pair, pi) in block.pairs"
                      :key="pi"
                      class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded
                             bg-gray-900 border border-gray-700 font-mono text-xs"
                    >
                      <span class="text-yellow-400">{{ pair[0] }}</span>
                      <span class="text-gray-600">=</span>
                      <span class="text-green-400">{{ pair[1] === '*' ? '<any>' : pair[1] }}</span>
                    </span>
                  </div>
                </div>

                <button
                  @click="removeBlock(idx)"
                  class="opacity-0 group-hover:opacity-100 flex-shrink-0 text-gray-600
                         hover:text-red-400 transition-all mt-0.5"
                >✕</button>
              </div>

              <!-- Condición personalizada -->
              <div class="border border-dashed border-gray-700 rounded-lg p-2.5">
                <div class="text-xs text-gray-600 mb-2 font-medium">Condición personalizada</div>
                <div class="flex items-center gap-2 flex-wrap">
                  <input
                    v-model="customKey"
                    placeholder="key"
                    class="w-28 bg-gray-950 border border-gray-700 rounded px-2 py-1
                           text-yellow-400 font-mono text-xs focus:outline-none focus:border-yellow-700"
                  />
                  <span class="text-gray-600 text-xs">=</span>
                  <input
                    v-model="customVal"
                    placeholder="value  (* = any)"
                    class="w-40 bg-gray-950 border border-gray-700 rounded px-2 py-1
                           text-green-400 font-mono text-xs focus:outline-none focus:border-green-800"
                  />
                  <label class="flex items-center gap-1 text-xs text-gray-500 cursor-pointer select-none">
                    <input type="checkbox" v-model="customOr" class="accent-orange-500" />
                    OR
                  </label>
                  <button
                    @click="addCustomPair"
                    :disabled="!customKey.trim()"
                    class="px-2 py-1 rounded text-xs bg-gray-700 hover:bg-gray-600 text-gray-300
                           disabled:opacity-40 disabled:cursor-not-allowed"
                  >+ Añadir</button>
                </div>
              </div>
            </div>

            <!-- Query live -->
            <div class="border-t border-gray-700 flex-shrink-0">
              <div class="flex items-center justify-between px-3 py-1.5 bg-gray-800/60">
                <span class="text-xs text-gray-500 font-medium uppercase tracking-wider">Overpass QL</span>
                <button
                  @click="copyQuery"
                  class="text-xs text-gray-600 hover:text-gray-300 transition-colors px-2 py-0.5
                         rounded border border-gray-700 hover:border-gray-500"
                >{{ copied ? '✓ copiado' : 'copiar' }}</button>
              </div>
              <pre
                class="px-3 py-2.5 text-xs font-mono text-green-300 bg-gray-950
                       overflow-x-auto leading-relaxed max-h-40"
                v-text="queryPreview"
              />
            </div>
          </div>
        </div>

        <!-- ── Footer ───────────────────────────────────────────────────── -->
        <div class="flex items-center justify-between px-5 py-3 border-t border-gray-700 flex-shrink-0 bg-gray-850">
          <span class="text-xs text-gray-600">
            {{ blocks.length }} bloque{{ blocks.length !== 1 ? 's' : '' }}
            · {{ uniqueQueryLines }} sentencias Overpass
          </span>
          <div class="flex gap-2">
            <button
              @click="cancel"
              class="px-3 py-1.5 rounded text-sm text-gray-400 hover:text-gray-200
                     border border-gray-700 hover:border-gray-500 transition-colors"
            >Cancelar</button>
            <button
              @click="save"
              class="px-4 py-1.5 rounded text-sm font-medium bg-blue-600 hover:bg-blue-500
                     text-white transition-colors"
            >Guardar</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  modelValue:   { type: String,          default: '' },
  presets:      { type: Object,          default: () => ({}) },
  demarcacion:  { type: String,          default: 'España' },
  elementTypes: { type: String,          default: 'node,way' },
  timeout:      { type: [String,Number], default: 60 },
  outFormat:    { type: String,          default: 'center' },
})
const emit = defineEmits(['update:modelValue', 'close'])

// ── Estado ──────────────────────────────────────────────────────────────────
const blocks      = ref([])
const customKey   = ref('')
const customVal   = ref('')
const customOr    = ref(false)
const copied      = ref(false)

// Inicializar copia de trabajo (no editamos el modelValue directamente)
watch(() => props.modelValue, (val) => {
  blocks.value = parseModelValue(val)
}, { immediate: true })

function parseModelValue(val) {
  if (!val) return []
  try {
    const p = JSON.parse(val)
    if (!Array.isArray(p)) return []
    return p.map(b => typeof b === 'string' ? presetToBlock(b.toUpperCase()) : b)
  } catch { return [] }
}

// ── Categorías ───────────────────────────────────────────────────────────────
const PRESET_GROUPS = {
  'Religioso':      ['RELIGIOUS_CATHOLIC_STRICT','RELIGIOUS_CATHOLIC_LOOSE','RELIGIOUS_ALL','RELIGIOUS_BUILDING_EXTRA'],
  'Educación':      ['EDUCATION_STRICT','EDUCATION_LOOSE','EDUCATION_BUILDING_EXTRA'],
  'Salud':          ['HEALTHCARE_STRICT','HEALTHCARE_LOOSE','HEALTHCARE_BUILDING_EXTRA'],
  'Administración': ['PUBLIC_ADMIN_STRICT','PUBLIC_ADMIN_LOOSE'],
  'Patrimonio':     ['HERITAGE_STRICT','HERITAGE_LOOSE'],
  'Turismo':        ['TOURISM'],
  'Emergencias':    ['EMERGENCY'],
  'Transporte':     ['TRANSPORT_STRICT','TRANSPORT_LOOSE'],
}

const GROUP_COLORS = {
  'Religioso':      { bar: 'bg-purple-600', text: 'text-purple-400' },
  'Educación':      { bar: 'bg-blue-600',   text: 'text-blue-400'   },
  'Salud':          { bar: 'bg-emerald-600',text: 'text-emerald-400'},
  'Administración': { bar: 'bg-violet-600', text: 'text-violet-400' },
  'Patrimonio':     { bar: 'bg-amber-600',  text: 'text-amber-400'  },
  'Turismo':        { bar: 'bg-cyan-600',   text: 'text-cyan-400'   },
  'Emergencias':    { bar: 'bg-red-600',    text: 'text-red-400'    },
  'Transporte':     { bar: 'bg-slate-500',  text: 'text-slate-400'  },
}

// Detectar grupo de un preset key
function groupOfPreset(key) {
  if (!key) return null
  for (const [gname, keys] of Object.entries(PRESET_GROUPS))
    if (keys.includes(key)) return gname
  return null
}
function categoryColor(presetKey) {
  const g = groupOfPreset(presetKey)
  return GROUP_COLORS[g]?.text || 'text-gray-400'
}
function categoryBar(presetKey) {
  const g = groupOfPreset(presetKey)
  return GROUP_COLORS[g]?.bar || 'bg-gray-600'
}
function groupBar(gname) {
  return GROUP_COLORS[gname]?.bar || 'bg-gray-600'
}

const presetGroups = computed(() => {
  const result = {}
  for (const [gname, keys] of Object.entries(PRESET_GROUPS)) {
    const items = keys
      .filter(k => props.presets[k])
      .map(k => ({ key: k, label: props.presets[k].label || k }))
    if (items.length) result[gname] = items
  }
  const grouped = Object.values(PRESET_GROUPS).flat()
  const others = Object.keys(props.presets)
    .filter(k => !grouped.includes(k))
    .map(k => ({ key: k, label: props.presets[k].label || k }))
  if (others.length) result['Otros'] = others
  return result
})

// Categorías abiertas por defecto (todas abiertas)
const openCategories = ref(
  Object.fromEntries(Object.keys(PRESET_GROUPS).map(g => [g, true]))
)
function toggleCategory(gname) {
  openCategories.value[gname] = !openCategories.value[gname]
}

// ── Helpers ───────────────────────────────────────────────────────────────
function isActive(key) {
  return blocks.value.some(b => b.preset === key)
}

function pairSummary(key) {
  const p = props.presets[key]
  if (!p) return ''
  const pairs = p.pairs || p.pairs_or || []
  return pairs.map(([k, v]) => `${k}=${v}`).join('  ·  ')
}

function presetToBlock(key) {
  const p = props.presets[key] || {}
  const pairs = p.pairs || p.pairs_or || []
  const mode  = p.pairs_or ? 'or' : 'and'
  return { preset: key, pairs, mode }
}

// ── Acciones ──────────────────────────────────────────────────────────────
function togglePreset(key) {
  if (isActive(key)) {
    blocks.value = blocks.value.filter(b => b.preset !== key)
  } else {
    blocks.value.push(presetToBlock(key))
  }
}

function addCustomPair() {
  if (!customKey.value.trim()) return
  const pair = [customKey.value.trim(), customVal.value.trim() || '*']
  const mode = customOr.value ? 'or' : 'and'
  const last = blocks.value[blocks.value.length - 1]
  if (last && !last.preset && last.mode === mode) {
    last.pairs.push(pair)
  } else {
    blocks.value.push({ preset: null, pairs: [pair], mode })
  }
  customKey.value = ''
  customVal.value = ''
}

function removeBlock(idx) {
  blocks.value.splice(idx, 1)
}

// ── Query live ────────────────────────────────────────────────────────────
const queryLines = computed(() => {
  if (!blocks.value.length) return []
  const etypes = (props.elementTypes || 'node,way').split(',').map(s => s.trim()).filter(Boolean)
  const demar  = props.demarcacion?.trim()
  const geo    = (demar && !['españa','espana'].includes(demar.toLowerCase()))
    ? '(area.searchArea)'
    : '(27.6,-18.2,43.8,4.3)'

  const lines = []
  for (const block of blocks.value) {
    if (block.mode === 'and') {
      const chain = block.pairs.map(([k,v]) => !v||v==='*' ? `["${k}"]` : `["${k}"="${v}"]`).join('')
      for (const et of etypes) lines.push(`  ${et}${chain}${geo};`)
    } else {
      for (const [k,v] of block.pairs) {
        const f = !v||v==='*' ? `["${k}"]` : `["${k}"="${v}"]`
        for (const et of etypes) lines.push(`  ${et}${f}${geo};`)
      }
    }
  }
  return [...new Set(lines)]
})

const uniqueQueryLines = computed(() => queryLines.value.length)

const queryPreview = computed(() => {
  if (!blocks.value.length) return '-- sin condiciones --'
  const timeout = parseInt(props.timeout) || 60
  const outFmt  = props.outFormat || 'center'
  const demar   = props.demarcacion?.trim()
  let header = `[out:json][timeout:${timeout}];`
  if (demar && !['españa','espana'].includes(demar.toLowerCase()))
    header += `\narea["name"="${demar}"]->.searchArea;`
  return [header, '(', ...queryLines.value, ');', `out ${outFmt};`].join('\n')
})

async function copyQuery() {
  try {
    await navigator.clipboard.writeText(queryPreview.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}

// ── Guardar / cancelar ────────────────────────────────────────────────────
function save() {
  emit('update:modelValue', JSON.stringify(blocks.value))
  emit('close')
}
function cancel() {
  emit('close')
}
</script>
