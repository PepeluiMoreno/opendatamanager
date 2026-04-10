<template>
  <div class="p-6 space-y-6" style="min-height:100%">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold text-white">Publishers</h1>
        <p class="text-gray-400 text-sm mt-1">Organisations and portals publishing open data</p>
      </div>
      <button @click="openCreate" class="btn btn-primary flex items-center gap-2">
        <span class="text-lg leading-none">+</span> New publisher
      </button>
    </div>

    <!-- Tabla -->
    <div class="card">
      <div v-if="loading" class="p-8 text-center text-gray-400">Loading...</div>
      <div v-else-if="publishers.length === 0" class="p-8 text-center text-gray-400">
        No publishers yet. Create the first one.
      </div>
      <div v-else class="overflow-x-auto max-h-[calc(100vh-260px)] overflow-y-auto">
        <table class="w-full text-sm">
          <thead class="sticky top-0 z-10 bg-gray-800">
            <tr class="text-left text-gray-400 border-b border-gray-700">
              <th class="py-3 px-4 font-medium">Name</th>
              <th class="py-3 px-4 font-medium">Acronym</th>
              <th class="py-3 px-4 font-medium">Scope</th>
              <th class="py-3 px-4 font-medium">Contact</th>
              <th class="py-3 px-4 font-medium">Resources</th>
              <th class="py-3 px-4 font-medium"></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in publishers" :key="p.id"
                class="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
              <td class="py-3 px-4 text-white font-medium">
                {{ p.nombre }}
                <a v-if="p.portalUrl" :href="p.portalUrl" target="_blank"
                   class="ml-1 text-blue-400 hover:text-blue-300 text-xs">↗</a>
              </td>
              <td class="py-3 px-4">
                <span v-if="p.acronimo" class="px-2 py-0.5 bg-gray-700 text-gray-300 rounded text-xs font-mono">
                  {{ p.acronimo }}
                </span>
              </td>
              <td class="py-3 px-4">
                <div class="flex items-center gap-2">
                  <span :class="nivelClass(p.nivel)" class="px-2 py-0.5 rounded text-xs font-semibold whitespace-nowrap">
                    {{ p.nivel }}
                  </span>
                  <span class="text-gray-300 text-xs">{{ ambitoLabel(p) }}</span>
                </div>
              </td>
              <td class="py-3 px-4 text-gray-400 text-xs space-y-0.5">
                <div v-if="p.email">
                  <a :href="`mailto:${p.email}`" class="hover:text-blue-300">{{ p.email }}</a>
                </div>
                <div v-if="p.telefono">{{ p.telefono }}</div>
                <span v-if="!p.email && !p.telefono">—</span>
              </td>
              <td class="py-3 px-4 text-gray-400">{{ resourceCount(p.id) }}</td>
              <td class="py-3 px-4">
                <div class="flex gap-2 justify-end">
                  <button @click="openEdit(p)"
                          class="text-blue-400 hover:text-blue-300 text-xs px-2 py-1 rounded hover:bg-blue-900/30">
                    Edit
                  </button>
                  <button @click="confirmDelete(p)"
                          :disabled="resourceCount(p.id) > 0"
                          :title="resourceCount(p.id) > 0 ? 'Has associated resources' : 'Delete'"
                          class="text-red-400 hover:text-red-300 text-xs px-2 py-1 rounded hover:bg-red-900/30 disabled:opacity-30 disabled:cursor-not-allowed">
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    <!-- Modal -->
    <div v-if="showModal"
         class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 pointer-events-none">
      <div class="bg-gray-800 rounded-xl shadow-2xl w-full max-w-lg border border-gray-700 max-h-[90vh] flex flex-col pointer-events-auto"
           @click.stop>
        <!-- Cabecera -->
        <div class="flex items-center justify-between p-5 border-b border-gray-700 flex-shrink-0">
          <h2 class="text-lg font-bold text-white">{{ editing ? 'Edit' : 'New' }} Publisher</h2>
          <button @click="closeModal" class="text-gray-400 hover:text-white text-xl leading-none">×</button>
        </div>

        <!-- Cuerpo scrollable -->
        <div class="p-5 space-y-4 overflow-y-auto">

          <!-- DIR3 search panel (only on create) -->
          <div v-if="!editing" class="border border-gray-600 rounded-lg overflow-hidden">
            <button
              type="button"
              class="w-full flex items-center justify-between px-4 py-2.5 bg-gray-700/60 hover:bg-gray-700 transition-colors text-sm font-medium text-gray-200"
              @click="dir3Open = !dir3Open"
            >
              <span class="flex items-center gap-2">
                <span class="text-blue-400">🏛</span> Find in DIR3 registry
              </span>
              <span class="text-gray-400 text-xs">{{ dir3Open ? '▲' : '▼' }}</span>
            </button>

            <div v-if="dir3Open" class="p-3 space-y-2 bg-gray-750 border-t border-gray-600">
              <!-- Row 1: Level + Province (province only for Local) -->
              <div class="flex gap-2">
                <select v-model="dir3Nivel" class="input text-xs py-1.5 flex-shrink-0" style="min-width:140px" @change="onDir3NivelChange">
                  <option :value="0">All levels</option>
                  <option :value="1">AGE (Nacional)</option>
                  <option :value="2">Autonómica</option>
                  <option :value="3">Provincial</option>
                  <option :value="4">Local</option>
                </select>
                <select
                  v-if="dir3Nivel === 0 || dir3Nivel === 3 || dir3Nivel === 4"
                  v-model="dir3Prov"
                  class="input text-xs py-1.5 flex-1"
                  @change="searchDir3"
                >
                  <option value="">All provinces</option>
                  <option v-for="p in PROVINCIAS" :key="p.code" :value="p.code">{{ p.name }}</option>
                </select>
              </div>
              <!-- Row 2: Name search -->
              <div class="relative">
                <input
                  v-model="dir3Query"
                  class="input w-full text-xs py-1.5 pr-8"
                  placeholder="Search by name..."
                  @input="onDir3Input"
                />
                <span v-if="dir3Loading" class="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 text-xs animate-spin">⟳</span>
              </div>

              <!-- Results list -->
              <div v-if="dir3Results.length > 0" class="max-h-48 overflow-y-auto rounded border border-gray-600 divide-y divide-gray-700">
                <button
                  v-for="r in dir3Results" :key="r.id"
                  type="button"
                  class="w-full text-left px-3 py-2 hover:bg-blue-900/40 transition-colors group"
                  @click="applyDir3(r)"
                >
                  <div class="flex items-center justify-between gap-2">
                    <span class="text-xs text-white font-medium group-hover:text-blue-200 truncate">{{ r.name }}</span>
                    <span :class="dir3LevelClass(r.adm_level_id)" class="text-xs px-1.5 py-0.5 rounded flex-shrink-0">
                      L{{ r.adm_level_id }}
                    </span>
                  </div>
                  <div class="text-xs text-gray-400 mt-0.5 flex gap-2">
                    <span class="font-mono">{{ r.id }}</span>
                    <span v-if="r.nif_cif" class="text-gray-500">· {{ r.nif_cif }}</span>
                  </div>
                </button>
              </div>
              <p v-else-if="(dir3Query.length >= 2 || dir3Prov || dir3Nivel) && !dir3Loading" class="text-xs text-gray-500 text-center py-2">No results</p>
              <p v-else-if="!dir3Query && !dir3Prov && !dir3Nivel && !dir3Loading" class="text-xs text-gray-500 py-1">
                Select a level or province, or type a name to search.
              </p>
              <p v-if="dir3Truncated" class="text-xs text-yellow-500 text-center">Showing first 60 results — refine your search</p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <!-- Name -->
            <div class="col-span-2">
              <label class="block text-xs font-medium text-gray-400 mb-1">Name *</label>
              <input v-model="form.nombre" class="input w-full text-sm" placeholder="Junta de Andalucía" />
            </div>
            <!-- Acronym + Level -->
            <div>
              <label class="block text-xs font-medium text-gray-400 mb-1">Acronym</label>
              <input v-model="form.acronimo" class="input w-full text-sm font-mono" placeholder="JDA" maxlength="30" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-400 mb-1">Level *</label>
              <select v-model="form.nivel" class="input w-full text-sm" @change="onNivelChange">
                <option value="">Select...</option>
                <option v-for="n in NIVELES" :key="n.value" :value="n.value">{{ n.label }}</option>
              </select>
            </div>
            <!-- Country -->
            <div>
              <label class="block text-xs font-medium text-gray-400 mb-1">Country *</label>
              <input v-model="form.pais" class="input w-full text-sm" placeholder="España" />
            </div>
            <!-- CCAA -->
            <div v-if="showCcaa">
              <label class="block text-xs font-medium text-gray-400 mb-1">Autonomous Community</label>
              <input v-model="form.comunidadAutonoma" class="input w-full text-sm" placeholder="Andalucía" />
            </div>
            <!-- Province -->
            <div v-if="showProvincia">
              <label class="block text-xs font-medium text-gray-400 mb-1">Province</label>
              <input v-model="form.provincia" class="input w-full text-sm" placeholder="Sevilla" />
            </div>
            <!-- Municipality -->
            <div v-if="showMunicipio" class="col-span-2">
              <label class="block text-xs font-medium text-gray-400 mb-1">Municipality</label>
              <input v-model="form.municipio" class="input w-full text-sm" placeholder="Dos Hermanas" />
            </div>
            <!-- Portal URL -->
            <div class="col-span-2">
              <label class="block text-xs font-medium text-gray-400 mb-1">Portal URL</label>
              <div class="flex gap-2">
                <input v-model="form.portalUrl" class="input flex-1 text-sm" placeholder="https://datos.juntadeandalucia.es" />
                <button type="button" @click="checkUrl"
                        :disabled="!form.portalUrl || checkingUrl"
                        class="btn btn-secondary text-xs px-3 whitespace-nowrap">
                  {{ checkingUrl ? '...' : 'Verify' }}
                </button>
              </div>
              <p v-if="urlStatus === 'ok'" class="text-green-400 text-xs mt-1">✓ URL reachable</p>
              <p v-else-if="urlStatus === 'error'" class="text-red-400 text-xs mt-1">✗ URL not reachable ({{ urlError }})</p>
            </div>
            <!-- Contact -->
            <div>
              <label class="block text-xs font-medium text-gray-400 mb-1">Contact email</label>
              <input v-model="form.email" class="input w-full text-sm" type="email" placeholder="datos@organismo.es" />
            </div>
            <div>
              <label class="block text-xs font-medium text-gray-400 mb-1">Phone</label>
              <input v-model="form.telefono" class="input w-full text-sm" placeholder="+34 91 000 00 00" />
            </div>
          </div>
          <p v-if="formError" class="text-red-400 text-xs">{{ formError }}</p>
        </div>

        <!-- Pie -->
        <div class="flex justify-end gap-3 p-5 border-t border-gray-700 flex-shrink-0">
          <button @click="closeModal" class="btn btn-secondary text-sm">Cancel</button>
          <button @click="save" :disabled="saving" class="btn btn-primary text-sm">
            {{ saving ? 'Saving...' : (editing ? 'Save changes' : 'Create publisher') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Delete Modal -->
    <div v-if="showDeleteModal"
         class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
         @click.self="showDeleteModal = false">
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-4">Delete Publisher</h2>
        <p class="mb-6">
          Are you sure you want to delete <strong class="text-purple-300">{{ publisherToDelete?.nombre }}</strong>?
          The publisher will be hidden from the UI.
        </p>
        <label class="flex items-start gap-2 mb-6 cursor-pointer">
          <input type="checkbox" v-model="hardDeleteFlag" class="accent-red-500 mt-0.5" />
          <span>
            <span class="text-sm text-gray-300">Permanently delete</span>
            <span class="block text-xs text-gray-500 mt-0.5">The publisher record will be removed from the database.</span>
          </span>
        </label>
        <div class="flex justify-end gap-2">
          <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="handleDelete" class="btn btn-danger">Delete</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchPublishers, createPublisher, updatePublisher, deletePublisher, fetchResources } from '../api/graphql.js'

const NIVELES = [
  { value: 'ESTATAL',       label: 'National (AGE)' },
  { value: 'AUTONOMICO',    label: 'Regional (CCAA)' },
  { value: 'PROVINCIAL',    label: 'Provincial' },
  { value: 'LOCAL',         label: 'Local' },
  { value: 'EUROPEO',       label: 'European' },
  { value: 'INTERNACIONAL', label: 'International' },
]

const ADM_LEVEL_TO_NIVEL = { 1: 'ESTATAL', 2: 'AUTONOMICO', 3: 'PROVINCIAL', 4: 'LOCAL' }

const publishers       = ref([])
const resources        = ref([])
const loading          = ref(true)
const showModal        = ref(false)
const showDeleteModal  = ref(false)
const publisherToDelete = ref(null)
const hardDeleteFlag   = ref(false)
const editing          = ref(null)
const saving           = ref(false)
const formError        = ref('')
const checkingUrl      = ref(false)
const urlStatus   = ref('')   // '' | 'ok' | 'error'
const urlError    = ref('')

// DIR3 search state
const dir3Open     = ref(false)
const dir3Query    = ref('')
const dir3Nivel    = ref(0)
const dir3Prov     = ref('')
const dir3Results  = ref([])
const dir3Truncated = ref(false)
const dir3Loading  = ref(false)
let   dir3Timer    = null

const PROVINCIAS = [
  { code: '01', name: 'Álava' },
  { code: '02', name: 'Albacete' },
  { code: '03', name: 'Alicante' },
  { code: '04', name: 'Almería' },
  { code: '05', name: 'Ávila' },
  { code: '06', name: 'Badajoz' },
  { code: '07', name: 'Balears (Illes)' },
  { code: '08', name: 'Barcelona' },
  { code: '09', name: 'Burgos' },
  { code: '10', name: 'Cáceres' },
  { code: '11', name: 'Cádiz' },
  { code: '12', name: 'Castellón' },
  { code: '13', name: 'Ciudad Real' },
  { code: '14', name: 'Córdoba' },
  { code: '15', name: 'Coruña (A)' },
  { code: '16', name: 'Cuenca' },
  { code: '17', name: 'Girona' },
  { code: '18', name: 'Granada' },
  { code: '19', name: 'Guadalajara' },
  { code: '20', name: 'Gipuzkoa' },
  { code: '21', name: 'Huelva' },
  { code: '22', name: 'Huesca' },
  { code: '23', name: 'Jaén' },
  { code: '24', name: 'León' },
  { code: '25', name: 'Lleida' },
  { code: '26', name: 'Rioja (La)' },
  { code: '27', name: 'Lugo' },
  { code: '28', name: 'Madrid' },
  { code: '29', name: 'Málaga' },
  { code: '30', name: 'Murcia' },
  { code: '31', name: 'Navarra' },
  { code: '32', name: 'Ourense' },
  { code: '33', name: 'Asturias' },
  { code: '34', name: 'Palencia' },
  { code: '35', name: 'Palmas (Las)' },
  { code: '36', name: 'Pontevedra' },
  { code: '37', name: 'Salamanca' },
  { code: '38', name: 'Santa Cruz de Tenerife' },
  { code: '39', name: 'Cantabria' },
  { code: '40', name: 'Segovia' },
  { code: '41', name: 'Sevilla' },
  { code: '42', name: 'Soria' },
  { code: '43', name: 'Tarragona' },
  { code: '44', name: 'Teruel' },
  { code: '45', name: 'Toledo' },
  { code: '46', name: 'Valencia' },
  { code: '47', name: 'Valladolid' },
  { code: '48', name: 'Bizkaia' },
  { code: '49', name: 'Zamora' },
  { code: '50', name: 'Zaragoza' },
  { code: '51', name: 'Ceuta' },
  { code: '52', name: 'Melilla' },
]

function dir3LevelClass(lvl) {
  return {
    1: 'bg-blue-900/60 text-blue-300',
    2: 'bg-green-900/60 text-green-300',
    3: 'bg-yellow-900/60 text-yellow-300',
    4: 'bg-orange-900/60 text-orange-300',
  }[lvl] || 'bg-gray-700 text-gray-300'
}

async function searchDir3() {
  if (dir3Query.value.length < 2 && dir3Nivel.value === 0 && !dir3Prov.value) {
    dir3Results.value = []
    return
  }
  dir3Loading.value = true
  try {
    const params = new URLSearchParams({ q: dir3Query.value, nivel: dir3Nivel.value, max_hier: 3 })
    if (dir3Prov.value) params.set('prov', dir3Prov.value)
    const res = await fetch(`/api/dir3/search?${params}`)
    const data = await res.json()
    dir3Results.value  = data.results || []
    dir3Truncated.value = data.truncated || false
  } catch {
    dir3Results.value = []
  } finally {
    dir3Loading.value = false
  }
}

function onDir3Input() {
  clearTimeout(dir3Timer)
  dir3Timer = setTimeout(searchDir3, 300)
}

function onDir3NivelChange() {
  // Reset province when switching to a level where province is irrelevant
  if (dir3Nivel.value !== 0 && dir3Nivel.value !== 3 && dir3Nivel.value !== 4) {
    dir3Prov.value = ''
  }
  searchDir3()
}

function applyDir3(r) {
  form.value.nombre = r.name
  form.value.nivel  = ADM_LEVEL_TO_NIVEL[r.adm_level_id] || ''
  // Clear geographic fields so user fills them fresh
  form.value.comunidadAutonoma = ''
  form.value.provincia = ''
  form.value.municipio = ''
  dir3Open.value = false
}

const emptyForm = () => ({
  nombre: '', acronimo: '', nivel: '', pais: 'España',
  comunidadAutonoma: '', provincia: '', municipio: '',
  portalUrl: '', email: '', telefono: '',
})
const form = ref(emptyForm())

const showCcaa      = computed(() => ['AUTONOMICO', 'PROVINCIAL', 'LOCAL'].includes(form.value.nivel))
const showProvincia = computed(() => ['PROVINCIAL', 'LOCAL'].includes(form.value.nivel))
const showMunicipio = computed(() => form.value.nivel === 'LOCAL')

function onNivelChange() {
  if (!showCcaa.value)      { form.value.comunidadAutonoma = ''; form.value.provincia = ''; form.value.municipio = '' }
  else if (!showProvincia.value) { form.value.provincia = ''; form.value.municipio = '' }
  else if (!showMunicipio.value) { form.value.municipio = '' }
}

function nivelClass(nivel) {
  return {
    ESTATAL:       'bg-blue-900/50 text-blue-300 border border-blue-800',
    AUTONOMICO:    'bg-green-900/50 text-green-300 border border-green-800',
    PROVINCIAL:    'bg-yellow-900/50 text-yellow-300 border border-yellow-800',
    LOCAL:         'bg-orange-900/50 text-orange-300 border border-orange-800',
    EUROPEO:       'bg-purple-900/50 text-purple-300 border border-purple-800',
    INTERNACIONAL: 'bg-gray-700 text-gray-300 border border-gray-600',
  }[nivel] || 'bg-gray-700 text-gray-300'
}

function ambitoLabel(p) {
  if (['ESTATAL', 'EUROPEO', 'INTERNACIONAL'].includes(p.nivel)) return p.pais
  if (p.municipio) return `${p.municipio}${p.provincia ? ' (' + p.provincia + ')' : ''}`
  if (p.provincia) return `${p.provincia}${p.comunidadAutonoma ? ' · ' + p.comunidadAutonoma : ''}`
  return p.comunidadAutonoma || p.pais
}

function resourceCount(publisherId) {
  return resources.value.filter(r => r.publisherId === publisherId).length
}

async function checkUrl() {
  if (!form.value.portalUrl) return
  checkingUrl.value = true
  urlStatus.value = ''
  urlError.value = ''
  try {
    const res = await fetch(`/api/check-url?url=${encodeURIComponent(form.value.portalUrl)}`)
    const data = await res.json()
    if (data.ok) {
      urlStatus.value = 'ok'
    } else {
      urlStatus.value = 'error'
      urlError.value = data.status ? `HTTP ${data.status}` : data.error || 'sin respuesta'
    }
  } catch {
    urlStatus.value = 'error'
    urlError.value = 'no se pudo verificar'
  } finally {
    checkingUrl.value = false
  }
}

async function load() {
  loading.value = true
  const [pd, rd] = await Promise.all([fetchPublishers(), fetchResources(false)])
  publishers.value = pd?.publishers || []
  resources.value  = rd?.resources  || []
  loading.value = false
}

function openCreate() {
  editing.value = null
  form.value = emptyForm()
  formError.value = ''
  urlStatus.value = ''
  dir3Open.value = false
  dir3Query.value = ''
  dir3Nivel.value = 0
  dir3Prov.value = ''
  dir3Results.value = []
  dir3Truncated.value = false
  showModal.value = true
}

function openEdit(p) {
  editing.value = p
  form.value = {
    nombre: p.nombre, acronimo: p.acronimo || '', nivel: p.nivel,
    pais: p.pais, comunidadAutonoma: p.comunidadAutonoma || '',
    provincia: p.provincia || '', municipio: p.municipio || '',
    portalUrl: p.portalUrl || '', email: p.email || '', telefono: p.telefono || '',
  }
  formError.value = ''
  urlStatus.value = ''
  showModal.value = true
}

function closeModal() { showModal.value = false }

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

async function save() {
  formError.value = ''
  if (!form.value.nombre.trim() || !form.value.nivel) {
    formError.value = 'Name and Level are required'
    return
  }
  if (form.value.email && !EMAIL_RE.test(form.value.email.trim())) {
    formError.value = 'Invalid email format'
    return
  }
  saving.value = true
  try {
    const input = {
      nombre:            form.value.nombre.trim(),
      acronimo:          form.value.acronimo || null,
      nivel:             form.value.nivel,
      pais:              form.value.pais || 'España',
      comunidadAutonoma: form.value.comunidadAutonoma || null,
      provincia:         form.value.provincia || null,
      municipio:         form.value.municipio || null,
      portalUrl:         form.value.portalUrl || null,
      email:             form.value.email || null,
      telefono:          form.value.telefono || null,
    }
    if (editing.value) {
      await updatePublisher(editing.value.id, input)
    } else {
      await createPublisher(input)
    }
    closeModal()
    await load()
  } catch (e) {
    formError.value = e.message || 'Error saving publisher'
  } finally {
    saving.value = false
  }
}

function confirmDelete(p) {
  publisherToDelete.value = p
  hardDeleteFlag.value = false
  showDeleteModal.value = true
}

async function handleDelete() {
  try {
    await deletePublisher(publisherToDelete.value.id, hardDeleteFlag.value)
    showDeleteModal.value = false
    publisherToDelete.value = null
    await load()
  } catch (e) {
    alert(e.message || 'Error deleting publisher')
  }
}

onMounted(load)
</script>
