<template>
  <div class="rounded-lg border border-gray-700 bg-gray-900 overflow-hidden text-xs" @click.stop>

    <!-- ── Toolbar ──────────────────────────────────────────────────────── -->
    <div class="flex items-center justify-between px-3 py-2 border-b border-gray-700 bg-gray-850">
      <span class="text-gray-400 font-medium tracking-wide uppercase" style="font-size:10px;">
        Condiciones de búsqueda
      </span>
      <div class="flex items-center gap-1.5">
        <span v-if="blocks.length" class="text-gray-600" style="font-size:10px;">
          {{ blocks.length }} bloque{{ blocks.length !== 1 ? 's' : '' }}
        </span>
        <!-- Botón Añadir preset -->
        <div class="relative" ref="dropdownRef">
          <button
            @click="showDropdown = !showDropdown"
            class="flex items-center gap-1 px-2 py-1 rounded text-blue-400 border border-blue-800
                   hover:bg-blue-900/40 hover:text-blue-300 transition-colors"
          >
            <span>＋</span> Añadir preset
          </button>

          <!-- Dropdown de presets -->
          <div
            v-if="showDropdown"
            class="absolute right-0 top-full mt-1 z-50 w-72 rounded-lg border border-gray-600
                   bg-gray-800 shadow-2xl overflow-hidden"
          >
            <div
              v-for="(group, gname) in presetGroups"
              :key="gname"
            >
              <div class="px-3 py-1.5 bg-gray-750 border-b border-gray-700">
                <span class="text-gray-400 font-semibold uppercase tracking-wider" style="font-size:9px;">
                  {{ gname }}
                </span>
              </div>
              <button
                v-for="p in group"
                :key="p.key"
                @click="addPreset(p.key)"
                :disabled="isActive(p.key)"
                class="w-full text-left px-3 py-2 flex items-center justify-between
                       hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed
                       border-b border-gray-750 last:border-b-0 transition-colors"
              >
                <span :class="['font-mono', categoryColor(p.key)]">{{ p.label }}</span>
                <span v-if="isActive(p.key)" class="text-green-500 text-xs">✓</span>
                <span v-else class="text-gray-600 text-xs">{{ pairCount(p.key) }} cond.</span>
              </button>
            </div>

            <!-- Separador + condición personalizada -->
            <div class="border-t border-gray-600 px-3 py-2">
              <button
                @click="showDropdown = false; showCustomForm = true"
                class="w-full text-left text-gray-400 hover:text-gray-200 flex items-center gap-1.5"
              >
                <span class="text-gray-600">⊕</span> Condición personalizada…
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Bloques activos ──────────────────────────────────────────────── -->
    <div class="divide-y divide-gray-800">
      <div
        v-for="(block, idx) in blocks"
        :key="idx"
        class="flex items-start gap-3 px-3 py-2.5 hover:bg-gray-800/50 group transition-colors"
      >
        <!-- Indicador de categoría -->
        <div :class="['w-1 self-stretch rounded-full flex-shrink-0 mt-0.5', categoryBar(block.preset)]" />

        <!-- Contenido -->
        <div class="flex-1 min-w-0 space-y-1.5">
          <!-- Nombre del preset -->
          <div class="flex items-center gap-2">
            <span :class="['font-mono font-semibold', categoryColor(block.preset)]" style="font-size:10px;">
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

          <!-- Píldoras de pares -->
          <div class="flex flex-wrap gap-1">
            <span
              v-for="(pair, pi) in block.pairs"
              :key="pi"
              class="inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded
                     bg-gray-800 border border-gray-700 font-mono"
            >
              <span class="text-yellow-400">{{ pair[0] }}</span>
              <span class="text-gray-600">=</span>
              <span class="text-green-400">{{ pair[1] === '*' ? '<any>' : pair[1] }}</span>
            </span>
          </div>
        </div>

        <!-- Botón eliminar -->
        <button
          @click="removeBlock(idx)"
          class="opacity-0 group-hover:opacity-100 flex-shrink-0 mt-0.5
                 text-gray-600 hover:text-red-400 transition-all"
          title="Eliminar"
        >✕</button>
      </div>

      <!-- Estado vacío -->
      <div v-if="!blocks.length" class="px-3 py-6 text-center text-gray-600 italic">
        Sin condiciones — añade un preset para comenzar
      </div>
    </div>

    <!-- ── Formulario condición personalizada ───────────────────────────── -->
    <div
      v-if="showCustomForm"
      class="border-t border-gray-700 px-3 py-3 bg-gray-850 space-y-2"
    >
      <div class="text-gray-400 font-medium" style="font-size:10px;">CONDICIÓN PERSONALIZADA</div>
      <div class="flex items-center gap-2 flex-wrap">
        <input
          v-model="customKey"
          placeholder="key (p.ej. amenity)"
          class="w-36 bg-gray-900 border border-gray-600 rounded px-2 py-1
                 text-yellow-400 font-mono focus:outline-none focus:border-yellow-600"
        />
        <span class="text-gray-600">=</span>
        <input
          v-model="customVal"
          placeholder="value  (* = cualquiera)"
          class="w-44 bg-gray-900 border border-gray-600 rounded px-2 py-1
                 text-green-400 font-mono focus:outline-none focus:border-green-700"
        />
        <label class="flex items-center gap-1 text-gray-500 cursor-pointer select-none">
          <input type="checkbox" v-model="customOr" class="accent-orange-500" />
          OR
        </label>
        <button
          @click="addCustomPair"
          :disabled="!customKey.trim()"
          class="px-2 py-1 rounded bg-gray-700 hover:bg-gray-600
                 disabled:opacity-40 disabled:cursor-not-allowed text-gray-300"
        >Añadir</button>
        <button @click="showCustomForm = false" class="text-gray-600 hover:text-gray-400">✕</button>
      </div>
    </div>

    <!-- ── Preview Overpass QL ───────────────────────────────────────────── -->
    <div class="border-t border-gray-700">
      <button
        @click="showPreview = !showPreview"
        class="w-full flex items-center justify-between px-3 py-2
               text-gray-500 hover:text-gray-300 hover:bg-gray-800/50 transition-colors"
        style="font-size:10px;"
      >
        <span class="uppercase tracking-wider font-medium">Overpass QL preview</span>
        <span>{{ showPreview ? '▲' : '▼' }}</span>
      </button>
      <div v-if="showPreview" class="relative">
        <pre
          class="px-3 py-3 text-xs font-mono text-green-300 bg-gray-950
                 overflow-x-auto leading-relaxed border-t border-gray-800"
          v-text="queryPreview"
        />
        <button
          @click="copyQuery"
          class="absolute top-2 right-2 px-2 py-0.5 rounded text-gray-500 border border-gray-700
                 hover:text-gray-300 hover:border-gray-500 transition-colors bg-gray-900"
          style="font-size:10px;"
        >{{ copied ? '✓ copiado' : 'copiar' }}</button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  modelValue:   { type: String,          default: '' },
  presets:      { type: Object,          default: () => ({}) },
  demarcacion:  { type: String,          default: 'España' },
  elementTypes: { type: String,          default: 'node,way' },
  timeout:      { type: [String,Number], default: 60 },
  outFormat:    { type: String,          default: 'center' },
})
const emit = defineEmits(['update:modelValue'])

// ── Estado ─────────────────────────────────────────────────────────────────
const blocks        = ref([])
const showDropdown  = ref(false)
const showCustomForm= ref(false)
const showPreview   = ref(false)
const customKey     = ref('')
const customVal     = ref('')
const customOr      = ref(false)
const copied        = ref(false)
const dropdownRef   = ref(null)

// ── Inicialización ──────────────────────────────────────────────────────────
watch(() => props.modelValue, (val) => {
  const incoming = parseModelValue(val)
  if (JSON.stringify(incoming) !== JSON.stringify(blocks.value))
    blocks.value = incoming
}, { immediate: true })

function parseModelValue(val) {
  if (!val) return []
  try {
    const p = JSON.parse(val)
    if (!Array.isArray(p)) return []
    return p.map(b => typeof b === 'string'
      ? presetToBlock(b.toUpperCase())
      : b
    )
  } catch { return [] }
}

function emitChange() {
  emit('update:modelValue', JSON.stringify(blocks.value))
}

// ── Grupos de presets ───────────────────────────────────────────────────────
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

const CATEGORY_COLORS = {
  RELIGIOUS:      'text-purple-400',
  EDUCATION:      'text-blue-400',
  HEALTHCARE:     'text-emerald-400',
  PUBLIC_ADMIN:   'text-violet-400',
  HERITAGE:       'text-amber-400',
  TOURISM:        'text-cyan-400',
  EMERGENCY:      'text-red-400',
  TRANSPORT:      'text-slate-400',
}

const CATEGORY_BARS = {
  RELIGIOUS:      'bg-purple-600',
  EDUCATION:      'bg-blue-600',
  HEALTHCARE:     'bg-emerald-600',
  PUBLIC_ADMIN:   'bg-violet-600',
  HERITAGE:       'bg-amber-600',
  TOURISM:        'bg-cyan-600',
  EMERGENCY:      'bg-red-600',
  TRANSPORT:      'bg-slate-500',
}

function categoryKey(presetKey) {
  if (!presetKey) return null
  return Object.keys(CATEGORY_COLORS).find(c => presetKey.startsWith(c)) || null
}
function categoryColor(presetKey) {
  return CATEGORY_COLORS[categoryKey(presetKey)] || 'text-gray-400'
}
function categoryBar(presetKey) {
  return CATEGORY_BARS[categoryKey(presetKey)] || 'bg-gray-600'
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

function isActive(key) {
  return blocks.value.some(b => b.preset === key)
}

function pairCount(key) {
  const p = props.presets[key]
  if (!p) return 0
  return (p.pairs || p.pairs_or || []).length
}

// ── Acciones ────────────────────────────────────────────────────────────────
function presetToBlock(key) {
  const p = props.presets[key] || {}
  const pairs = p.pairs || p.pairs_or || []
  const mode  = p.pairs_or ? 'or' : 'and'
  return { preset: key, pairs, mode }
}

function addPreset(key) {
  if (isActive(key)) return
  blocks.value.push(presetToBlock(key))
  showDropdown.value = false
  emitChange()
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
  emitChange()
}

function removeBlock(idx) {
  blocks.value.splice(idx, 1)
  emitChange()
}

// ── Cerrar dropdown al clicar fuera ────────────────────────────────────────
function onClickOutside(e) {
  if (dropdownRef.value && !dropdownRef.value.contains(e.target))
    showDropdown.value = false
}
onMounted(() => document.addEventListener('mousedown', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('mousedown', onClickOutside))

// ── Query preview ───────────────────────────────────────────────────────────
const queryPreview = computed(() => {
  if (!blocks.value.length) return '-- sin condiciones --'
  const timeout = parseInt(props.timeout) || 60
  const outFmt  = props.outFormat || 'center'
  const etypes  = (props.elementTypes || 'node,way').split(',').map(s => s.trim()).filter(Boolean)
  const demar   = props.demarcacion?.trim()

  let header = `[out:json][timeout:${timeout}];`
  let geo
  if (demar && !['españa','espana'].includes(demar.toLowerCase())) {
    header += `\narea["name"="${demar}"]->.searchArea;`
    geo = '(area.searchArea)'
  } else {
    geo = '(27.6,-18.2,43.8,4.3)'
  }

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

  // Deduplicar
  const unique = [...new Set(lines)]
  return [header, '(', ...unique, ');', `out ${outFmt};`].join('\n')
})

async function copyQuery() {
  try {
    await navigator.clipboard.writeText(queryPreview.value)
    copied.value = true
    setTimeout(() => { copied.value = false }, 2000)
  } catch {}
}
</script>
