<template>
  <div class="console" :style="{ gridTemplateColumns: railW + 'px 6px 1fr' }">
    <!-- ============ SUBSCRIBERS RAIL (maestro) ============ -->
    <aside class="rail">
      <div class="brand">
        <div class="logo"></div>
        <div><h1>Suscriptores</h1><div class="sub">Vista nueva · beta</div></div>
      </div>

      <div class="roster-h">
        <span>Suscriptores</span>
        <button @click="abrirDrawer(null)" title="Nuevo suscriptor">+</button>
      </div>

      <div class="roster">
        <div v-for="s in subsFiltrados" :key="s.id"
             :class="['col', { active: selected === s.id }]"
             @click="selected = s.id">
          <span class="gi">{{ modeIcon(s.consumptionMode) }}</span>
          <div class="cmeta">
            <span class="nm">{{ s.name }}</span>
            <span class="attrs">
              <span class="at">{{ modeLabel(s.consumptionMode) }}</span>
              <span class="at">· {{ nSubs(s.id) }} susc.</span>
              <span class="at" :class="s.active ? 'ok' : 'off'">· {{ s.active ? 'activo' : 'inactivo' }}</span>
            </span>
          </div>
          <span class="edit" @click.stop>
            <button title="Editar" @click="abrirDrawer(s)">✎</button>
            <button class="del" title="Eliminar" @click="pedirBorrar(s)">🗑</button>
          </span>
        </div>
      </div>

      <div class="col-filter">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
        <input v-model="subFilter" placeholder="Filtrar suscriptores…" />
        <button v-if="subFilter" class="clr" @click="subFilter=''">✕</button>
      </div>

      <div class="rail-foot"><span class="pulse"></span> {{ nActivos }} activos · {{ subscribers.length }} totales</div>
    </aside>

    <div class="divider" @mousedown="startDrag"><span></span></div>

    <!-- ============ MAIN: suscripciones del suscriptor (detalle) ============ -->
    <main class="main">
      <div class="topbar">
        <div class="crumb">
          <div class="big">{{ actual?.name || 'Suscriptor' }}</div>
          <div class="meta">{{ metaActual }}</div>
        </div>
        <div class="spacer"></div>
        <button v-if="actual" class="btn primary" @click="abrirAlta">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><path d="M12 5v14M5 12h14"/></svg>
          Nueva suscripción
        </button>
      </div>

      <div class="filters">
        <div class="search">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M21 21l-4-4"/></svg>
          <input v-model="q" placeholder="Buscar recurso…" />
        </div>
        <div class="chip pub-chip">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 21h18M5 21V7l8-4v18M19 21V11l-6-4"/></svg>
          <select v-model="fPublisher"><option value="">Publisher: todos</option><option v-for="p in publishersUsados" :key="p.id" :value="p.id">{{ p.acronimo || p.nombre }}</option></select>
        </div>
      </div>

      <div class="listwrap">
        <div v-if="loading" class="empty">Cargando…</div>
        <div v-else-if="!actual" class="empty">Elige un suscriptor a la izquierda.</div>
        <template v-else>
          <div class="lhead">
            <div>Recurso</div>
            <div class="col-pub">Publisher</div>
            <div>Versión</div>
            <div>Auto-upgrade</div>
            <div class="col-acts" style="text-align:right">Acciones</div>
          </div>
          <div v-if="subsActual.length === 0" class="empty">
            Este suscriptor no tiene suscripciones.
            <button class="link" @click="abrirAlta">Añadir la primera</button>
          </div>
          <div v-for="sub in subsActual" :key="sub.id" class="row">
            <div class="rname"><span class="ttl">{{ resName(sub.resourceId) }}</span></div>
            <div class="col-pub pub" :title="resPub(sub.resourceId)?.nombre || ''">{{ resPub(sub.resourceId)?.acronimo || resPub(sub.resourceId)?.nombre || '—' }}</div>
            <div class="ver">
              <span class="cur">{{ sub.currentVersion || '—' }}</span>
              <small v-if="sub.pinnedVersion">fijada {{ sub.pinnedVersion }}</small>
            </div>
            <div><span class="auto">{{ sub.autoUpgrade || '—' }}</span></div>
            <div class="col-acts racts">
              <button class="act-icon danger" title="Cancelar suscripción" @click="pedirCancelar(sub)">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>
              </button>
            </div>
          </div>
        </template>
      </div>
    </main>

    <!-- ============ DRAWER: editar/crear suscriptor ============ -->
    <div :class="['scrim',{show:drawer}]" @click="cerrarDrawer"></div>
    <aside :class="['drawer',{show:drawer}]">
      <div class="dh">
        <div class="di">{{ editing ? '✎' : '＋' }}</div>
        <div><h2>{{ editing ? 'Editar suscriptor' : 'Nuevo suscriptor' }}</h2><p>Suscriptor de ODM</p></div>
        <button class="x" @click="cerrarDrawer">✕</button>
      </div>
      <div class="dbody">
        <div class="sect">
          <div class="sh"><span class="nidx">01</span><h3>Identidad</h3></div>
          <div class="sbody">
            <div class="field"><label>Nombre <span class="req">*</span></label><input class="inp" v-model="form.name" placeholder="p. ej. ckan-jerez"></div>
            <div class="field"><label>Descripción</label><textarea class="inp" v-model="form.description" placeholder="Qué hace este consumidor"></textarea></div>
            <div class="field"><label>Propósito</label><input class="inp" v-model="form.proposito" placeholder="Para qué consume los datos"></div>
            <div class="tog"><div><div class="t">Activo</div><div class="s">Recibe notificaciones y puede consultar</div></div>
              <div :class="['sw',{on:form.active}]" @click="form.active=!form.active"></div></div>
          </div>
        </div>
        <div class="sect">
          <div class="sh"><span class="nidx">02</span><h3>Entrega</h3></div>
          <div class="sbody">
            <div class="field"><label>Modo de consumo</label>
              <div class="seg">
                <button :class="{on:form.consumptionMode==='webhook'}" @click="form.consumptionMode='webhook'">Webhook</button>
                <button :class="{on:form.consumptionMode==='graphql'}" @click="form.consumptionMode='graphql'">GraphQL</button>
                <button :class="{on:form.consumptionMode==='both'}" @click="form.consumptionMode='both'">Ambos</button>
              </div>
            </div>
            <div v-if="form.consumptionMode!=='graphql'" class="field"><label>URL del webhook</label>
              <input class="inp mono" v-model="form.webhookUrl" placeholder="https://tu-app/webhooks/odmgr"></div>
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
        <button v-if="editing" class="del" @click="pedirBorrar(editing)">Eliminar suscriptor</button>
        <div class="grow"></div>
        <button class="ghost" @click="cerrarDrawer">Cancelar</button>
        <button class="save" :disabled="!form.name || saving" @click="guardar">{{ saving?'Guardando…':'Guardar' }}</button>
      </div>
    </aside>

    <!-- alta de suscripción -->
    <div v-if="alta.show" class="scrim show" @click.self="alta.show=false">
      <div class="confirm">
        <h2>Nueva suscripción</h2>
        <div class="field"><label>Recurso</label>
          <select class="inp" v-model="alta.resourceId"><option value="">Elige recurso…</option><option v-for="r in resources" :key="r.id" :value="r.id">{{ r.name }}{{ r.publisherObj?.acronimo ? ' — '+r.publisherObj.acronimo : '' }}</option></select></div>
        <div class="field"><label>Auto-upgrade</label>
          <select class="inp" v-model="alta.autoUpgrade"><option value="patch">patch</option><option value="minor">minor</option><option value="major">major</option><option value="none">none</option></select></div>
        <div class="cf"><button class="ghost" @click="alta.show=false">Cancelar</button>
          <button class="save" :disabled="!alta.resourceId" @click="confirmarAlta">Suscribir</button></div>
      </div>
    </div>

    <!-- confirmaciones -->
    <div v-if="confirm.show" class="scrim show" @click.self="confirm.show=false">
      <div class="confirm">
        <h2>{{ confirm.title }}</h2><p>{{ confirm.msg }}</p>
        <div class="cf"><button class="ghost" @click="confirm.show=false">Cancelar</button>
          <button class="danger" @click="confirm.onOk">Eliminar</button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  fetchSubscribers, createSubscriber, updateSubscriber, deleteSubscriber, activateSubscriber,
  fetchSubscriptions, subscribeResource, unsubscribeResource, fetchResources,
} from '../api/graphql'

const loading = ref(true)
const subscribers = ref([])
const subscriptions = ref([])
const resources = ref([])
const selected = ref(null)

const railW = ref(300); let dragging=false
function startDrag(e){ dragging=true; e.preventDefault()
  const move=ev=>{ if(dragging) railW.value=Math.min(440,Math.max(220,ev.clientX)) }
  const up=()=>{ dragging=false; window.removeEventListener('mousemove',move); window.removeEventListener('mouseup',up) }
  window.addEventListener('mousemove',move); window.addEventListener('mouseup',up) }

const subFilter = ref(''); const q = ref(''); const fPublisher = ref('')

async function load(){
  loading.value=true
  try{
    const [sd,subd,rd]=await Promise.all([fetchSubscribers(),fetchSubscriptions(),fetchResources(false)])
    subscribers.value=(sd?.subscribers||[]).slice().sort((a,b)=>a.name.localeCompare(b.name,'es'))
    subscriptions.value=subd?.resourceSubscriptions||[]
    resources.value=rd?.resources||[]
    if(!subscribers.value.find(s=>s.id===selected.value)) selected.value=subscribers.value[0]?.id||null
  } finally { loading.value=false }
}
onMounted(load)

function modeIcon(m){ return m==='graphql'?'⚡':m==='both'?'🔗':'🪝' }
function modeLabel(m){ return m==='both'?'webhook+graphql':m||'webhook' }
function nSubs(id){ return subscriptions.value.filter(x=>x.applicationId===id).length }
const nActivos = computed(()=>subscribers.value.filter(s=>s.active).length)
const subsFiltrados = computed(()=>{ const f=subFilter.value.trim().toLowerCase(); return f?subscribers.value.filter(s=>s.name.toLowerCase().includes(f)):subscribers.value })
const actual = computed(()=>subscribers.value.find(s=>s.id===selected.value)||null)
const metaActual = computed(()=>{ if(!actual.value)return''; return `${modeLabel(actual.value.consumptionMode)} · ${nSubs(actual.value.id)} suscripciones · ${actual.value.active?'activo':'inactivo'}` })

const resById = computed(()=>Object.fromEntries(resources.value.map(r=>[r.id,r])))
function resName(id){ return resById.value[id]?.name || '(recurso eliminado)' }
function resPub(id){ return resById.value[id]?.publisherObj || null }
const publishersUsados = computed(()=>{ const map=new Map(); for(const sub of subscriptions.value.filter(x=>x.applicationId===selected.value)){ const p=resPub(sub.resourceId); if(p?.id&&!map.has(p.id))map.set(p.id,p) } return Array.from(map.values()) })
const subsActual = computed(()=> subscriptions.value.filter(x=>x.applicationId===selected.value).filter(sub=>{
  if(q.value && !resName(sub.resourceId).toLowerCase().includes(q.value.toLowerCase())) return false
  if(fPublisher.value && resPub(sub.resourceId)?.id!==fPublisher.value) return false
  return true
}))

// drawer suscriptor
const drawer=ref(false); const editing=ref(null); const saving=ref(false)
const form=ref({ name:'',description:'',proposito:'',active:true,consumptionMode:'webhook',webhookUrl:'',personaContacto:'',email:'',telefono:'',githubUrl:'' })
function abrirDrawer(s){ editing.value=s
  form.value = s ? { name:s.name,description:s.description||'',proposito:s.proposito||'',active:s.active,consumptionMode:s.consumptionMode||'webhook',webhookUrl:s.webhookUrl||'',personaContacto:s.personaContacto||'',email:s.email||'',telefono:s.telefono||'',githubUrl:s.githubUrl||'' }
              : { name:'',description:'',proposito:'',active:true,consumptionMode:'webhook',webhookUrl:'',personaContacto:'',email:'',telefono:'',githubUrl:'' }
  drawer.value=true }
function cerrarDrawer(){ drawer.value=false }
async function guardar(){ saving.value=true
  try{ const f=form.value; const input={ name:f.name,description:f.description||null,proposito:f.proposito||null,active:f.active,consumptionMode:f.consumptionMode,webhookUrl:f.consumptionMode==='graphql'?null:(f.webhookUrl||null),personaContacto:f.personaContacto||null,email:f.email||null,telefono:f.telefono||null,githubUrl:f.githubUrl||null }
    if(editing.value){ await updateSubscriber(editing.value.id,input) } else { const r=await createSubscriber(input); const g=r?.createSubscriber; drawer.value=false; await load(); if(g) selected.value=g.id; saving.value=false; return }
    drawer.value=false; await load()
  }catch(e){ window.alert('Error: '+(e?.message||e)) } finally{ saving.value=false } }

// alta de suscripción
const alta=ref({show:false,resourceId:'',autoUpgrade:'patch'})
function abrirAlta(){ alta.value={show:true,resourceId:'',autoUpgrade:'patch'} }
async function confirmarAlta(){ try{ await subscribeResource(selected.value,alta.value.resourceId,null,alta.value.autoUpgrade,null); alta.value.show=false; await load() }catch(e){ window.alert('Error: '+(e?.message||e)) } }

// confirmaciones
const confirm=ref({show:false,title:'',msg:'',onOk:()=>{}})
function pedirBorrar(s){ confirm.value={show:true,title:'Eliminar suscriptor',msg:`¿Eliminar "${s.name}" y sus suscripciones?`,onOk:async()=>{ try{ await deleteSubscriber(s.id,false); confirm.value.show=false; drawer.value=false; if(selected.value===s.id) selected.value=null; await load() }catch(e){ window.alert('Error: '+(e?.message||e)) } }} }
function pedirCancelar(sub){ confirm.value={show:true,title:'Cancelar suscripción',msg:`¿Cancelar la suscripción a "${resName(sub.resourceId)}"?`,onOk:async()=>{ try{ await unsubscribeResource(sub.id); confirm.value.show=false; await load() }catch(e){ window.alert('Error: '+(e?.message||e)) } }} }
</script>

<style scoped>
.console{
  --ink:#0C0F14;--panel:#12171F;--panel-2:#161D27;--raised:#1B2430;--line:#222C39;--line-soft:#1A222E;
  --txt:#E7EEF6;--muted:#8595A6;--faint:#5A6878;--signal:#3FE0CB;--signal-dim:#1c5b54;--harvest:#F7B85C;--alert:#FF6B6B;--violet:#9C8CFF;
  --mono:'JetBrains Mono',ui-monospace,monospace;--disp:'Space Grotesk',Inter,sans-serif;
  display:grid;height:100vh;background:radial-gradient(1200px 600px at 80% -10%,#16313044,transparent 60%),radial-gradient(900px 500px at -10% 110%,#1d243a55,transparent 55%),var(--ink);color:var(--txt);font-size:14px;margin:-1rem;overflow:hidden}
.console *{box-sizing:border-box}
.rail{background:linear-gradient(180deg,#10151d,#0d1218);border-right:1px solid var(--line);display:flex;flex-direction:column;min-height:0}
.brand{display:flex;align-items:center;gap:10px;padding:18px 18px 14px}
.brand .logo{width:30px;height:30px;border-radius:9px;background:conic-gradient(from 200deg,var(--signal),var(--violet),var(--harvest),var(--signal));position:relative}
.brand .logo::after{content:"";position:absolute;inset:6px;border-radius:5px;background:var(--ink)}
.brand h1{font-family:var(--disp);font-size:15px;font-weight:600;margin:0}
.brand .sub{font-size:10px;color:var(--faint);letter-spacing:.14em;text-transform:uppercase;font-family:var(--mono)}
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
.col .cmeta{flex:1;min-width:0;display:flex;flex-direction:column;gap:2px}
.col .cmeta .nm{font-size:13px;font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.col .attrs{display:flex;gap:5px;font-family:var(--mono);font-size:10px;color:var(--faint);flex-wrap:wrap}
.col .attrs .ok{color:#5fb9af}.col .attrs .off{color:var(--faint)}
.col .edit{opacity:0;display:flex;gap:2px;position:absolute;right:8px;background:linear-gradient(90deg,transparent,#13202a 30%);padding-left:18px}
.col:hover .edit{opacity:1}
.col .edit button{width:22px;height:22px;border-radius:6px;color:var(--faint);display:grid;place-items:center;background:none;border:none;cursor:pointer}
.col .edit button:hover{color:var(--signal);background:#10211d}
.col .edit button.del:hover{color:var(--alert)}
.col-filter{display:flex;align-items:center;gap:8px;margin:6px 12px 4px;padding:7px 10px;background:#0e151d;border:1px solid var(--line);border-radius:9px}
.col-filter svg{width:13px;height:13px;color:var(--faint);flex-shrink:0}
.col-filter input{flex:1;min-width:0;background:transparent;border:none;color:var(--txt);font-size:12px;outline:none}
.col-filter .clr{color:var(--faint);background:none;border:none;cursor:pointer}
.rail-foot{padding:12px 16px;border-top:1px solid var(--line);font-size:11px;color:var(--faint);display:flex;align-items:center;gap:8px;font-family:var(--mono)}
.pulse{width:7px;height:7px;border-radius:50%;background:var(--signal);box-shadow:0 0 8px var(--signal);animation:pp 2s infinite}
@keyframes pp{0%,100%{opacity:1}50%{opacity:.35}}
.divider{cursor:col-resize;display:flex;align-items:center;justify-content:center}
.divider span{width:2px;height:46px;border-radius:2px;background:var(--line)}
.divider:hover span{background:var(--signal);box-shadow:0 0 8px var(--signal)}
.main{display:flex;flex-direction:column;min-width:0;min-height:0}
.topbar{display:flex;align-items:center;gap:14px;padding:16px 22px 12px}
.crumb{min-width:0}.crumb .big{font-family:var(--disp);font-size:21px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.crumb .meta{font-family:var(--mono);font-size:11px;color:var(--faint)}
.spacer{flex:1}
.btn{display:inline-flex;align-items:center;gap:7px;padding:9px 14px;border-radius:10px;font-weight:600;font-size:13px;border:1px solid var(--line);color:var(--muted);background:none;cursor:pointer}
.btn:hover{border-color:#34424f;color:var(--txt)}
.btn.primary{background:linear-gradient(180deg,var(--signal),#2bc3b0);color:#042521;border:none}
.btn svg{width:15px;height:15px}
.filters{display:flex;align-items:center;gap:8px;padding:4px 22px 10px;flex-wrap:wrap}
.search{flex:0 1 230px;min-width:140px;position:relative}
.search input{width:100%;background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:9px 12px 9px 34px;color:var(--txt);font-size:13px;outline:none}
.search svg{position:absolute;left:11px;top:50%;transform:translateY(-50%);width:15px;height:15px;color:var(--faint)}
.chip{display:inline-flex;align-items:center;gap:6px;padding:7px 11px;border-radius:9px;border:1px solid var(--line);background:var(--panel);font-size:12.5px;color:var(--muted)}
.chip select{background:transparent;border:none;color:var(--txt);outline:none;font-size:12.5px}
.chip svg{width:13px;height:13px;color:var(--faint)}
.pub-chip{flex:1 1 auto;min-width:170px}.pub-chip select{flex:1;min-width:0}
.listwrap{flex:1;overflow-y:auto;padding:2px 16px 60px}
.empty{text-align:center;color:var(--faint);padding:40px;font-size:13px}
.link{color:var(--signal);background:none;border:none;cursor:pointer;margin-left:6px}
.lhead{display:grid;grid-template-columns:minmax(0,1fr) 150px 130px 130px 78px;gap:8px;padding:9px 14px 8px;font-family:var(--disp);font-size:11px;font-weight:600;color:var(--muted);position:sticky;top:0;background:var(--ink);z-index:3;border-bottom:1px solid var(--line)}
.row{display:grid;grid-template-columns:minmax(0,1fr) 150px 130px 130px 78px;gap:8px;align-items:center;padding:11px 14px;border-radius:12px;margin:3px 0;background:var(--panel);border:1px solid var(--line-soft)}
.row:hover{border-color:#2c3a48;background:var(--panel-2)}
.rname{min-width:0}.rname .ttl{font-weight:500;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block}
.pub{font-size:12px;color:var(--muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ver{display:flex;flex-direction:column}.ver .cur{font-family:var(--mono);font-size:12px;color:var(--txt)}.ver small{font-family:var(--mono);font-size:10px;color:var(--faint)}
.auto{font-family:var(--mono);font-size:11px;color:var(--harvest);border:1px solid #5a4423;background:#1d160a;padding:2px 8px;border-radius:6px}
.racts{display:flex;gap:4px;justify-content:flex-end}
@media(max-width:1100px){.lhead,.row{grid-template-columns:1fr 110px 78px}.col-pub,.ver,.auto{display:none}}
.scrim{position:fixed;inset:0;background:#04060a99;backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:.25s;z-index:50}
.scrim.show{opacity:1;pointer-events:auto}
.drawer{position:fixed;top:0;right:0;height:100vh;width:min(540px,94vw);background:linear-gradient(180deg,#131922,#0f141b);border-left:1px solid var(--line);transform:translateX(102%);transition:.3s cubic-bezier(.3,.8,.3,1);z-index:60;display:flex;flex-direction:column}
.drawer.show{transform:translateX(0)}
.dh{display:flex;align-items:flex-start;gap:12px;padding:20px 22px 16px;border-bottom:1px solid var(--line)}
.dh .di{width:40px;height:40px;border-radius:11px;background:#10211d;border:1px solid var(--signal-dim);display:grid;place-items:center;font-size:19px}
.dh h2{font-family:var(--disp);font-size:18px;margin:0 0 2px;font-weight:600}.dh p{margin:0;font-size:12px;color:var(--faint);font-family:var(--mono)}
.dh .x{margin-left:auto;width:32px;height:32px;border-radius:9px;color:var(--muted);font-size:18px;display:grid;place-items:center;border:1px solid var(--line);background:none;cursor:pointer}
.dbody{flex:1;overflow-y:auto;padding:6px 22px 30px}
.sect{border-top:1px solid var(--line-soft);padding:18px 0}.sect:first-child{border-top:none}
.sect>.sh{display:flex;align-items:center;gap:9px;margin-bottom:14px}
.sect>.sh .nidx{font-family:var(--mono);font-size:10px;color:var(--signal);border:1px solid var(--signal-dim);border-radius:5px;padding:2px 6px;background:#0f201d}
.sect>.sh h3{font-family:var(--disp);font-size:13px;font-weight:600;margin:0}
.field{margin-bottom:14px}.field>label{display:block;font-size:12px;font-weight:500;color:var(--muted);margin-bottom:6px}.field>label .req{color:var(--signal)}
.inp{width:100%;background:#0d131b;border:1px solid var(--line);border-radius:10px;padding:10px 12px;color:var(--txt);font-size:13.5px;outline:none}
.inp:focus{border-color:var(--signal-dim)}textarea.inp{resize:vertical;min-height:60px}.inp.mono{font-family:var(--mono);font-size:12.5px}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.seg{display:inline-flex;background:#0d131b;border:1px solid var(--line);border-radius:10px;padding:3px;gap:2px}
.seg button{padding:7px 14px;border-radius:7px;font-size:12.5px;color:var(--muted);background:none;border:none;cursor:pointer}
.seg button.on{background:linear-gradient(180deg,var(--signal),#2bc3b0);color:#042521}
.tog{display:flex;align-items:center;justify-content:space-between;padding:11px 13px;background:#0d131b;border:1px solid var(--line);border-radius:10px}
.tog .t{font-size:13px;font-weight:500}.tog .s{font-size:11px;color:var(--faint);margin-top:2px}
.sw{width:40px;height:23px;border-radius:20px;background:#26313d;position:relative;transition:.2s;flex-shrink:0;cursor:pointer}
.sw::after{content:"";position:absolute;top:2.5px;left:2.5px;width:18px;height:18px;border-radius:50%;background:#cdd7e1;transition:.2s}
.sw.on{background:var(--signal-dim)}.sw.on::after{left:19px;background:var(--signal)}
.dfoot{display:flex;align-items:center;gap:10px;padding:14px 22px;border-top:1px solid var(--line);background:#0f141b}
.dfoot .del{color:var(--alert);font-size:12.5px;font-weight:500;background:none;border:none;cursor:pointer}.dfoot .grow{flex:1}
.dfoot .ghost{padding:10px 16px;border-radius:10px;border:1px solid var(--line);color:var(--muted);font-size:13px;background:none;cursor:pointer}
.dfoot .save{padding:10px 20px;border-radius:10px;background:linear-gradient(180deg,var(--signal),#2bc3b0);color:#042521;font-weight:700;font-size:13px;border:none;cursor:pointer}
.dfoot .save:disabled{opacity:.45;cursor:not-allowed}
.confirm{position:fixed;left:50%;top:50%;transform:translate(-50%,-50%);background:#131922;border:1px solid var(--line);border-radius:14px;padding:22px;width:min(440px,92vw);z-index:70}
.confirm h2{font-family:var(--disp);font-size:18px;margin:0 0 10px}.confirm p{color:var(--muted);font-size:13px;margin:0 0 16px;line-height:1.5}
.cf{display:flex;justify-content:flex-end;gap:10px;margin-top:6px}
.cf .ghost{padding:9px 16px;border-radius:10px;border:1px solid var(--line);color:var(--muted);background:none;cursor:pointer}
.cf .danger{padding:9px 18px;border-radius:10px;background:var(--alert);color:#2a0b0b;font-weight:700;border:none;cursor:pointer}
.cf .save{padding:9px 18px;border-radius:10px;background:var(--signal);color:#042521;font-weight:700;border:none;cursor:pointer}
.cf .save:disabled{opacity:.45;cursor:not-allowed}
</style>
