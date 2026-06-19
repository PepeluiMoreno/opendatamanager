<template>
  <div class="cm-wrap">
    <h3 class="cm-h3">Recursos de la colección «{{ collectionName }}»</h3>
    <div class="cm">
    <!-- ── DISPONIBLES (no incluidos) ── -->
    <section class="cm-col">
      <header class="cm-head">
        <div class="cm-title">Disponibles <span class="cm-badge">{{ disponibles.length }}</span></div>
        <div class="cm-search">
          <input v-model="qL" placeholder="Buscar disponibles…" />
        </div>
      </header>
      <div class="cm-list" :class="{ over: overPanel==='available' }"
           @dragover.prevent="overPanel='available'" @dragleave="overPanel=null" @drop.prevent="onDrop('available')">
        <div v-for="it in disponiblesView" :key="it.r.id"
             :class="['cm-row', { child: it.isChild, sel: selL.has(it.r.id), drag: dragIds.includes(it.r.id) }]"
             :draggable="canEdit" @dragstart="onDragStart('available', it, $event)" @dragend="onDragEnd"
             @click="toggle('available', it)">
          <input type="checkbox" class="cm-cbx" :checked="selL.has(it.r.id)" @click.stop="toggle('available', it)" :disabled="!canEdit" />
          <span v-if="it.hasChildren" class="cm-tw" :class="{open: expanded.has(it.r.id)}" @click.stop="toggleExp(it.r.id)">▸</span>
          <span v-else-if="!it.isChild" class="cm-tw ph"></span>
          <span class="cm-nm">
            <span v-if="esNodriza(it.r)" class="cm-mark">🛰️</span>
            <span v-else-if="it.isChild" class="cm-mark">↳</span>
            {{ it.r.name }}
            <small v-if="esNodriza(it.r) && hijos(it.r.id).length" class="cm-sub">· familia de {{ hijos(it.r.id).length }}</small>
            <small v-else-if="it.isChild && it.parentName" class="cm-sub">· de {{ it.parentName }}</small>
          </span>
        </div>
        <div v-if="!disponiblesView.length" class="cm-empty">Todo el pool está en la colección.</div>
      </div>
    </section>

    <!-- ── BOTONERA ── -->
    <div class="cm-mid">
      <button class="cm-btn" :disabled="!canEdit || !selL.size || busy" @click="incluir" title="Incluir en la colección">
        {{ busy ? '…' : `Incluir (${selL.size}) →` }}
      </button>
      <button class="cm-btn" :disabled="!canEdit || !selR.size || busy" @click="excluir" title="Excluir de la colección">
        {{ busy ? '…' : `← Excluir (${selR.size})` }}
      </button>
      <p class="cm-hint">Arrastra entre paneles o marca y usa los botones. Marcar una nodriza 🛰️ selecciona toda su familia; marca hijos sueltos para mover solo algunos.</p>
    </div>

    <!-- ── EN LA COLECCIÓN (incluidos) ── -->
    <section class="cm-col">
      <header class="cm-head">
        <div class="cm-title">Incluidos <span class="cm-badge on">{{ miembros.length }}</span></div>
        <div class="cm-search">
          <input v-model="qR" placeholder="Buscar incluidos…" />
        </div>
      </header>
      <div class="cm-list" :class="{ over: overPanel==='members' }"
           @dragover.prevent="overPanel='members'" @dragleave="overPanel=null" @drop.prevent="onDrop('members')">
        <div v-for="it in miembrosView" :key="it.r.id"
             :class="['cm-row', { child: it.isChild, sel: selR.has(it.r.id), drag: dragIds.includes(it.r.id) }]"
             :draggable="canEdit" @dragstart="onDragStart('members', it, $event)" @dragend="onDragEnd"
             @click="toggle('members', it)">
          <input type="checkbox" class="cm-cbx" :checked="selR.has(it.r.id)" @click.stop="toggle('members', it)" :disabled="!canEdit" />
          <span v-if="it.hasChildren" class="cm-tw" :class="{open: expanded.has(it.r.id)}" @click.stop="toggleExp(it.r.id)">▸</span>
          <span v-else-if="!it.isChild" class="cm-tw ph"></span>
          <span class="cm-nm">
            <span v-if="esNodriza(it.r)" class="cm-mark">🛰️</span>
            <span v-else-if="it.isChild" class="cm-mark">↳</span>
            {{ it.r.name }}
            <small v-if="esNodriza(it.r) && hijos(it.r.id).length" class="cm-sub">· familia de {{ hijos(it.r.id).length }}</small>
            <small v-else-if="it.isChild && it.parentName" class="cm-sub">· de {{ it.parentName }}</small>
          </span>
        </div>
        <div v-if="!miembrosView.length" class="cm-empty">La colección está vacía. Incluye recursos del panel izquierdo.</div>
      </div>
    </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useAuth } from '../composables/useAuth'
import { useToast } from '../composables/useToast'
import { addResourcesToCollection, removeResourceFromCollection } from '../api/graphql'

const props = defineProps({
  collectionId: { type: String, required: true },
  collectionName: { type: String, default: '' },
  resources: { type: Array, default: () => [] },
})
const emit = defineEmits(['changed'])

const { puede } = useAuth()
const { toast } = useToast()
const canEdit = computed(() => puede('recursos.editar'))

const qL = ref(''); const qR = ref('')
const selL = ref(new Set()); const selR = ref(new Set())
const busy = ref(false)
const dragIds = ref([]); const dragFrom = ref(null); const overPanel = ref(null)
const expanded = ref(new Set())   // nodrizas con su familia desplegada (colapsadas por defecto)
function toggleExp(id) { const s = new Set(expanded.value); s.has(id) ? s.delete(id) : s.add(id); expanded.value = s }

function esNodriza(r) { return r?.generaColecciones === true }
function esMiembro(r) { return (r.collectionIds || []).includes(props.collectionId) }
function hijos(id) { return props.resources.filter(r => r.parentResourceId === id) }
const byName = (a, b) => (a.r.name || '').localeCompare(b.r.name || '', 'es')
const nombreDe = (id) => props.resources.find(r => r.id === id)?.name || ''

const miembros = computed(() => props.resources.filter(esMiembro))
const disponibles = computed(() => props.resources.filter(r => !esMiembro(r)))

// Construye una vista ordenada: cada nodriza/recurso de nivel superior, seguido de
// sus hijos PRESENTES en el mismo panel; los hijos cuyo padre está en el otro panel
// se muestran como "huérfanos" con la pista de su padre. Filtro de búsqueda aplicado.
function construirVista(lista, q) {
  const f = q.trim().toLowerCase()
  const casa = r => !f || (r.name || '').toLowerCase().includes(f)
  const enPanel = new Set(lista.map(r => r.id))
  const topLevel = lista.filter(r => !r.parentResourceId).sort((a, b) => (a.name||'').localeCompare(b.name||'', 'es'))
  const hijosEnPanel = new Map()
  for (const r of lista) {
    if (r.parentResourceId && enPanel.has(r.parentResourceId)) {
      if (!hijosEnPanel.has(r.parentResourceId)) hijosEnPanel.set(r.parentResourceId, [])
      hijosEnPanel.get(r.parentResourceId).push(r)
    }
  }
  const out = []
  for (const r of topLevel) {
    const hs = (hijosEnPanel.get(r.id) || []).sort((a, b) => (a.name||'').localeCompare(b.name||'', 'es'))
    const algunoCasa = casa(r) || hs.some(casa)
    if (!algunoCasa) continue
    out.push({ r, isChild: false, hasChildren: hs.length > 0, childCount: hs.length })
    // hijos solo si la familia está desplegada (o hay búsqueda activa): evita
    // renderizar miles de filas de una nodriza grande.
    if (hs.length && (expanded.value.has(r.id) || f)) {
      for (const ch of hs) if (!f || casa(ch) || casa(r)) out.push({ r: ch, isChild: true, parentName: r.name })
    }
  }
  // hijos cuyo padre está en el OTRO panel (movido individualmente)
  for (const r of lista) {
    if (r.parentResourceId && !enPanel.has(r.parentResourceId) && casa(r)) {
      out.push({ r, isChild: true, parentName: nombreDe(r.parentResourceId) })
    }
  }
  return out
}
const disponiblesView = computed(() => construirVista(disponibles.value, qL.value))
const miembrosView = computed(() => construirVista(miembros.value, qR.value))

// La colección y el pool cambian al recargar: limpia selecciones obsoletas.
watch(() => props.collectionId, () => { selL.value = new Set(); selR.value = new Set() })
watch(() => props.resources, () => { selL.value = new Set(); selR.value = new Set() })

// Marcar una nodriza arrastra/selecciona su familia (la nodriza + sus hijos que
// estén en el MISMO panel). Un hijo o recurso suelto, solo a él.
function familia(panel, r) {
  const lista = panel === 'available' ? disponibles.value : miembros.value
  if (esNodriza(r)) {
    const enPanel = new Set(lista.map(x => x.id))
    return [r.id, ...hijos(r.id).filter(h => enPanel.has(h.id)).map(h => h.id)]
  }
  return [r.id]
}
function toggle(panel, it) {
  if (!canEdit.value) return
  const set = panel === 'available' ? new Set(selL.value) : new Set(selR.value)
  const ids = familia(panel, it.r)
  const encender = !ids.every(i => set.has(i))
  ids.forEach(i => encender ? set.add(i) : set.delete(i))
  if (panel === 'available') selL.value = set; else selR.value = set
}

function onDragStart(panel, it, ev) {
  if (!canEdit.value) { ev.preventDefault(); return }
  const sel = panel === 'available' ? selL.value : selR.value
  // si el ítem arrastrado está en la selección, mueve toda la selección; si no, su familia
  dragIds.value = sel.has(it.r.id) ? [...sel] : familia(panel, it.r)
  dragFrom.value = panel
  try { ev.dataTransfer.effectAllowed = 'move'; ev.dataTransfer.setData('text/plain', dragIds.value.join(',')) } catch {}
}
function onDragEnd() { dragIds.value = []; dragFrom.value = null; overPanel.value = null }
async function onDrop(panel) {
  overPanel.value = null
  if (!dragIds.value.length || dragFrom.value === panel) { onDragEnd(); return }
  const ids = dragIds.value.slice()
  if (panel === 'members') await aplicar('incluir', ids)
  else await aplicar('excluir', ids)
  onDragEnd()
}

async function aplicar(accion, ids) {
  if (!canEdit.value || !ids.length || busy.value) return
  busy.value = true
  try {
    if (accion === 'incluir') {
      await addResourcesToCollection(props.collectionId, ids)
      toast.success(`${ids.length} recurso(s) incluido(s)`)
    } else {
      for (const id of ids) await removeResourceFromCollection(props.collectionId, id)
      toast.success(`${ids.length} recurso(s) excluido(s)`)
    }
    selL.value = new Set(); selR.value = new Set()
    emit('changed')
  } catch (e) { toast.error('Error: ' + (e?.message || e)) }
  finally { busy.value = false }
}
const incluir = () => aplicar('incluir', [...selL.value])
const excluir = () => aplicar('excluir', [...selR.value])
</script>

<style scoped>
.cm-wrap{display:flex;flex-direction:column;gap:12px;height:100%;min-height:0}
.cm-h3{margin:0;font-size:15px;font-weight:600;color:#E7EEF6}
.cm{display:grid;grid-template-columns:1fr 200px 1fr;gap:14px;align-items:stretch;flex:1;min-height:0}
.cm-col{display:flex;flex-direction:column;min-height:0;background:#0e151d;border:1px solid #1c2733;border-radius:12px;overflow:hidden}
.cm-head{padding:12px 14px;border-bottom:1px solid #1c2733;display:flex;flex-direction:column;gap:8px}
.cm-title{font-weight:600;color:#E7EEF6;display:flex;align-items:center;gap:8px}
.cm-badge{font-family:var(--mono,monospace);font-size:11px;color:#8595A6;background:#0d1219;border:1px solid #243140;border-radius:20px;padding:1px 9px}
.cm-badge.on{color:#3FE0CB;border-color:#1c5b54}
.cm-search input{width:100%;background:#0d1219;border:1px solid #243140;border-radius:8px;padding:6px 10px;font-size:13px;color:#E7EEF6;outline:none}
.cm-search input:focus{border-color:#3FE0CB}
.cm-list{flex:1;min-height:0;overflow-y:auto;padding:6px;transition:background .15s}
.cm-list.over{background:#15302c;outline:2px dashed #3FE0CB;outline-offset:-4px}
.cm-row{display:flex;align-items:center;gap:9px;padding:7px 9px;border-radius:8px;cursor:pointer;user-select:none}
.cm-row:hover{background:#161e29}
.cm-row.sel{background:#13202a;box-shadow:inset 0 0 0 1px #2b6a61}
.cm-row.child{margin-left:18px}
.cm-row.drag{opacity:.45}
.cm-cbx{width:16px;height:16px;accent-color:#3FE0CB;cursor:pointer;flex-shrink:0}
.cm-tw{width:12px;flex-shrink:0;text-align:center;color:#5A6878;font-size:10px;cursor:pointer;transition:transform .15s}
.cm-tw.open{transform:rotate(90deg)}
.cm-tw.ph{cursor:default;visibility:hidden}
.cm-nm{font-size:13px;color:#E7EEF6;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cm-mark{margin-right:2px}
.cm-sub{color:#5A6878;font-size:11px;margin-left:4px}
.cm-empty{padding:18px;text-align:center;color:#5A6878;font-size:13px}
.cm-mid{display:flex;flex-direction:column;justify-content:center;gap:10px;padding:0 4px}
.cm-btn{padding:10px 12px;border-radius:10px;border:1px solid #2b6a61;background:#13202a;color:#3FE0CB;font-weight:600;cursor:pointer;font-size:13px}
.cm-btn:hover:not(:disabled){background:#15302c}
.cm-btn:disabled{opacity:.4;cursor:not-allowed}
.cm-hint{font-size:11px;color:#5A6878;line-height:1.5;margin-top:6px;text-align:center}
@media(max-width:900px){.cm{grid-template-columns:1fr;gap:10px}.cm-mid{flex-direction:row;justify-content:center}}
</style>
