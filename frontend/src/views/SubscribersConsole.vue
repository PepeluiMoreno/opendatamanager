<template>
  <div class="subs-shell">
    <div class="subs-tabs">
      <button :class="['stab',{on:tab==='activos'}]" @click="tab='activos'">Activos</button>
      <button v-if="canApprove" :class="['stab',{on:tab==='pendientes'}]" @click="tab='pendientes'">Pendientes</button>
    </div>
    <div v-show="tab==='activos'" :class="['console', { collapsed: !railOpen }]" :style="{ gridTemplateColumns: railOpen ? (railW + 'px 6px 1fr') : '0 0 1fr' }">
    <!-- ===== SUBSCRIBERS RAIL ===== -->
    <aside class="rail">
      <div class="brand">
        <PageHeader title="Suscriptores" subtitle="Vista nueva · beta" tight />
      </div>
      <div class="roster-h">
        <span>Suscriptores</span>
        <button v-if="puede('subscribers.crear')" @click="abrirDrawer(null)" title="Nuevo suscriptor">+</button>
      </div>
      <div class="roster">
        <div v-for="s in subsFiltrados" :key="s.id"
             :class="['col', { active: selected === s.id }]" @click="selected = s.id; limpiarSel()">
          <span class="gi">{{ s.active ? '🟢' : '⚪' }}</span>
          <div class="cmeta">
            <span class="nm">{{ s.name }}</span>
            <span class="attrs">
              <span class="at">{{ modoLabel(s.consumptionMode) }}</span>
              <span class="at">· {{ nSubs(s.id) }} susc.</span>
            </span>
          </div>
          <span class="edit" @click.stop>
            <button title="Editar" @click="abrirDrawer(s)">✎</button>
            <button class="del" title="Eliminar" @click="pedirBorrarSub(s)">🗑</button>
          </span>
        </div>
      </div>
      <div class="col-filter">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
        <input v-model="subFilter" placeholder="Filtrar suscriptores…" />
        <button v-if="subFilter" class="clr" @click="subFilter=''">✕</button>
      </div>
      <div class="rail-foot"><span class="pulse"></span> {{ nActivos }} activos · {{ subscribers.length }} suscriptores</div>
    </aside>

    <div class="divider" @mousedown="startDrag"><span></span></div>

    <!-- ===== MAIN: SUBSCRIPTIONS ===== -->
    <main class="main">
      <div class="topbar">
        <button class="rail-toggle" @click="railOpen = !railOpen" :title="railOpen ? 'Ocultar suscriptores' : 'Mostrar suscriptores'">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
        </button>
        <div class="crumb">
          <div class="big">{{ subActual?.name || 'Suscriptores' }}</div>
          <div class="meta">{{ metaSub }}</div>
        </div>
        <div class="spacer"></div>
        <button v-if="subActual && puede('subscribers.editar')" class="btn primary" @click="abrirNuevaSusc">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 5v14M5 12h14"/></svg>
          Nueva suscripción
        </button>
      </div>

      <div class="filters" v-if="subActual">
        <div class="search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
          <input v-model="q" placeholder="Buscar recurso…" />
        </div>
        <div class="chip pub-chip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4"/></svg>
          <select v-model="fPublisher"><option value="">Publisher: todos</option><option v-for="p in publishersUsados" :key="p.id" :value="p.id">{{ p.nombre || p.acronimo }}</option></select>
        </div>
        <div class="chip">
          <select v-model="fUpgrade"><option value="">Auto-upgrade: todos</option><option v-for="u in upgradeOpts" :key="u" :value="u">{{ u }}</option></select>
        </div>
      </div>

      <div class="listwrap">
        <div v-if="!subActual" class="empty">Elige un suscriptor a la izquierda para ver sus suscripciones.</div>
        <template v-else>
          <div v-if="sel.size > 0" class="bulkbar">
            <span class="bn"><b>{{ sel.size }}</b> seleccionadas</span>
            <button class="bapply danger-btn" :disabled="bulkBusy" @click="bajaLote">{{ bulkBusy?'Cancelando…':'Cancelar suscripción' }}</button>
            <button class="bclear" @click="limpiarSel">Limpiar</button>
          </div>
          <div v-if="loading" class="empty">Cargando…</div>
          <template v-else>
            <div class="lhead">
              <div><input type="checkbox" class="cbx" :checked="todasSel" @change="toggleTodas" /></div>
              <div>Recurso</div>
              <div class="col-pub">Publisher</div>
              <div>Auto-upgrade</div>
              <div class="col-sched">Versión</div>
              <div class="col-acts" style="text-align:right">Acciones</div>
            </div>
            <div v-if="subsDelActual.length === 0" class="empty">
              Este suscriptor no tiene suscripciones.
              <button class="link" @click="abrirNuevaSusc">Añadir la primera</button>
            </div>
            <div v-for="su in subsPaginadas" :key="su.id" :class="['row', { sel: sel.has(su.id) }]">
              <div><input type="checkbox" class="cbx" :checked="sel.has(su.id)" @change="toggleUno(su.id)" /></div>
              <div class="rname"><span class="twist" style="visibility:hidden">▸</span><span class="ttl">{{ recDe(su.resourceId)?.name || su.resourceId }}</span></div>
              <div class="col-pub pub" :title="recDe(su.resourceId)?.publisherObj?.nombre || ''">{{ recDe(su.resourceId)?.publisherObj?.acronimo || recDe(su.resourceId)?.publisherObj?.nombre || '—' }}</div>
              <div><span class="status on" v-if="su.autoUpgrade && su.autoUpgrade!=='none'"><span class="sd"></span>{{ su.autoUpgrade }}</span><span class="status off" v-else><span class="sd"></span>fijada</span></div>
              <div class="col-sched sched"><span class="nx ok">{{ su.currentVersion || '—' }}</span><small v-if="su.pinnedVersion">pin {{ su.pinnedVersion }}</small></div>
              <div class="col-acts racts">
                <button class="danger" title="Cancelar suscripción" @click="pedirBaja(su)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 7l-.9 12.1A2 2 0 0116.1 21H7.9a2 2 0 01-2-1.9L5 7m5 4v6m4-6v6M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3M4 7h16"/></svg></button>
              </div>
            </div>

            <div v-if="total > 0" class="pager">
              <div class="pl">
                <span>Por página</span>
                <select v-model.number="perPage" @change="page=1">
                  <option :value="10">10</option><option :value="25">25</option><option :value="50">50</option><option :value="100">100</option>
                </select>
              </div>
              <div class="pr">
                <span class="rng">{{ desde }}–{{ hasta }} de {{ total }}</span>
                <div class="pbtns">
                  <button :disabled="page<=1" @click="page=1">«</button>
                  <button :disabled="page<=1" @click="page--">‹</button>
                  <span class="cur">{{ page }} / {{ totalPaginas }}</span>
                  <button :disabled="page>=totalPaginas" @click="page++">›</button>
                  <button :disabled="page>=totalPaginas" @click="page=totalPaginas">»</button>
                </div>
              </div>
            </div>
          </template>
        </template>
      </div>
    </main>

    <!-- ===== DRAWER: subscriber editor ===== -->
    <div :class="['scrim',{show:drawer}]" @click="cerrarDrawer"></div>
    <aside :class="['drawer',{show:drawer}]" :style="{ width: 'min('+drawerW+'px, 96vw)' }">
      <DrawerResizeHandle v-model="drawerW" storage-key="subscribers" />
      <div class="dh">
        <div class="di">{{ editing ? '✎' : '＋' }}</div>
        <div><h2>{{ editing ? 'Editar suscriptor' : 'Nuevo suscriptor' }}</h2><p>consumidor de datos</p></div>
        <button class="x" @click="cerrarDrawer">✕</button>
      </div>
      <div class="dbody">
        <div class="sect">
          <div class="sh"><span class="nidx">01</span><h3>Identidad</h3></div>
          <div class="sbody">
            <div class="field"><label>Nombre <span class="req">*</span></label><input class="inp" v-model="form.name" placeholder="p. ej. ckan-jerez"></div>
            <div class="field"><label>Descripción</label><textarea class="inp" v-model="form.description" placeholder="Qué consume y para qué"></textarea></div>
            <div class="field"><label>Propósito</label><input class="inp" v-model="form.proposito" placeholder="Finalidad del consumo"></div>
            <div class="tog"><div><div class="t">Activo</div><div class="s">Recibe notificaciones y puede consumir</div></div><div :class="['sw',{on:form.active}]" @click="form.active=!form.active"></div></div>
          </div>
        </div>
        <div class="sect">
          <div class="sh"><span class="nidx">02</span><h3>Entrega</h3></div>
          <div class="sbody">
            <div class="field"><label>Modo de consumo</label>
              <div class="seg">
                <button :class="{on:form.consumptionMode==='webhook',sig:form.consumptionMode==='webhook'}" @click="form.consumptionMode='webhook'">Webhook</button>
                <button :class="{on:form.consumptionMode==='graphql',sig:form.consumptionMode==='graphql'}" @click="form.consumptionMode='graphql'">GraphQL</button>
                <button :class="{on:form.consumptionMode==='both',sig:form.consumptionMode==='both'}" @click="form.consumptionMode='both'">Ambos</button>
              </div>
            </div>
            <div class="field" v-if="form.consumptionMode!=='graphql'"><label>URL de webhook</label><input class="inp mono" v-model="form.webhookUrl" placeholder="https://tu-app/webhooks/odmgr"></div>
          </div>
        </div>
        <div class="sect">
          <div class="sh"><span class="nidx">03</span><h3>Contacto</h3></div>
          <div class="sbody">
            <div class="row2">
              <div class="field"><label>Persona</label><input class="inp" v-model="form.personaContacto"></div>
              <div class="field"><label>Email</label><input class="inp" v-model="form.email" type="email"></div>
            </div>
            <div class="row2">
              <div class="field"><label>Teléfono</label><input class="inp" v-model="form.telefono"></div>
              <div class="field"><label>GitHub</label><input class="inp mono" v-model="form.githubUrl" placeholder="https://github.com/…"></div>
            </div>
          </div>
        </div>
      </div>
      <div class="dfoot">
        <button v-if="editing && puede('subscribers.borrar')" class="del" @click="pedirBorrarSubDrawer">Eliminar suscriptor</button>
        <div class="grow"></div>
        <button class="ghost" @click="cerrarDrawer">Cancelar</button>
        <button class="save" :disabled="!form.name || saving" @click="guardar">{{ saving ? 'Guardando…' : 'Guardar' }}</button>
      </div>
    </aside>

    <!-- ===== nueva suscripción ===== -->
    <div v-if="nuevaSusc.show" class="scrim show" @click.self="nuevaSusc.show=false">
      <div class="confirm">
        <h2>Nueva suscripción</h2>
        <div class="field"><label>Recurso</label>
          <select class="inp" v-model="nuevaSusc.resourceId">
            <option value="">Elige recurso…</option>
            <option v-for="r in recursosSuscribibles" :key="r.id" :value="r.id">{{ r.name }}{{ r.publisherObj?.acronimo ? ' — '+r.publisherObj.acronimo : '' }}</option>
          </select></div>
        <div class="field"><label>Auto-upgrade</label>
          <select class="inp" v-model="nuevaSusc.autoUpgrade"><option v-for="u in upgradeOpts" :key="u" :value="u">{{ u }}</option></select></div>
        <div class="cf">
          <button class="ghost" @click="nuevaSusc.show=false">Cancelar</button>
          <button class="save" :disabled="!nuevaSusc.resourceId || nuevaSusc.busy" @click="crearSuscripcion">{{ nuevaSusc.busy?'Suscribiendo…':'Suscribir' }}</button>
        </div>
      </div>
    </div>

    </div><!-- /console activos -->

    <div v-if="tab==='pendientes'" class="pend-wrap"><Aprobaciones /></div>
  </div>
</template>

<script setup>
import PageHeader from '../components/PageHeader.vue'
import { ref, computed, onMounted } from 'vue'
import { useAuth } from '../composables/useAuth'
import Aprobaciones from './Aprobaciones.vue'
import { usePagination } from '../composables/usePagination'
import { useConfirm } from '../composables/useConfirm'
import { useToast } from '../composables/useToast'
import DrawerResizeHandle from '../components/DrawerResizeHandle.vue'
import {
  fetchSubscribers, createSubscriber, updateSubscriber, deleteSubscriber,
  fetchSubscriptions, subscribeResource, unsubscribeResource, fetchResources,
} from '../api/graphql'

const { puede } = useAuth()
const { confirm } = useConfirm()
const { toast } = useToast()
const tab = ref('activos')
const canApprove = computed(() => puede('aplicaciones.aprobar') || puede('recursos.aprobar'))
const loading = ref(true)
const subscribers = ref([]); const subscriptions = ref([]); const resources = ref([])
const selected = ref(null)
const q = ref(''); const fPublisher = ref(''); const fUpgrade = ref('')
const sel = ref(new Set())
const upgradeOpts = ['none','patch','minor','major']

const railW = ref(264); const railOpen = ref(typeof window === 'undefined' || window.innerWidth >= 880); let dragging=false
function startDrag(e){ dragging=true; e.preventDefault()
  const mv=ev=>{ if(dragging) railW.value=Math.min(440,Math.max(200,ev.clientX)) }
  const up=()=>{ dragging=false; window.removeEventListener('mousemove',mv); window.removeEventListener('mouseup',up) }
  window.addEventListener('mousemove',mv); window.addEventListener('mouseup',up) }
const subFilter = ref('')

function modoLabel(m){ return m==='both'?'webhook+graphql':m||'—' }
async function load(){
  loading.value=true
  try{
    const [sd,td,rd]=await Promise.all([fetchSubscribers(),fetchSubscriptions(),fetchResources(false)])
    subscribers.value=(sd?.subscribers||[]).slice().sort((a,b)=>a.name.localeCompare(b.name,'es'))
    subscriptions.value=td?.resourceSubscriptions||[]
    resources.value=rd?.resources||[]
    if(!subscribers.value.find(s=>s.id===selected.value)) selected.value=subscribers.value[0]?.id||null
  } finally{ loading.value=false }
}
onMounted(load)

const subsFiltrados = computed(()=>{ const f=subFilter.value.trim().toLowerCase(); return f?subscribers.value.filter(s=>s.name.toLowerCase().includes(f)):subscribers.value })
const subActual = computed(()=> subscribers.value.find(s=>s.id===selected.value)||null)
function nSubs(id){ return subscriptions.value.filter(x=>x.applicationId===id).length }
const nActivos = computed(()=> subscribers.value.filter(s=>s.active).length)
function recDe(id){ return resources.value.find(r=>r.id===id) }
const metaSub = computed(()=>{ const s=subActual.value; if(!s) return ''; return `${nSubs(s.id)} suscripciones · ${modoLabel(s.consumptionMode)} · ${s.active?'activo':'inactivo'}` })

const subsDelActual = computed(()=> subscriptions.value.filter(x=>x.applicationId===selected.value).filter(su=>{
  const r=recDe(su.resourceId)
  if(q.value && !(r?.name||'').toLowerCase().includes(q.value.toLowerCase())) return false
  if(fPublisher.value && r?.publisherObj?.id!==fPublisher.value) return false
  if(fUpgrade.value && (su.autoUpgrade||'none')!==fUpgrade.value) return false
  return true
}))
const publishersUsados = computed(()=>{ const m=new Map(); for(const su of subscriptions.value.filter(x=>x.applicationId===selected.value)){ const r=recDe(su.resourceId); if(r?.publisherObj?.id&&!m.has(r.publisherObj.id)) m.set(r.publisherObj.id,r.publisherObj) } return Array.from(m.values()).sort((a,b)=>(a.acronimo||a.nombre).localeCompare(b.acronimo||b.nombre,'es')) })

// paginación de suscripciones (misma lógica que el resto de la app)
const { page, perPage, total, paged: subsPaginadas } = usePagination(subsDelActual, 25)
const totalPaginas = computed(()=> Math.max(1, Math.ceil(total.value / perPage.value)))
const desde = computed(()=> total.value===0 ? 0 : (page.value-1)*perPage.value + 1)
const hasta = computed(()=> Math.min(page.value*perPage.value, total.value))
const recursosSuscribibles = computed(()=>{ const ya=new Set(subscriptions.value.filter(x=>x.applicationId===selected.value).map(x=>x.resourceId)); return resources.value.filter(r=>!ya.has(r.id)&&!r.parentResourceId).sort((a,b)=>a.name.localeCompare(b.name,'es')) })

// selección
function toggleUno(id){ const s=new Set(sel.value); s.has(id)?s.delete(id):s.add(id); sel.value=s }
const todasSel = computed(()=> subsPaginadas.value.length>0 && subsPaginadas.value.every(su=>sel.value.has(su.id)))
function toggleTodas(){ const s=new Set(sel.value); const on=!todasSel.value; subsPaginadas.value.forEach(su=>on?s.add(su.id):s.delete(su.id)); sel.value=s }
function limpiarSel(){ sel.value=new Set() }
const bulkBusy = ref(false)
async function bajaLote(){ bulkBusy.value=true; try{ for(const id of sel.value) await unsubscribeResource(id); limpiarSel(); await load() }catch(e){ toast.error('Error: '+(e?.message||e)) } finally{ bulkBusy.value=false } }

// drawer suscriptor
const drawer=ref(false); const editing=ref(null); const saving=ref(false)
const drawerW = ref(760)
const form=ref({ name:'',description:'',proposito:'',active:true,consumptionMode:'webhook',webhookUrl:'',personaContacto:'',email:'',telefono:'',githubUrl:'' })
function abrirDrawer(s){ editing.value=s
  form.value = s ? { name:s.name,description:s.description||'',proposito:s.proposito||'',active:s.active!==false,consumptionMode:s.consumptionMode||'webhook',webhookUrl:s.webhookUrl||'',personaContacto:s.personaContacto||'',email:s.email||'',telefono:s.telefono||'',githubUrl:s.githubUrl||'' }
            : { name:'',description:'',proposito:'',active:true,consumptionMode:'webhook',webhookUrl:'',personaContacto:'',email:'',telefono:'',githubUrl:'' }
  drawer.value=true }
function cerrarDrawer(){ drawer.value=false }
async function guardar(){ saving.value=true
  try{
    const f=form.value
    const input={ name:f.name, description:f.description||null, webhookUrl: f.consumptionMode==='graphql'?null:(f.webhookUrl||null), consumptionMode:f.consumptionMode, active:f.active, personaContacto:f.personaContacto||null, email:f.email||null, telefono:f.telefono||null, githubUrl:f.githubUrl||null, proposito:f.proposito||null }
    if(editing.value) await updateSubscriber(editing.value.id,input); else await createSubscriber(input)
    drawer.value=false; await load()
  }catch(e){ toast.error('Error guardando: '+(e?.message||e)) } finally{ saving.value=false } }

async function pedirBorrarSub(s){ const { ok } = await confirm({ title:'Eliminar suscriptor', message:`¿Eliminar "${s.name}"? Se eliminará el suscriptor y sus suscripciones.`, confirmText:'Eliminar', danger:true }); if(!ok) return; try{ await deleteSubscriber(s.id,false); if(selected.value===s.id) selected.value=null; await load() }catch(e){ toast.error('Error: '+(e?.message||e)) } }
function pedirBorrarSubDrawer(){ const s=editing.value; drawer.value=false; pedirBorrarSub(s) }
async function pedirBaja(su){ const r=recDe(su.resourceId); const { ok } = await confirm({ title:'Cancelar suscripción', message:`¿Cancelar la suscripción a "${r?.name||su.resourceId}"?`, confirmText:'Cancelar suscripción', danger:true }); if(!ok) return; try{ await unsubscribeResource(su.id); await load() }catch(e){ toast.error('Error: '+(e?.message||e)) } }

// nueva suscripción
const nuevaSusc=ref({show:false,resourceId:'',autoUpgrade:'patch',busy:false})
function abrirNuevaSusc(){ nuevaSusc.value={show:true,resourceId:'',autoUpgrade:'patch',busy:false} }
async function crearSuscripcion(){ nuevaSusc.value.busy=true
  try{ await subscribeResource(selected.value, nuevaSusc.value.resourceId, null, nuevaSusc.value.autoUpgrade, null); nuevaSusc.value.show=false; await load() }
  catch(e){ toast.error('Error: '+(e?.message||e)) } finally{ nuevaSusc.value.busy=false } }
</script>

<style scoped>
.subs-shell{margin:-1rem;height:100vh;display:flex;flex-direction:column;overflow:hidden;background:#0C0F14}
.subs-tabs{flex-shrink:0;display:flex;gap:6px;align-items:center;padding:10px 16px;border-bottom:1px solid #222C39;background:#0d1218}
.subs-tabs .stab{padding:7px 16px;border-radius:9px;font-size:13px;font-weight:600;color:#8595A6;background:none;border:1px solid transparent;cursor:pointer}
.subs-tabs .stab:hover{color:#E7EEF6}
.subs-tabs .stab.on{color:#3FE0CB;background:#10211e;border-color:#1c5b54}
.pend-wrap{flex:1;min-height:0;overflow:auto;padding:18px 22px;background:#0C0F14;color:#E7EEF6}
.console{
  --ink:#0C0F14;--panel:#12171F;--panel-2:#161D27;--raised:#1B2430;--line:#222C39;--line-soft:#1A222E;
  --txt:#E7EEF6;--muted:#8595A6;--faint:#5A6878;--signal:#3FE0CB;--signal-dim:#1c5b54;--harvest:#F7B85C;--alert:#FF6B6B;--violet:#9C8CFF;
  --mono:'JetBrains Mono',ui-monospace,monospace;--disp:'Space Grotesk',Inter,sans-serif;
  display:grid;grid-template-columns:264px 1fr;flex:1;min-height:0;
  background:
    radial-gradient(1200px 600px at 80% -10%, #16313044, transparent 60%),
    radial-gradient(900px 500px at -10% 110%, #1d243a55, transparent 55%),
    var(--ink);
  color:var(--txt);font-size:14px;border-radius:0;overflow:hidden;
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
.params .ph{display:grid;grid-template-columns:1fr 1.4fr 30px;gap:8px;font-family:var(--mono);font-size:10px;text-transform:uppercase;color:var(--faint);padding:0 2px 6px}
.prow{display:grid;grid-template-columns:1fr 1.4fr 30px;gap:8px;margin-bottom:7px}
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

.bulkbar .danger-btn{background:#ef4444;color:#2a0b0b}
.bulkbar .danger-btn:hover{background:#f87171}
.seg{display:inline-flex;background:#0d131b;border:1px solid var(--line);border-radius:10px;padding:3px;gap:2px}
.seg button{padding:7px 14px;border-radius:7px;font-size:12.5px;font-weight:500;color:var(--muted);background:none;cursor:pointer}
.seg button.on{background:var(--raised);color:var(--txt)}
.seg button.on.sig{background:linear-gradient(180deg,var(--signal),#2bc3b0);color:#042521}

/* paginación */
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
</style>
