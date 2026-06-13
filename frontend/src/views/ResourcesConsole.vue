<template>
  <div :class="['console', { collapsed: !railOpen }]" :style="{ gridTemplateColumns: railOpen ? (railW + 'px 6px 1fr') : '0 0 1fr' }">
    <!-- ============ COLLECTIONS RAIL ============ -->
    <aside class="rail">
      <div class="brand">
        <PageHeader title="Recursos" subtitle="Vista nueva · beta" tight />
      </div>

      <div class="roster-h">
        <span>Colecciones</span>
        <button v-if="puede('recursos.crear')" @click="showAdd = !showAdd" title="Nueva colección">+</button>
      </div>
      <div v-if="showAdd" class="col-add">
        <input v-model="addName" placeholder="Nombre de la colección…" @keyup.enter="crearColeccion" autofocus />
        <button @click="crearColeccion">Crear</button>
      </div>

      <div class="roster">
        <div v-if="!loaded" class="rail-load">Cargando…</div>
        <template v-else>
        <div v-for="c in panelsFiltradas" :key="c.key"
             :class="['col', { active: selected === c.group, 'tag-matriz': c.kind==='matriz' }]"
             @click="selected = c.group; limpiarSel()">
          <span class="gi">{{ c.icon }}</span>
          <div class="cmeta">
            <span class="nm">{{ c.label }}</span>
            <span class="attrs">
              <span class="at">{{ c.kind==='matriz' ? 'nodriza' : c.kind==='none' ? 'sin agrupar' : c.kind==='all' ? 'todas' : 'organizativa' }}</span>
              <span class="at">· {{ c.count }} rec.</span>
            </span>
          </div>
          <span v-if="c.kind==='col'" class="edit" @click.stop>
            <button title="Renombrar" @click="abrirRename(c.g)">✎</button>
            <button class="del" title="Eliminar" @click="pedirBorrarCol(c.g)">🗑</button>
          </span>
        </div>
        </template>
      </div>

      <!-- panel de filtro de colecciones -->
      <div class="col-filter">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
        <input v-model="colFilter" placeholder="Filtrar colecciones…" />
        <button v-if="colFilter" class="clr" @click="colFilter=''">✕</button>
      </div>

      <div class="rail-foot"><span class="pulse"></span> {{ nActivos }} activos · {{ nPend }} descubiertos</div>
    </aside>

    <!-- divisor redimensionable -->
    <div class="divider" @mousedown="startDrag"><span></span></div>

    <!-- ============ MAIN ============ -->
    <main class="main">
      <div class="topbar">
        <button class="rail-toggle" @click="railOpen = !railOpen" :title="railOpen ? 'Ocultar colecciones' : 'Mostrar colecciones'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
        <div class="crumb">
          <div class="big">{{ tituloColeccion }}</div>
          <div class="meta">{{ metaColeccion }}</div>
        </div>
        <div class="spacer"></div>
        <button v-if="puede('recursos.crear')" class="btn primary" @click="abrirDrawer(null)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 5v14M5 12h14"/></svg>
          Nuevo recurso
        </button>
      </div>

      <div class="filters">
        <div class="search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
          <input v-model="q" placeholder="Buscar en esta colección…" />
        </div>
        <div class="chip pub-chip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4"/></svg>
          <select v-model="fPublisher"><option value="">Publisher: todos</option><option v-for="p in publishersUsados" :key="p.id" :value="p.id">{{ p.nombre || p.acronimo }}</option></select>
        </div>
        <div class="chip">
          <span class="sd-mini"></span>
          <select v-model="fStatus"><option value="">Estado: todos</option><option value="on">Activos</option><option value="off">Inactivos</option></select>
        </div>
      </div>

      <div class="listwrap">
        <!-- barra de acciones en lote (estilo master: inline, select + contextual) -->
        <div v-if="sel.size > 0" class="bulkbar">
          <span class="bn"><b>{{ sel.size }}</b> seleccionados</span>
          <select v-model="bulkAction" class="bsel">
            <option value="">Acción…</option>
            <option value="toggle">Activar/Desactivar (invertir)</option>
            <option value="run">Ejecutar (Run)</option>
            <option value="move">Mover a colección</option>
            <option value="group">Agrupar (nueva colección)</option>
            <option value="ungroup">Desagrupar</option>
          </select>
          <select v-if="bulkAction==='move'" v-model="bulkMoveTarget" class="bsel">
            <option value="">Elige colección…</option>
            <option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option>
          </select>
          <input v-if="bulkAction==='group'" v-model="bulkGroupName" class="bsel" placeholder="Nombre de la colección…" @keyup.enter="aplicarLote" />
          <button class="bapply" :disabled="bulkBusy || !bulkAction || (bulkAction==='move'&&!bulkMoveTarget) || (bulkAction==='group'&&!bulkGroupName.trim())" @click="aplicarLote">{{ bulkBusy?'Aplicando…':'Aplicar' }}</button>
          <button class="bclear" @click="limpiarSel">Limpiar</button>
        </div>

        <div v-if="loading" class="empty">Cargando…</div>
        <template v-else>
          <div class="lhead">
            <div><input type="checkbox" class="cbx" :checked="todasSel" @change="toggleTodas" /></div>
            <div>Recurso</div>
            <div class="col-pub">Publisher</div>
            <div>Estado</div>
            <div class="col-sched">Próxima ejecución</div>
            <div class="col-acts" style="text-align:right">Acciones</div>
          </div>

          <div v-if="topLevel.length === 0" class="empty">
            No hay recursos en esta colección.
            <button v-if="puede('recursos.crear')" class="link" @click="abrirDrawer(null)">Crear el primero</button>
          </div>

          <template v-for="r in topLevelPaged" :key="r.id">
            <div :class="['row', { sel: sel.has(r.id) }]">
              <div><input type="checkbox" class="cbx" :checked="sel.has(r.id)" @change="toggleRama(r)" /></div>
              <div class="rname">
                <span v-if="hijosDe(r.id).length" :class="['twist',{open:abiertas.has(r.id)}]" @click="toggleRamaOpen(r.id)">▸</span>
                <span v-else class="twist" style="visibility:hidden">▸</span>
                <span class="ttl">
                  <span v-if="esNodriza(r)">🛰️ </span>{{ r.name }}
                  <small v-if="hijosDe(r.id).length"> · {{ hijosDe(r.id).length }} descubiertos</small>
                </span>
              </div>
              <div class="col-pub pub" :title="r.publisherObj?.nombre || ''">{{ r.publisherObj?.acronimo || r.publisherObj?.nombre || '—' }}</div>
              <div><span :class="['status', estadoClase(r)]"><span class="sd"></span>{{ estadoTexto(r) }}</span></div>
              <div class="col-sched sched">
                <span :class="['nx', proximaEjecucion(r).t]">{{ proximaEjecucion(r).txt }}</span>
                <small v-if="proximaEjecucion(r).rel">{{ proximaEjecucion(r).rel }}</small>
              </div>
              <div class="col-acts racts">
                <button v-if="puede('ejecuciones.lanzar')" title="Ejecutar" @click="ejecutar(r)"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg></button>
                <button v-if="puede('recursos.editar')" title="Editar" @click="abrirDrawer(r)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H6a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2v-5M18.5 2.5a2.1 2.1 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
              </div>
            </div>
            <template v-if="abiertas.has(r.id)">
              <div v-for="ch in hijosDe(r.id)" :key="ch.id" :class="['row','child',{ sel: sel.has(ch.id) }]">
                <div><input type="checkbox" class="cbx" :checked="sel.has(ch.id)" @change="toggleUno(ch.id)" /></div>
                <div class="rname"><span class="twist" style="visibility:hidden">▸</span><span class="ttl">{{ ch.name }}</span></div>
                <div class="col-pub pub" :title="ch.publisherObj?.nombre || ''">{{ ch.publisherObj?.acronimo || ch.publisherObj?.nombre || '—' }}</div>
                <div><span :class="['status', estadoClase(ch)]"><span class="sd"></span>{{ estadoTexto(ch) }}</span></div>
                <div class="col-sched sched"><span :class="['nx', proximaEjecucion(ch).t]">{{ proximaEjecucion(ch).txt }}</span></div>
                <div class="col-acts racts">
                  <button v-if="puede('recursos.editar')" title="Editar" @click="abrirDrawer(ch)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H6a2 2 0 00-2 2v12a2 2 0 002 2h12a2 2 0 002-2v-5M18.5 2.5a2.1 2.1 0 013 3L12 15l-4 1 1-4 9.5-9.5z"/></svg></button>
                </div>
              </div>
            </template>
          </template>

          <div v-if="rTotal > 0" class="pager">
            <div class="pl">
              <span>Por página</span>
              <select v-model.number="rPerPage" @change="rPage=1">
                <option :value="10">10</option><option :value="25">25</option><option :value="50">50</option><option :value="100">100</option>
              </select>
            </div>
            <div class="pr">
              <span class="rng">{{ rDesde }}–{{ rHasta }} de {{ rTotal }}</span>
              <div class="pbtns">
                <button :disabled="rPage<=1" @click="rPage=1">«</button>
                <button :disabled="rPage<=1" @click="rPage--">‹</button>
                <span class="cur">{{ rPage }} / {{ rPaginas }}</span>
                <button :disabled="rPage>=rPaginas" @click="rPage++">›</button>
                <button :disabled="rPage>=rPaginas" @click="rPage=rPaginas">»</button>
              </div>
            </div>
          </div>
        </template>
      </div>
    </main>

    <!-- ============ DRAWER (resource editor) ============ -->
    <div :class="['scrim',{show:drawer}]" @click="cerrarDrawer"></div>
    <aside :class="['drawer',{show:drawer}]" :style="{ width: 'min('+drawerW+'px, 96vw)' }">
      <DrawerResizeHandle v-model="drawerW" storage-key="resources" />
      <div class="dh">
        <div class="di">{{ editing ? '✎' : '＋' }}</div>
        <div>
          <h2>{{ editing ? 'Editar recurso' : 'Nuevo recurso' }}</h2>
          <p>en · {{ tituloColeccion }}</p>
        </div>
        <button class="x" @click="cerrarDrawer">✕</button>
      </div>

      <div class="dbody">
        <div class="sect">
          <div class="sh"><span class="nidx">01</span><h3>Identidad</h3></div>
          <div class="sbody">
            <div class="field"><label>Nombre <span class="req">*</span></label>
              <input class="inp" v-model="form.name" placeholder="p. ej. Registro de Entidades Religiosas"></div>
            <div class="field"><label>Descripción</label>
              <textarea class="inp" v-model="form.description" placeholder="Qué publica esta fuente y para qué se cosecha"></textarea></div>
            <div class="row2">
              <div class="field"><label>Publisher</label>
                <select class="inp" v-model="form.publisherId"><option value="">—</option><option v-for="p in publishers" :key="p.id" :value="p.id">{{ p.nombre || p.acronimo }}</option></select></div>
              <div class="field"><label>Colección</label>
                <select class="inp" v-model="form.collectionId"><option value="">Sin agrupar</option><option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</option></select></div>
            </div>
          </div>
        </div>

        <div class="sect">
          <div class="sh"><span class="nidx">02</span><h3>Fuente</h3></div>
          <div class="sbody">
            <div class="field"><label>Fetcher <span class="req">*</span></label>
              <select class="inp" v-model="form.fetcherId"><option value="">—</option><option v-for="f in fetchers" :key="f.id" :value="f.id">{{ f.name }}</option></select></div>
            <div class="field"><label>Parámetros</label>
              <ResourceParamsEditor :fetcher="selectedFetcher" v-model="form.params" />
            </div>
          </div>
        </div>

        <div class="sect">
          <div class="sh"><span class="nidx">03</span><h3>Programación</h3></div>
          <div class="sbody">
            <div class="field"><label>Cuándo se cosecha</label>
              <ScheduleEditor v-model="form.schedule" />
            </div>
            <div class="tog"><div><div class="t">Activo</div><div class="s">Se ejecuta según la programación</div></div>
              <div :class="['sw',{on:form.active}]" @click="form.active=!form.active"></div></div>
          </div>
        </div>

        <div :class="['sect',{collapsed:!advOpen}]">
          <div class="sh" @click="advOpen=!advOpen"><span class="nidx">04</span><h3>Ejecución avanzada</h3><span class="tw">▾</span></div>
          <div class="sbody">
            <div class="steppers">
              <div v-for="s in steppers" :key="s.key" class="stp">
                <div class="lab"><span>{{ s.lab }}</span><span class="u">{{ s.unit }}</span></div>
                <div class="ctl"><button @click="s.val=Math.max(0,(+s.val||0)-1)">−</button>
                  <input v-model="s.val" :placeholder="globalCfg[s.key] != null ? String(globalCfg[s.key]) : ''"><button @click="s.val=(+s.val||0)+1">＋</button></div>
              </div>
            </div>
            <p class="hint">Vacío = usa el valor por defecto de Ajustes. Lo que pongas aquí lo sobreescribe solo para este recurso.</p>
          </div>
        </div>
      </div>

      <div class="dfoot">
        <button v-if="editing && puede('recursos.borrar')" class="del" @click="pedirBorrarRecurso">Eliminar recurso</button>
        <div class="grow"></div>
        <button class="ghost" @click="cerrarDrawer">Cancelar</button>
        <button class="save" :disabled="!form.name || !form.fetcherId || saving" @click="guardar">{{ saving ? 'Guardando…' : 'Guardar recurso' }}</button>
      </div>
    </aside>


    <!-- rename collection (reuse drawer-lite modal) -->
    <div v-if="rename.show" class="scrim show" @click.self="rename.show=false">
      <div class="confirm">
        <h2>Renombrar colección</h2>
        <input class="inp" v-model="rename.name" @keyup.enter="confirmarRename" autofocus />
        <div class="cf">
          <button class="ghost" @click="rename.show=false">Cancelar</button>
          <button class="save" @click="confirmarRename">Guardar</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import PageHeader from '../components/PageHeader.vue'
import { ref, computed, onMounted } from 'vue'
import { usePagination } from '../composables/usePagination'
import { useAuth } from '../composables/useAuth'
import ResourceParamsEditor from '../components/ResourceParamsEditor.vue'
import ScheduleEditor from '../components/ScheduleEditor.vue'
import DrawerResizeHandle from '../components/DrawerResizeHandle.vue'
import { useConfirm } from '../composables/useConfirm'
import { useToast } from '../composables/useToast'
import {
  fetchResources, fetchResourceCollections, fetchFetchers, fetchPublishers,
  createResource, updateResource, deleteResource, executeResource,
  createResourceCollection, renameResourceCollection, deleteResourceCollection,
  fetchAppConfig,
} from '../api/graphql'

const { puede } = useAuth()
const { confirm } = useConfirm()
const { toast } = useToast()

const loading = ref(true)
const loaded = ref(false)
const resources = ref([])
const groups = ref([])
const fetchers = ref([])
const publishers = ref([])

const selected = ref('__all__')   // colección abierta: '__all__' | id | '__none__'
const q = ref(''); const fType = ref(''); const fStatus = ref(''); const fPublisher = ref('')
const sel = ref(new Set())
const abiertas = ref(new Set())

// ---- rail redimensionable ----
const railW = ref(264)
const railOpen = ref(typeof window === 'undefined' || window.innerWidth >= 880)
let dragging = false
function startDrag(e){ dragging = true; e.preventDefault()
  const move = ev => { if(!dragging) return; railW.value = Math.min(440, Math.max(200, ev.clientX)) }
  const up = () => { dragging = false; window.removeEventListener('mousemove',move); window.removeEventListener('mouseup',up) }
  window.addEventListener('mousemove',move); window.addEventListener('mouseup',up)
}

// ---- filtro de colecciones ----
const colFilter = ref('')

// ---- próxima ejecución programada (calculada del cron, sin librería) ----
function parseField(f, lo, hi){
  if (f === '*' || f === '?') { const s=new Set(); for(let i=lo;i<=hi;i++) s.add(i); return s }
  const set = new Set()
  for (const part of f.split(',')){
    let m
    if ((m = part.match(/^(\*|\d+)(?:-(\d+))?(?:\/(\d+))?$/))){
      let a = m[1]==='*' ? lo : +m[1]
      let b = m[2]!=null ? +m[2] : (m[1]==='*' ? hi : (m[3]!=null ? hi : a))
      const step = m[3]!=null ? +m[3] : 1
      for(let i=a;i<=b;i+=step) if(i>=lo&&i<=hi) set.add(i)
    }
  }
  return set
}
function nextRun(cron){
  if (!cron) return null
  const p = cron.trim().split(/\s+/); if (p.length !== 5) return null
  let mins,hrs,doms,mons,dows
  try {
    mins=parseField(p[0],0,59); hrs=parseField(p[1],0,23); doms=parseField(p[2],1,31)
    mons=parseField(p[3],1,12); dows=parseField(p[4],0,6)
  } catch { return null }
  const domR = p[2] !== '*' && p[2] !== '?'
  const dowR = p[4] !== '*' && p[4] !== '?'
  const d = new Date(); d.setSeconds(0,0); d.setMinutes(d.getMinutes()+1)
  for (let guard=0; guard<366*24*60; guard++){
    if (!mons.has(d.getMonth()+1)){ d.setMonth(d.getMonth()+1,1); d.setHours(0,0,0,0); continue }
    const domOk = doms.has(d.getDate()); const dowOk = dows.has(d.getDay())
    const dayOk = domR && dowR ? (domOk||dowOk) : domR ? domOk : dowR ? dowOk : true
    if (!dayOk){ d.setDate(d.getDate()+1); d.setHours(0,0,0,0); continue }
    if (!hrs.has(d.getHours())){ d.setHours(d.getHours()+1,0,0,0); continue }
    if (!mins.has(d.getMinutes())){ d.setMinutes(d.getMinutes()+1,0,0); continue }
    return d
  }
  return null
}
function proximaEjecucion(r){
  if (!r.active) return { txt:'—', t:'inactivo' }
  if (!r.schedule) return { txt:'manual', t:'manual' }
  const d = nextRun(r.schedule)
  if (!d) return { txt:r.schedule, t:'cron' }
  const now = new Date(); const diff = d - now
  const fmt = d.toLocaleString('es-ES',{ day:'2-digit', month:'short', hour:'2-digit', minute:'2-digit' })
  let rel = ''
  const h = Math.round(diff/3600000)
  if (h < 1) rel = 'en breve'
  else if (h < 24) rel = `en ${h} h`
  else rel = `en ${Math.round(h/24)} d`
  return { txt: fmt, rel, t:'ok' }
}

// ---- barra de acciones en lote (estilo master) ----
const bulkAction = ref(''); const bulkMoveTarget = ref(''); const bulkGroupName = ref(''); const bulkBusy = ref(false)

// ---- carga ----
async function load() {
  loading.value = true
  try {
    const [rd, gd, td, pd] = await Promise.all([
      fetchResources(false), fetchResourceCollections(), fetchFetchers(), fetchPublishers(),
    ])
    resources.value = rd?.resources || []
    groups.value = (gd?.resourceCollections || []).slice().sort((a,b)=>a.name.localeCompare(b.name,'es'))
    fetchers.value = (td?.fetchers || []).slice().sort((a,b)=>a.name.localeCompare(b.name,'es'))
    publishers.value = pd?.publishers || []
    const gids = panels.value.map(p => p.group)
    if (!gids.includes(selected.value)) selected.value = gids[0] ?? '__none__'
  } finally { loading.value = false; loaded.value = true }
}
onMounted(load)
onMounted(async () => {
  try {
    const c = await fetchAppConfig()
    globalCfg.value = Object.fromEntries((c?.appConfig || []).map(x => [x.key, x.value ?? x.defaultValue]))
  } catch {}
})

// ---- panels (colecciones + sin agrupar) ----
function esNodriza(r) { return r?.generaColecciones === true }
function memberCount(id) { return resources.value.filter(r => r.collectionId === id).length }
const countSinAgrupar = computed(() => resources.value.filter(r => !r.collectionId).length)
const panels = computed(() => [
  { key:'all', group:'__all__', label:'Todos los recursos', icon:'📚', kind:'all', count: resources.value.length },
  ...groups.value.map(g => ({
    key:g.id, group:g.id, label:g.name, g,
    icon: g.origin === 'matriz' ? '🛰️' : '🗂️',
    kind: g.origin === 'matriz' ? 'matriz' : 'col',
    count: memberCount(g.id),
  })),
  { key:'none', group:'__none__', label:'Sin agrupar', icon:'🗃️', kind:'none', count: countSinAgrupar.value },
])
const tituloColeccion = computed(() => panels.value.find(p => p.group === selected.value)?.label || 'Recursos')
const metaColeccion = computed(() => {
  const p = panels.value.find(x => x.group === selected.value)
  if (!p) return ''
  const k = p.kind === 'all' ? 'todas las colecciones' : p.kind === 'matriz' ? 'nodriza' : p.kind === 'none' ? 'sin colección' : 'organizativa'
  return `${p.count} recursos · ${k}`
})
const nActivos = computed(() => resources.value.filter(r => r.active).length)
const nPend = computed(() => resources.value.filter(r => r.estadoAprobacion === 'pendiente').length)

// ---- lista de la colección abierta ----
const enColeccion = computed(() => resources.value.filter(r =>
  selected.value === '__all__' ? true
    : selected.value === '__none__' ? !r.collectionId
    : r.collectionId === selected.value))
const topLevel = computed(() => enColeccion.value.filter(r => !r.parentResourceId).filter(r => {
  if (q.value && !r.name.toLowerCase().includes(q.value.toLowerCase())) return false
  if (fType.value && r.fetcher?.code !== fType.value) return false
  if (fPublisher.value && r.publisherObj?.id !== fPublisher.value) return false
  if (fStatus.value === 'on' && !r.active) return false
  if (fStatus.value === 'off' && r.active) return false
  return true
}))
function hijosDe(id) { return resources.value.filter(r => r.parentResourceId === id) }
function toggleRamaOpen(id) { const s = new Set(abiertas.value); s.has(id)?s.delete(id):s.add(id); abiertas.value = s }
// Paginación de los recursos de la colección elegida.
const { page: rPage, perPage: rPerPage, total: rTotal, paged: topLevelPaged } = usePagination(topLevel, 25)
const rDesde = computed(()=> rTotal.value===0 ? 0 : (rPage.value-1)*rPerPage.value + 1)
const rHasta = computed(()=> Math.min(rPage.value*rPerPage.value, rTotal.value))
const rPaginas = computed(()=> Math.max(1, Math.ceil(rTotal.value / rPerPage.value)))
// Publishers que realmente aparecen en algún recurso (para el filtro).
const publishersUsados = computed(() => {
  const map = new Map()
  for (const r of resources.value) if (r.publisherObj?.id && !map.has(r.publisherObj.id)) map.set(r.publisherObj.id, r.publisherObj)
  return Array.from(map.values()).sort((a,b)=>(a.acronimo||a.nombre).localeCompare(b.acronimo||b.nombre,'es'))
})

function estadoClase(r){ if(r.estadoAprobacion==='pendiente')return'pend'; return r.active?'on':'off' }
function estadoTexto(r){ if(r.estadoAprobacion==='pendiente')return'Descubierto'; return r.active?'Activo':'Inactivo' }

// ---- selección en lote ----
function ramaDe(r){ return [r.id, ...hijosDe(r.id).map(c=>c.id)] }
function toggleRama(r){ const ids=ramaDe(r); const s=new Set(sel.value); const on=!ids.every(i=>s.has(i)); ids.forEach(i=>on?s.add(i):s.delete(i)); sel.value=s }
function toggleUno(id){ const s=new Set(sel.value); s.has(id)?s.delete(id):s.add(id); sel.value=s }
const todasSel = computed(()=> topLevelPaged.value.length>0 && topLevelPaged.value.every(r=>ramaDe(r).every(i=>sel.value.has(i))))
function toggleTodas(){ const s=new Set(sel.value); const on=!todasSel.value; topLevelPaged.value.forEach(r=>ramaDe(r).forEach(i=>on?s.add(i):s.delete(i))); sel.value=s }
function limpiarSel(){ sel.value=new Set() }
const seleccionados = computed(()=> resources.value.filter(r=>sel.value.has(r.id)))

const moveTarget = ref(''); const grpName = ref('')
async function aplicar(fn){ try{ await fn(); limpiarSel(); await load() }catch(e){ toast.error('Error: '+(e?.message||e)) } }
async function invertirEstado(){ await aplicar(async()=>{ for(const r of seleccionados.value) await updateResource(r.id,{active:!r.active}) }) }
async function moverSel(){ if(!moveTarget.value)return; await aplicar(async()=>{ for(const r of seleccionados.value) await updateResource(r.id,{collectionId:moveTarget.value}) }); moveTarget.value='' }
async function desagruparSel(){ await aplicar(async()=>{ for(const r of seleccionados.value) await updateResource(r.id,{collectionId:''}) }) }
async function agruparSel(){ const n=grpName.value.trim(); if(!n)return; await aplicar(async()=>{ const r=await createResourceCollection(n); const g=r?.createResourceCollection; if(!g)throw new Error('no creada'); for(const x of seleccionados.value) await updateResource(x.id,{collectionId:g.id}) }); grpName.value='' }

// dispatcher estilo master: una acción + control contextual
const panelsFiltradas = computed(() => {
  const f = colFilter.value.trim().toLowerCase()
  if (!f) return panels.value
  return panels.value.filter(p => p.label.toLowerCase().includes(f) || p.kind === 'none' || p.kind === 'all')
})
async function aplicarLote(){
  if (!bulkAction.value || sel.value.size===0) return
  bulkBusy.value = true
  try {
    if (bulkAction.value === 'toggle') { for(const r of seleccionados.value) await updateResource(r.id,{active:!r.active}) }
    else if (bulkAction.value === 'run') {
      // Ejecutar N recursos es costoso: confirmar antes.
      const n = seleccionados.value.length
      const objetivos = seleccionados.value.slice()
      bulkBusy.value = false
      const { ok } = await confirm({ title:'Ejecutar recursos', confirmText:`Ejecutar ${n}`,
        message:`Se lanzará la ejecución de ${n} recurso${n===1?'':'s'} ahora. Puede consumir tiempo y cuota. ¿Continuar?` })
      if (!ok) return
      bulkBusy.value = true
      try { for(const r of objetivos) await executeResource(r.id); bulkAction.value=''; limpiarSel(); await load() }
      catch(e){ toast.error('Error: '+(e?.message||e)) } finally{ bulkBusy.value=false }
      return
    }
    else if (bulkAction.value === 'move') { if(!bulkMoveTarget.value){bulkBusy.value=false;return} for(const r of seleccionados.value) await updateResource(r.id,{collectionId:bulkMoveTarget.value}) }
    else if (bulkAction.value === 'group') { const n=bulkGroupName.value.trim(); if(!n){bulkBusy.value=false;return} const rr=await createResourceCollection(n); const g=rr?.createResourceCollection; if(!g)throw new Error('no creada'); for(const r of seleccionados.value) await updateResource(r.id,{collectionId:g.id}) }
    else if (bulkAction.value === 'ungroup') { for(const r of seleccionados.value) await updateResource(r.id,{collectionId:''}) }
    bulkAction.value=''; bulkMoveTarget.value=''; bulkGroupName.value=''
    limpiarSel(); await load()
  } catch(e){ toast.error('Error: '+(e?.message||e)) }
  finally { bulkBusy.value=false }
}

// ---- colecciones CRUD ----
const showAdd = ref(false); const addName = ref('')
async function crearColeccion(){ const n=addName.value.trim(); if(!n)return; try{ const r=await createResourceCollection(n); const g=r?.createResourceCollection; addName.value=''; showAdd.value=false; await load(); if(g) selected.value=g.id }catch(e){ toast.error('Error: '+(e?.message||e)) } }
const rename = ref({show:false,g:null,name:''})
function abrirRename(g){ rename.value={show:true,g,name:g.name} }
async function confirmarRename(){ const n=rename.value.name.trim(); if(!n)return; try{ await renameResourceCollection(rename.value.g.id,n); rename.value.show=false; await load() }catch(e){ toast.error('Error: '+(e?.message||e)) } }
async function pedirBorrarCol(g){ const { ok } = await confirm({ title:'Eliminar colección', message:`¿Eliminar "${g.name}"? Sus recursos quedarán sin agrupar (no se borran).`, confirmText:'Eliminar', danger:true }); if(!ok) return; try{ await deleteResourceCollection(g.id); if(selected.value===g.id) selected.value='__all__'; await load() }catch(e){ toast.error('Error: '+(e?.message||e)) } }

// ---- drawer recurso ----
const drawer = ref(false); const editing = ref(null); const saving = ref(false); const advOpen = ref(false)
const drawerW = ref(760)
const selectedFetcher = computed(() => fetchers.value.find(f => f.id === form.value.fetcherId) || null)
const STEP_KEYS = [
  {key:'num_workers',lab:'Workers',unit:''},
  {key:'max_concurrent_requests',lab:'Concurrencia',unit:'req'},
  {key:'rate_limit_per_second',lab:'Rate limit',unit:'/s'},
  {key:'request_delay_ms',lab:'Delay',unit:'ms'},
  {key:'retry_attempts',lab:'Reintentos',unit:''},
  {key:'batch_size',lab:'Batch',unit:'filas'},
]
const steppers = ref(STEP_KEYS.map(s=>({...s,val:''})))
const globalCfg = ref({})   // defaults globales (Ajustes/Settings) por clave
const form = ref({ name:'', description:'', publisherId:'', collectionId:'', fetcherId:'', params:[], schedule:'', active:true })

function abrirDrawer(r){
  editing.value = r
  advOpen.value = false
  if (r){
    const stepKeys = STEP_KEYS.map(s=>s.key)
    form.value = {
      name:r.name, description:r.description||'', publisherId:r.publisherObj?.id||'',
      collectionId:r.collectionId||'', fetcherId:r.fetcher?.id||'',
      params:(r.params||[]).filter(p=>!stepKeys.includes(p.key)).map(p=>({key:p.key,value:p.value,isExternal:p.isExternal||false})),
      schedule:r.schedule||'', active:r.active!==false,
    }
    steppers.value = STEP_KEYS.map(s=>({ ...s, val:(r.params||[]).find(p=>p.key===s.key)?.value || '' }))
  } else {
    form.value = { name:'', description:'', publisherId:'', collectionId:((selected.value==='__none__'||selected.value==='__all__')?'':selected.value), fetcherId:'', params:[], schedule:'', active:true }
    steppers.value = STEP_KEYS.map(s=>({...s,val:''}))
  }
  drawer.value = true
}
function cerrarDrawer(){ drawer.value=false }
async function guardar(){
  saving.value = true
  try {
    const params = form.value.params.filter(p=>p.key&&(p.value!==''||p.isExternal)).map(p=>({key:p.key,value:String(p.value??''),isExternal:!!p.isExternal}))
    for (const s of steppers.value) if (s.val!=='' && s.val!=null) params.push({key:s.key,value:String(s.val),isExternal:false})
    const input = {
      name:form.value.name, description:form.value.description||null,
      publisherId:form.value.publisherId||null, fetcherId:form.value.fetcherId,
      params, active:form.value.active, schedule:form.value.schedule||null,
    }
    if (editing.value) await updateResource(editing.value.id, { ...input, collectionId: form.value.collectionId ?? '' })
    else await createResource(input)
    drawer.value = false
    await load()
  } catch(e){ toast.error('Error guardando: '+(e?.message||e)) }
  finally { saving.value = false }
}
async function pedirBorrarRecurso(){
  const r = editing.value
  const { ok } = await confirm({ title:'Eliminar recurso', message:`¿Eliminar "${r.name}"? Se borrará el recurso y su histórico.`, confirmText:'Eliminar', danger:true })
  if(!ok) return
  try{ await deleteResource(r.id,false); drawer.value=false; await load() }catch(e){ toast.error('Error: '+(e?.message||e)) }
}
async function ejecutar(r){ try{ await executeResource(r.id) }catch(e){ toast.error('No se pudo ejecutar: '+(e?.message||e)) } }
</script>

<style scoped>
.console{
  --ink:#0C0F14;--panel:#12171F;--panel-2:#161D27;--raised:#1B2430;--line:#222C39;--line-soft:#1A222E;
  --txt:#E7EEF6;--muted:#8595A6;--faint:#5A6878;--signal:#3FE0CB;--signal-dim:#1c5b54;--harvest:#F7B85C;--alert:#FF6B6B;--violet:#9C8CFF;
  --mono:'JetBrains Mono',ui-monospace,monospace;--disp:'Space Grotesk',Inter,sans-serif;
  display:grid;grid-template-columns:264px 1fr;height:calc(100vh - 0px);
  background:
    radial-gradient(1200px 600px at 80% -10%, #16313044, transparent 60%),
    radial-gradient(900px 500px at -10% 110%, #1d243a55, transparent 55%),
    var(--ink);
  color:var(--txt);font-size:14px;margin:-1rem;border-radius:0;overflow:hidden;
}
.console *{box-sizing:border-box}
.console.collapsed .rail, .console.collapsed .divider{display:none}
.rail-toggle{width:34px;height:34px;border-radius:9px;border:1px solid var(--line);color:var(--muted);display:grid;place-items:center;background:none;cursor:pointer;flex-shrink:0}
.rail-toggle:hover{color:var(--signal);border-color:var(--signal-dim);background:#0f201d}
.rail-toggle svg{width:17px;height:17px}
@media(max-width:880px){.rail{position:relative}}

.rail{background:linear-gradient(180deg,#10151d,#0d1218);border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0}
.brand{display:flex;align-items:center;gap:10px;padding:18px 18px 14px}
.roster-h{display:flex;align-items:center;justify-content:space-between;padding:8px 16px 6px}
.roster-h span{font-family:var(--mono);font-size:10px;letter-spacing:.16em;text-transform:uppercase;color:var(--faint)}
.roster-h button{width:22px;height:22px;border-radius:6px;color:var(--muted);font-size:16px;display:grid;place-items:center;border:1px solid var(--line);background:none;cursor:pointer}
.roster-h button:hover{color:var(--signal);border-color:var(--signal-dim);background:#0f2420}
.roster{overflow-y:auto;padding:4px 10px 10px;flex:1;min-height:0}
.col{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:10px;cursor:pointer;position:relative;margin-bottom:2px}
.col:hover{background:#161e29}
.col.active{background:linear-gradient(90deg,#15302c,#13202a);box-shadow:inset 0 0 0 1px #2b6a61}
.col.active::before{content:"";position:absolute;left:-10px;top:9px;bottom:9px;width:3px;border-radius:3px;background:var(--signal);box-shadow:0 0 10px var(--signal)}
.col .gi{width:18px;text-align:center;font-size:15px}
.col .nm{flex:1;font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.col .ct{font-family:var(--mono);font-size:11px;color:var(--faint);background:#0e151d;padding:1px 7px;border-radius:20px;border:1px solid var(--line-soft)}
.col.active .ct{color:var(--signal);border-color:var(--signal-dim)}
.col .edit{opacity:0;display:flex;gap:2px;position:absolute;right:8px;background:linear-gradient(90deg,transparent,#13202a 30%);padding-left:18px}
.col:hover .edit{opacity:1}
.col .edit button{width:22px;height:22px;border-radius:6px;color:var(--faint);display:grid;place-items:center;background:none;border:none;cursor:pointer}
.col .edit button:hover{color:var(--signal);background:#10211d}
.col .edit button.del:hover{color:var(--alert)}
.col.tag-matriz .gi{color:var(--violet)}
.rail-foot{padding:12px 16px;border-top:1px solid var(--line);font-size:11px;color:var(--faint);display:flex;align-items:center;gap:8px;font-family:var(--mono)}
.pulse{width:7px;height:7px;border-radius:50%;background:var(--signal);box-shadow:0 0 8px var(--signal);animation:pp 2s infinite}
@keyframes pp{0%,100%{opacity:1}50%{opacity:.35}}
.col-add{display:flex;gap:6px;padding:6px 8px;margin:2px 8px 6px}
.col-add input{flex:1;background:#0e151d;border:1px solid var(--signal-dim);border-radius:8px;padding:7px 10px;color:var(--txt);font-size:13px;outline:none}
.col-add button{padding:0 12px;border-radius:8px;background:var(--signal);color:#04201c;font-weight:600;font-size:12px;border:none;cursor:pointer}

.main{display:flex;flex-direction:column;min-width:0;min-height:0}
.topbar{display:flex;align-items:center;gap:14px;padding:16px 22px 12px}
.crumb{min-width:0}
.crumb .big{font-family:var(--disp);font-size:21px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.crumb .meta{font-family:var(--mono);font-size:11px;color:var(--faint)}
.spacer{flex:1}
.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 14px;border-radius:10px;font-weight:600;font-size:13px;border:1px solid var(--line);color:var(--muted);background:none;cursor:pointer}
.btn:hover{border-color:#34424f;color:var(--txt)}
.btn.primary{background:linear-gradient(180deg,var(--signal),#2bc3b0);color:#042521;border:none;box-shadow:0 6px 18px #1fd4be33}
.btn svg{width:15px;height:15px}
.filters{display:flex;align-items:center;gap:8px;padding:4px 22px 10px;flex-wrap:wrap}
.search{flex:0 1 230px;min-width:140px;position:relative}
.search input{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 12px 9px 34px;color:var(--txt);font-size:13px;outline:none}
.search input:focus{border-color:var(--signal-dim)}
.search svg{position:absolute;left:11px;top:50%;transform:translateY(-50%);width:15px;height:15px;color:var(--faint)}
.chip{display:inline-flex;align-items:center;gap:6px;padding:7px 11px;border-radius:9px;border:1px solid var(--line);background:var(--panel);font-size:12.5px;color:var(--muted)}
.pub-chip{flex:1 1 auto;min-width:170px}
.pub-chip select{flex:1;min-width:0}
.chip select{background:transparent;border:none;color:var(--txt);outline:none;font-size:12.5px}
.chip svg{width:13px;height:13px;color:var(--faint)}
.sd-mini{width:8px;height:8px;border-radius:50%;background:var(--signal);display:inline-block}

.listwrap{flex:1;overflow-y:auto;padding:2px 16px 90px}
.empty{text-align:center;color:var(--faint);padding:40px;font-size:13px}
.link{color:var(--signal);background:none;border:none;cursor:pointer;margin-left:6px}
.lhead{display:grid;grid-template-columns:30px minmax(0,1fr) 150px 104px 150px 78px;gap:8px;padding:9px 14px 8px;font-family:var(--disp);font-size:11px;font-weight:600;letter-spacing:.04em;color:var(--muted);position:sticky;top:0;background:var(--ink);z-index:3;border-bottom:1px solid var(--line)}
.row{display:grid;grid-template-columns:30px minmax(0,1fr) 150px 104px 150px 78px;gap:8px;align-items:center;padding:11px 14px;border-radius:12px;margin:3px 0;background:var(--panel);border:1px solid var(--line-soft)}
.row:hover{border-color:#2c3a48;background:var(--panel-2)}
.row.sel{border-color:var(--signal-dim);background:#10211e}
.row.child{background:#0f141bcc;margin-left:30px;border-style:dashed;border-color:#1c2733}
@media(max-width:1100px){.lhead,.row{grid-template-columns:30px 1fr 110px 78px}.col-sched,.col-pub{display:none!important}}
.cbx{appearance:none;width:17px;height:17px;border-radius:5px;border:1.5px solid #36434f;background:#0d1219;cursor:pointer;position:relative}
.cbx:checked{background:var(--signal);border-color:var(--signal)}
.cbx:checked::after{content:"✓";position:absolute;inset:0;display:grid;place-items:center;color:#042521;font-size:11px;font-weight:800}
.rname{display:flex;align-items:center;gap:9px;min-width:0}
.rname .twist{width:16px;color:var(--faint);font-size:11px;cursor:pointer;transition:.15s}
.rname .twist.open{transform:rotate(90deg);color:var(--signal)}
.rname .ttl{font-weight:500;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rname .ttl small{color:var(--faint)}
.badge{font-family:var(--mono);font-size:9.5px;text-transform:uppercase;padding:2px 7px;border-radius:5px;border:1px solid;white-space:nowrap}
.badge.sys{color:var(--muted);border-color:var(--line);background:#121922}
.ftype{display:flex;align-items:center;gap:7px;font-size:12px;color:var(--muted)}
.ftype .dot{width:6px;height:6px;border-radius:50%;background:var(--violet)}
.status{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:500}
.status .sd{width:8px;height:8px;border-radius:50%}
.status.on{color:var(--signal)}.status.on .sd{background:var(--signal);box-shadow:0 0 8px var(--signal);animation:pp 2.4s infinite}
.status.off{color:var(--faint)}.status.off .sd{background:#3a4654}
.status.pend{color:var(--harvest)}.status.pend .sd{background:var(--harvest);box-shadow:0 0 8px var(--harvest)}
.sched{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
.pub{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.racts{display:flex;gap:4px;justify-content:flex-end;opacity:1}
.racts button{width:28px;height:28px;border-radius:8px;border:1px solid #1d4ed8;color:#3b82f6;display:grid;place-items:center;background:#3b82f612;cursor:pointer}
.racts button:hover{color:#60a5fa;border-color:#3b82f6;background:#3b82f622}
.racts button svg{width:14px;height:14px}

.bulk{position:fixed;left:50%;bottom:22px;transform:translate(-50%,30px);opacity:0;pointer-events:none;transition:.25s cubic-bezier(.2,.9,.3,1.2);display:flex;align-items:center;gap:12px;background:linear-gradient(180deg,#1b2530,#141c25);border:1px solid #2d3a48;border-radius:14px;padding:10px 12px 10px 16px;box-shadow:0 16px 50px #000a;z-index:40}
.bulk.show{opacity:1;pointer-events:auto;transform:translate(-50%,0)}
.bulk .n{font-weight:600;font-size:13px}.bulk .n b{color:var(--signal)}
.bulk .vsep{width:1px;height:22px;background:var(--line)}
.bulk button.act{padding:8px 12px;border-radius:9px;border:1px solid var(--line);font-size:12.5px;color:var(--muted);background:none;cursor:pointer}
.bulk button.act:hover{color:var(--txt);border-color:#3a4856;background:#1c2632}
.bulk .grp{display:flex;align-items:center;background:#0e151d;border:1px solid var(--line);border-radius:9px;overflow:hidden}
.bulk .grp select,.bulk .grp input{background:transparent;border:none;color:var(--txt);padding:8px 10px;outline:none;font-size:12.5px;max-width:150px}
.bulk .grp button{padding:8px 11px;background:var(--signal);color:#042521;font-weight:600;border:none;cursor:pointer}
.bulk .x{width:30px;height:30px;border-radius:8px;color:var(--faint);background:none;border:none;cursor:pointer}.bulk .x:hover{color:var(--txt);background:#1c2632}

.scrim{position:fixed;inset:0;background:#04060a99;backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:.25s;z-index:50}
.scrim.show{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;height:100vh;width:min(760px,96vw);background:linear-gradient(180deg,#131922,#0f141b);border-left:1px solid var(--line);transform:translateX(102%);transition:transform .3s cubic-bezier(.3,.8,.3,1);z-index:60;display:flex;flex-direction:column}
.drawer.show{transform:translateX(0)}
.dh{display:flex;align-items:flex-start;gap:12px;padding:20px 22px 16px;border-bottom:1px solid var(--line)}
.dh .di{width:40px;height:40px;border-radius:11px;background:#10211d;border:1px solid var(--signal-dim);display:grid;place-items:center;font-size:19px;flex-shrink:0}
.dh h2{font-family:var(--disp);font-size:18px;margin:0 0 2px;font-weight:600}
.dh p{margin:0;font-size:12px;color:var(--faint);font-family:var(--mono)}
.dh .x{margin-left:auto;width:32px;height:32px;border-radius:9px;color:var(--muted);font-size:18px;display:grid;place-items:center;border:1px solid var(--line);background:none;cursor:pointer}
.dbody{flex:1;overflow-y:auto;padding:6px 22px 30px}
.sect{border-top:1px solid var(--line-soft);padding:18px 0}
.sect:first-child{border-top:none}
.sect>.sh{display:flex;align-items:center;gap:9px;margin-bottom:14px;cursor:pointer}
.sect>.sh .nidx{font-family:var(--mono);font-size:10px;color:var(--signal);border:1px solid var(--signal-dim);border-radius:5px;padding:2px 6px;background:#0f201d}
.sect>.sh h3{font-family:var(--disp);font-size:13px;font-weight:600;margin:0}
.sect>.sh .tw{margin-left:auto;color:var(--faint);font-size:12px}
.sect.collapsed .tw{transform:rotate(-90deg)}
.sect.collapsed .sbody{display:none}
.hint{font-size:11px;color:var(--faint);margin:10px 0 0}
.field{margin-bottom:14px}
.field>label{display:block;font-size:12px;font-weight:500;color:var(--muted);margin-bottom:6px}
.field>label .req{color:var(--signal)}
.inp{width:100%;background:#0d131b;border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--txt);font-size:13.5px;outline:none}
.inp:focus{border-color:var(--signal-dim)}
textarea.inp{resize:vertical;min-height:60px;line-height:1.5}
.inp.mono{font-family:var(--mono);font-size:12.5px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.steppers{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:10px}
.stp{background:#0d131b;border:1px solid var(--line);border-radius:10px;padding:9px 10px}
.stp .lab{font-size:10.5px;color:var(--faint);text-transform:uppercase;font-family:var(--mono);margin-bottom:4px;display:flex;justify-content:space-between}
.stp .lab .u{color:#4a5765}
.stp .ctl{display:flex;align-items:center;gap:6px}
.stp .ctl button{width:24px;height:24px;border-radius:7px;border:1px solid var(--line);color:var(--muted);font-size:15px;display:grid;place-items:center;background:none;cursor:pointer}
.stp .ctl button:hover{color:var(--signal);border-color:var(--signal-dim)}
.stp .ctl input{flex:1;width:100%;background:transparent;border:none;color:var(--txt);font-family:var(--mono);font-size:15px;text-align:center;outline:none}
.tog{display:flex;align-items:center;justify-content:space-between;padding:11px 13px;background:#0d131b;border:1px solid var(--line);border-radius:10px}
.tog .t{font-size:13px;font-weight:500}.tog .s{font-size:11px;color:var(--faint);margin-top:2px}
.sw{width:40px;height:23px;border-radius:20px;background:#26313d;position:relative;transition:.2s;flex-shrink:0;cursor:pointer}
.sw::after{content:"";position:absolute;top:2.5px;left:2.5px;width:18px;height:18px;border-radius:50%;background:#cdd7e1;transition:.2s}
.sw.on{background:var(--signal-dim)}.sw.on::after{left:19px;background:var(--signal)}
.params .ph{display:grid;grid-template-columns:minmax(120px,0.8fr) 2fr 30px;gap:8px;font-family:var(--mono);font-size:10px;text-transform:uppercase;color:var(--faint);padding:0 2px 6px}
.prow{display:grid;grid-template-columns:minmax(120px,0.8fr) 2fr 30px;gap:8px;margin-bottom:7px}
.prow input{background:#0d131b;border:1px solid var(--line);border-radius:8px;padding:8px 10px;color:var(--txt);font-family:var(--mono);font-size:12px;outline:none}
.prow .rm{border:1px solid var(--line);border-radius:8px;color:var(--faint);background:none;cursor:pointer}.prow .rm:hover{color:var(--alert)}
.addp{font-size:12px;color:var(--signal);background:none;border:none;cursor:pointer;margin-top:4px;font-weight:500}
.cron{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px}
.cron button{padding:7px 12px;border-radius:9px;border:1px solid var(--line);font-size:12px;color:var(--muted);background:none;cursor:pointer}
.cron button.on{border-color:var(--signal-dim);background:#0f201d;color:var(--signal)}
.dfoot{display:flex;align-items:center;gap:10px;padding:14px 22px;border-top:1px solid var(--line);background:#0f141b}
.dfoot .del{color:var(--alert);font-size:12.5px;font-weight:500;background:none;border:none;cursor:pointer}
.dfoot .grow{flex:1}
.dfoot .ghost{padding:10px 16px;border-radius:10px;border:1px solid var(--line);color:var(--muted);font-weight:500;font-size:13px;background:none;cursor:pointer}
.dfoot .save{padding:10px 20px;border-radius:10px;background:linear-gradient(180deg,var(--signal),#2bc3b0);color:#042521;font-weight:700;font-size:13px;border:none;cursor:pointer}
.dfoot .save:disabled{opacity:.45;cursor:not-allowed}
.confirm{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);background:#131922;border:1px solid var(--line);border-radius:14px;padding:22px;width:min(420px,92vw);z-index:70}
.confirm h2{font-family:var(--disp);font-size:18px;margin:0 0 10px}
.confirm p{color:var(--muted);font-size:13px;margin:0 0 16px;line-height:1.5}
.confirm .inp{margin-bottom:16px}
.cf{display:flex;justify-content:flex-end;gap:10px}
.cf .ghost{padding:9px 16px;border-radius:10px;border:1px solid var(--line);color:var(--muted);background:none;cursor:pointer}
.cf .danger{padding:9px 18px;border-radius:10px;background:var(--alert);color:#2a0b0b;font-weight:700;border:none;cursor:pointer}
.cf .save{padding:9px 18px;border-radius:10px;background:var(--signal);color:#042521;font-weight:700;border:none;cursor:pointer}

/* --- divisor redimensionable --- */
.divider{cursor:col-resize;display:flex;align-items:center;justify-content:center;background:transparent}
.divider span{width:2px;height:46px;border-radius:2px;background:var(--line);transition:.15s}
.divider:hover span{background:var(--signal);box-shadow:0 0 8px var(--signal)}

/* --- colección con atributos (dos líneas) --- */
.col{align-items:center}
.col .cmeta{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.col .cmeta .nm{font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.col .attrs{display:flex;gap:5px;font-family:var(--mono);font-size:10px;color:var(--faint)}
.col.active .attrs{color:#6fb9af}
.col.tag-matriz .attrs .at:first-child{color:var(--violet)}

/* --- filtro de colecciones --- */
.col-filter{display:flex;align-items:center;gap:8px;margin:6px 12px 4px;padding:7px 10px;background:#0e151d;border:1px solid var(--line);border-radius:9px}
.col-filter svg{width:13px;height:13px;color:var(--faint);flex-shrink:0}
.col-filter input{flex:1;min-width:0;background:transparent;border:none;color:var(--txt);font-size:12px;outline:none}
.col-filter .clr{color:var(--faint);background:none;border:none;cursor:pointer;font-size:12px}

/* --- barra de lote inline (estilo master) --- */
.bulkbar{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:4px 0 8px;padding:9px 12px;border-radius:11px;background:#10211e;border:1px solid var(--signal-dim)}
.bulkbar .bn{font-size:12.5px;color:#9fded3}.bulkbar .bn b{color:var(--signal)}
.bulkbar .bsel{background:#0d131b;border:1px solid var(--line);border-radius:8px;color:var(--txt);padding:7px 10px;font-size:12.5px;outline:none}
.bulkbar .bsel:focus{border-color:var(--signal-dim)}
.bulkbar .bapply{padding:7px 14px;border-radius:8px;background:var(--signal);color:#042521;font-weight:600;font-size:12.5px;border:none;cursor:pointer}
.bulkbar .bapply:disabled{opacity:.4;cursor:not-allowed}
.bulkbar .bclear{padding:7px 12px;border-radius:8px;border:1px solid var(--line);color:var(--muted);background:none;cursor:pointer;font-size:12.5px}
.bulkbar .bclear:hover{color:var(--txt);border-color:#34424f}

/* --- próxima ejecución --- */
.col-sched.sched{display:flex;flex-direction:column;gap:1px}
.nx{font-family:var(--mono);font-size:11.5px;color:var(--muted)}
.nx.manual{color:var(--faint)}.nx.inactivo{color:#3a4654}.nx.ok{color:var(--signal)}
.col-sched small{font-family:var(--mono);font-size:10px;color:var(--faint)}
.pager{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:10px 2px 4px;padding:10px 12px;border-top:1px solid var(--line-soft);font-size:12px;color:var(--muted)}
.pager .pl{display:flex;align-items:center;gap:8px;font-family:var(--mono);font-size:11px;color:var(--faint)}
.pager .pl select{background:#0d131b;border:1px solid var(--line);border-radius:7px;color:var(--txt);padding:5px 8px;outline:none}
.pager .pr{display:flex;align-items:center;gap:14px}
.pager .rng{font-family:var(--mono);font-size:11px;color:var(--faint)}
.pager .pbtns{display:flex;align-items:center;gap:4px}
.pager .pbtns button{width:28px;height:28px;border-radius:8px;border:1px solid var(--line);color:var(--muted);background:none;cursor:pointer;font-size:14px}
.pager .pbtns button:hover:not(:disabled){color:var(--signal);border-color:var(--signal-dim);background:#0f201d}
.pager .pbtns button:disabled{opacity:.3;cursor:not-allowed}
.pager .pbtns .cur{font-family:var(--mono);font-size:11.5px;color:var(--txt);padding:0 6px}
.rail-load{padding:1rem .4rem;color:#6b7280;font-size:.78rem}
</style>
