<template>
  <div class="se-wrap">
    <h3 class="se-h3">Subscriptions — «{{ subscriberName }}»</h3>
    <div class="se">
      <!-- ── DISPONIBLES (no suscrito) ── -->
      <section class="se-col">
        <header class="se-head">
          <div class="se-title">Available <span class="se-badge">{{ disponibles.length }}</span></div>
          <input v-model="qL" class="se-inp" placeholder="Buscar colecciones y recursos…" />
        </header>
        <div class="se-list" :class="{ over: over==='avail' }"
             @dragover.prevent="over='avail'" @dragleave="over=null" @drop.prevent="onDrop('avail')">
          <div v-for="u in disponiblesView" :key="u.key"
               :class="['se-row', { sel: selL.has(u.key), drag: dragKeys.includes(u.key) }]"
               :draggable="canEdit" @dragstart="onDragStart('avail', u, $event)" @dragend="onDragEnd"
               @click="toggle('avail', u)">
            <input type="checkbox" class="se-cbx" :checked="selL.has(u.key)" @click.stop="toggle('avail', u)" :disabled="!canEdit" />
            <span class="se-ic">{{ u.icon || '·' }}</span>
            <span class="se-nm">{{ u.name }}<small class="se-sub">{{ u.tipo }}</small></span>
          </div>
          <div v-if="!disponiblesView.length" class="se-empty">No queda nada por suscribir.</div>
        </div>
      </section>

      <!-- ── BOTONERA ── -->
      <div class="se-mid">
        <button class="se-btn" :disabled="!canEdit || !selL.size || busy" @click="incluir">{{ busy?'…':`Subscribe (${selL.size}) →` }}</button>
        <button class="se-btn" :disabled="!canEdit || !selR.size || busy" @click="excluir">{{ busy?'…':`← Unsubscribe (${selR.size})` }}</button>
        <p class="se-hint">Arrastra entre paneles o marca y usa los botones. Suscribir a una colección 🗂️ cubre sus recursos (también los futuros); a una nodriza 🛰️, toda su familia.</p>
      </div>

      <!-- ── SUSCRITO ── -->
      <section class="se-col">
        <header class="se-head">
          <div class="se-title">Subscribed <span class="se-badge on">{{ suscritas.length }}</span></div>
          <input v-model="qR" class="se-inp" placeholder="Buscar suscripciones…" />
        </header>
        <div class="se-list" :class="{ over: over==='subs' }"
             @dragover.prevent="over='subs'" @dragleave="over=null" @drop.prevent="onDrop('subs')">
          <div v-for="u in suscritasView" :key="u.key"
               :class="['se-row', { sel: selR.has(u.key), drag: dragKeys.includes(u.key) }]"
               :draggable="canEdit" @dragstart="onDragStart('subs', u, $event)" @dragend="onDragEnd"
               @click="toggle('subs', u)">
            <input type="checkbox" class="se-cbx" :checked="selR.has(u.key)" @click.stop="toggle('subs', u)" :disabled="!canEdit" />
            <span class="se-ic">{{ u.icon || '·' }}</span>
            <span class="se-nm">{{ u.name }}<small class="se-sub">{{ u.tipo }}</small></span>
          </div>
          <div v-if="!suscritasView.length" class="se-empty">Sin suscripciones. Añade desde el panel izquierdo.</div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { subscribeResource, subscribeCollection, unsubscribeResource } from '../api/graphql'

const props = defineProps({
  subscriberId: { type: String, required: true },
  subscriberName: { type: String, default: '' },
  resources: { type: Array, default: () => [] },
  collections: { type: Array, default: () => [] },
  subscriptions: { type: Array, default: () => [] },   // ya filtradas a este suscriptor
})
const emit = defineEmits(['changed'])

const { puede } = useAuth()
const { toast } = useToast()
const canEdit = computed(() => puede('subscribers.editar') || puede('aplicaciones.gestionar'))

const qL = ref(''); const qR = ref('')
const selL = ref(new Set()); const selR = ref(new Set())
const busy = ref(false)
const dragKeys = ref([]); const dragFrom = ref(null); const over = ref(null)

const esNodriza = r => r?.generaColecciones === true
const matrizDe = nodId => props.collections.find(c => c.origin === 'matriz' && c.rootResourceId === nodId)
const colDe = id => props.collections.find(c => c.id === id)
const recDe = id => props.resources.find(r => r.id === id)

// Unidades suscribibles: colecciones organizativas + recursos de nivel superior.
// La unidad declara su TARGET (recurso o colección); una nodriza apunta a su matriz.
const unidades = computed(() => {
  const out = []
  for (const c of props.collections.filter(c => (c.origin || 'organizativa') === 'organizativa')) {
    out.push({ key: 'c:' + c.id, name: c.name, icon: '🗂️', tipo: ' · colección', target: { type: 'collection', id: c.id } })
  }
  for (const r of props.resources.filter(r => !r.parentResourceId)) {
    if (esNodriza(r)) {
      const mz = matrizDe(r.id)
      out.push({ key: 'r:' + r.id, name: r.name, icon: '🛰️', tipo: ' · nodriza (familia)',
                 target: mz ? { type: 'collection', id: mz.id } : { type: 'resource', id: r.id } })
    } else {
      out.push({ key: 'r:' + r.id, name: r.name, icon: '', tipo: ' · recurso', target: { type: 'resource', id: r.id } })
    }
  }
  return out
})
const subDeTarget = t => props.subscriptions.find(s =>
  t.type === 'collection' ? s.collectionId === t.id : s.resourceId === t.id)

const disponibles = computed(() => unidades.value.filter(u => !subDeTarget(u.target)))

// Suscrito: una fila por suscripción (resuelve nombre/icono; cubre subs que no
// casen una unidad de nivel superior, p. ej. una suscripción antigua a un hijo).
function unidadDeSub(s) {
  if (s.collectionId) {
    const c = colDe(s.collectionId)
    if (c && c.origin === 'matriz') {
      const nod = recDe(c.rootResourceId)
      return { key: 'sub:' + s.id, subId: s.id, name: nod?.name || c.name, icon: '🛰️', tipo: ' · nodriza (familia)' }
    }
    return { key: 'sub:' + s.id, subId: s.id, name: c?.name || s.collectionId, icon: '🗂️', tipo: ' · colección' }
  }
  const r = recDe(s.resourceId)
  return { key: 'sub:' + s.id, subId: s.id, name: r?.name || s.resourceId, icon: esNodriza(r) ? '🛰️' : '', tipo: ' · recurso' }
}
const suscritas = computed(() => props.subscriptions.map(unidadDeSub))

const filtra = (lista, q) => {
  const f = q.trim().toLowerCase()
  return f ? lista.filter(u => (u.name || '').toLowerCase().includes(f)) : lista
}
const disponiblesView = computed(() => filtra(disponibles.value, qL.value))
const suscritasView = computed(() => filtra(suscritas.value, qR.value))

watch(() => props.subscriberId, () => { selL.value = new Set(); selR.value = new Set() })
watch(() => props.subscriptions, () => { selL.value = new Set(); selR.value = new Set() })

function toggle(panel, u) {
  if (!canEdit.value) return
  const set = panel === 'avail' ? new Set(selL.value) : new Set(selR.value)
  set.has(u.key) ? set.delete(u.key) : set.add(u.key)
  if (panel === 'avail') selL.value = set; else selR.value = set
}
function onDragStart(panel, u, ev) {
  if (!canEdit.value) { ev.preventDefault(); return }
  const set = panel === 'avail' ? selL.value : selR.value
  dragKeys.value = set.has(u.key) ? [...set] : [u.key]
  dragFrom.value = panel
  try { ev.dataTransfer.effectAllowed = 'move' } catch {}
}
function onDragEnd() { dragKeys.value = []; dragFrom.value = null; over.value = null }
async function onDrop(panel) {
  over.value = null
  if (!dragKeys.value.length || dragFrom.value === panel) { onDragEnd(); return }
  if (panel === 'subs') await incluirKeys(dragKeys.value)
  else await excluirKeys(dragKeys.value)
  onDragEnd()
}

async function incluirKeys(keys) {
  if (!canEdit.value || busy.value) return
  const units = unidades.value.filter(u => keys.includes(u.key) && !subDeTarget(u.target))
  if (!units.length) return
  busy.value = true
  try {
    for (const u of units) {
      if (u.target.type === 'collection') await subscribeCollection(props.subscriberId, u.target.id)
      else await subscribeResource(props.subscriberId, u.target.id, null, 'patch', null)
    }
    toast.success(`${units.length} suscripción(es) añadida(s)`)
    selL.value = new Set(); emit('changed')
  } catch (e) { toast.error('Error: ' + (e?.message || e)) }
  finally { busy.value = false }
}
async function excluirKeys(keys) {
  if (!canEdit.value || busy.value) return
  const ids = suscritas.value.filter(u => keys.includes(u.key)).map(u => u.subId)
  if (!ids.length) return
  busy.value = true
  try {
    for (const id of ids) await unsubscribeResource(id)
    toast.success(`${ids.length} baja(s)`)
    selR.value = new Set(); emit('changed')
  } catch (e) { toast.error('Error: ' + (e?.message || e)) }
  finally { busy.value = false }
}
const incluir = () => incluirKeys([...selL.value])
const excluir = () => excluirKeys([...selR.value])
</script>

<style scoped>
.se-wrap{display:flex;flex-direction:column;gap:12px;height:100%;min-height:0}
.se-h3{margin:0;font-size:15px;font-weight:600;color:#E7EEF6}
.se{display:grid;grid-template-columns:1fr 210px 1fr;gap:14px;align-items:stretch;flex:1;min-height:0}
.se-col{display:flex;flex-direction:column;min-height:0;background:#0e151d;border:1px solid #1c2733;border-radius:12px;overflow:hidden}
.se-head{padding:12px 14px;border-bottom:1px solid #1c2733;display:flex;flex-direction:column;gap:8px}
.se-title{font-weight:600;color:#E7EEF6;display:flex;align-items:center;gap:8px}
.se-badge{font-size:11px;color:#8595A6;background:#0d1219;border:1px solid #243140;border-radius:20px;padding:1px 9px}
.se-badge.on{color:#3FE0CB;border-color:#1c5b54}
.se-inp{width:100%;background:#0d1219;border:1px solid #243140;border-radius:8px;padding:6px 10px;font-size:13px;color:#E7EEF6;outline:none}
.se-inp:focus{border-color:#3FE0CB}
.se-list{flex:1;min-height:0;overflow-y:auto;padding:6px;transition:background .15s}
.se-list.over{background:#15302c;outline:2px dashed #3FE0CB;outline-offset:-4px}
.se-row{display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:8px;cursor:pointer;user-select:none}
.se-row:hover{background:#161e29}
.se-row.sel{background:#13202a;box-shadow:inset 0 0 0 1px #2b6a61}
.se-row.drag{opacity:.45}
.se-cbx{width:16px;height:16px;accent-color:#3FE0CB;cursor:pointer;flex-shrink:0}
.se-ic{width:18px;text-align:center;flex-shrink:0}
.se-nm{font-size:13px;color:#E7EEF6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.se-sub{color:#5A6878;font-size:11px}
.se-empty{padding:18px;text-align:center;color:#5A6878;font-size:13px}
.se-mid{display:flex;flex-direction:column;justify-content:center;gap:10px;padding:0 4px}
.se-btn{padding:10px 12px;border-radius:10px;border:1px solid #2b6a61;background:#13202a;color:#3FE0CB;font-weight:600;cursor:pointer;font-size:13px}
.se-btn:hover:not(:disabled){background:#15302c}
.se-btn:disabled{opacity:.4;cursor:not-allowed}
.se-hint{font-size:11px;color:#5A6878;line-height:1.5;margin-top:6px;text-align:center}
@media(max-width:900px){.se{grid-template-columns:1fr;gap:10px}.se-mid{flex-direction:row;justify-content:center}}
</style>
