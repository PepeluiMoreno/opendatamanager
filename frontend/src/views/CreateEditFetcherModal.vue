<template>
  <div class="w-full">
      <div class="bg-gray-800 rounded-lg p-6 w-full">
      <div class="flex items-start justify-between mb-6">
        <div class="flex items-center gap-3">
          <button @click="$emit('close')" class="btn btn-secondary text-sm py-1 px-3" title="Volver al listado">← Fetchers</button>
          <h2 class="text-2xl font-bold">
            {{ Fetcher ? 'Edit Fetcher' : 'New Fetcher' }}
            <span v-if="Fetcher" class="text-purple-300 font-mono text-lg ml-1">{{ Fetcher.name || Fetcher.code }}</span>
          </h2>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-white text-2xl">×</button>
      </div>

      <form @submit.prevent="submitForm" class="space-y-6">
        <!-- Basic Info -->
        <div class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-2">Fetcher Name *</label>
            <input
              v-model="formData.name"
              type="text"
              required
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
              placeholder="e.g., API REST, HTML Forms"
            />
            <p class="text-xs text-gray-400 mt-1">Unique identifier for this Fetcher</p>
          </div>

          <div>
            <label class="block text-sm font-medium mb-2">Description</label>
            <textarea
              v-model="formData.description"
              v-autogrow
              rows="2"
              class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 resize-none"
              placeholder="Describe what this Fetcher does..."
            ></textarea>
          </div>

          <!-- Variants: implementaciones concretas de esta tecnología -->
          <div v-if="Fetcher">
            <label class="block text-sm font-medium mb-1">Variants</label>
            <p class="text-xs text-gray-400 mb-2">
              Implementaciones concretas de esta tecnología. Cada variante fija valores para los
              parámetros de abajo; los recursos la eligen y heredan esos valores.
            </p>
            <div class="flex flex-wrap items-center gap-2">
              <button type="button" @click="varianteActiva && cerrarVariante(varianteActiva)"
                      class="px-2.5 py-1 rounded-full text-xs border transition-colors"
                      :class="!varianteActiva
                        ? 'bg-blue-900 text-blue-200 border-blue-600'
                        : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'">
                Genérico
              </button>
              <button v-for="v in variantes" :key="v.id || v._tmp" type="button"
                      @click="seleccionarVariante(v)"
                      class="px-2.5 py-1 rounded-full text-xs border transition-colors"
                      :class="varianteActiva === v
                        ? 'bg-purple-900 text-purple-200 border-purple-600'
                        : 'bg-gray-700 text-gray-300 border-gray-600 hover:bg-gray-600'">
                {{ v.code || '(sin nombre)' }}
              </button>
              <button type="button" @click="nuevaVariante"
                      class="px-2.5 py-1 rounded-full text-xs border border-dashed border-gray-500 text-gray-400 hover:bg-gray-700">
                + New variant
              </button>
            </div>
          </div>
        </div>

        <!-- Parameters List with Tabs -->
        <div class="border-t border-gray-600 pt-6">
            <div class="flex items-center justify-between mb-4">
              <h3 class="text-xl font-semibold cursor-pointer select-none flex items-center gap-2"
                  @click="seccionBasicaAbierta = !seccionBasicaAbierta">
                <span class="text-gray-500 text-base">{{ seccionBasicaAbierta ? '▾' : '▸' }}</span>
                <template v-if="varianteActiva">
                  <span class="text-purple-300 font-mono">{{ varianteActiva.code || 'Nueva variante' }}</span> Parameters Definition
                </template>
                <template v-else>Parameters Definition</template>
                <span v-if="!seccionBasicaAbierta" class="text-xs text-gray-500 font-normal">({{ totalAll }} parámetros)</span>
              </h3>
              <div class="flex gap-2" v-show="seccionBasicaAbierta">
                <template v-if="varianteActiva">
                  <input v-if="!varianteActiva.id || varianteActiva._renombrando" v-model="varianteActiva.code"
                         class="input text-sm w-44" placeholder="Nombre de la variante" />
                  <button type="button" @click="cerrarVariante(varianteActiva)"
                          class="btn btn-secondary text-sm py-1 px-2"
                          title="Volver a Genérico descartando los cambios no guardados">Cerrar</button>
                  <button type="button" v-if="varianteActiva.id" @click="retirarVariante(varianteActiva)"
                          class="btn btn-secondary text-sm py-1 px-2 text-red-400 border-red-800">Retirar</button>
                  <button type="button" :disabled="!varianteActiva.code || varianteActiva._saving"
                          @click="guardarVariante(varianteActiva)"
                          class="btn btn-primary text-sm py-1 px-2 disabled:opacity-40">
                    {{ varianteActiva._saving ? 'Guardando…' : (varianteActiva.id ? 'Guardar variante' : 'Crear variante') }}
                  </button>
                </template>
                <button
                  v-if="!varianteActiva"
                  type="button"
                  @click="addParameter"
                  class="btn btn-secondary text-sm py-1 px-2"
                >
                  + Add Parameter
                </button>
              </div>
            </div>
              
          <div v-show="seccionBasicaAbierta">
          <div v-if="parameters.length === 0" class="text-center py-8 text-gray-400">
            No parameters configured yet. Add at least one parameter for this Fetcher.
          </div>

          <div v-else>
            <!-- Tabs -->
            <div class="flex space-x-1 mb-4 border-b border-gray-600">
              <button
                type="button"
                @click="activeTab = 'required'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'required'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Required ({{ totalRequired }})
              </button>
              <button
                type="button"
                @click="activeTab = 'optional'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'optional'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Optional ({{ totalOptional }})
              </button>
              <button
                type="button"
                @click="activeTab = 'all'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeTab === 'all'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                All ({{ totalAll }})
              </button>
            </div>

            <p v-if="extrasVariante.length" class="text-[11px] text-purple-300/80 mb-2">
              Los contadores incluyen {{ extrasVariante.length }} parámetro(s) específico(s) de la variante
              «{{ varianteActiva.code }}» fuera del catálogo básico
              ({{ extrasVariante.map(e => e.key).join(', ') }}); aparecen al final, en la sección «Fuera del catálogo».
            </p>

            <!-- Parameters Grid -->
            <div class="space-y-2">
              <!-- Header — col layout: 2 name | 2 type | 1 req | 6 default/enum | 1 del -->
              <div class="grid grid-cols-12 gap-2 text-xs font-medium text-gray-400 px-2">
                <div class="col-span-2">Nombre</div>
                <div class="col-span-2">Tipo</div>
                <div class="col-span-1 text-center">Req</div>
                <div :class="varianteActiva ? 'col-span-3' : 'col-span-6'">Valor por defecto / Opciones</div>
                <div v-if="varianteActiva" class="col-span-4 text-purple-300">Valor en «{{ varianteActiva.code || '…' }}»</div>
                <div class="col-span-1"></div>
              </div>

              <!-- Rows: agrupadas por eje (peticion → paginacion → extraccion → http) -->
              <template v-for="g in filteredParamGroups" :key="g.name">
                <div class="flex items-center gap-2 mt-3 mb-1 px-1 cursor-pointer select-none"
                     @click="toggleGrupo(g.name)" :title="grupoAbierto(g.name) ? 'Colapsar' : 'Expandir'">
                  <span class="text-gray-500 text-xs">{{ grupoAbierto(g.name) ? '▾' : '▸' }}</span>
                  <span class="text-[11px] uppercase tracking-wide font-semibold text-blue-300">{{ tituloGrupo(g.name) }}</span>
                  <span class="text-[10px] text-gray-500">({{ g.params.length }})</span>
                  <div class="flex-1 border-t border-gray-700"></div>
                </div>
              <template v-for="(item, ii) in g.items" :key="g.name + '-' + ii">
              <!-- Etiqueta de rama: el valor del controlador que abre estos parámetros -->
              <div v-if="item.tipo === 'rama'" v-show="grupoAbierto(g.name)"
                   class="flex items-center gap-1.5 pt-1.5 pb-0.5"
                   :class="item.nivel > 0 ? 'pl-7' : ''">
                <span class="text-gray-600">└</span>
                <span class="text-[10px] uppercase tracking-wide text-amber-300/90">
                  <template v-if="item.externa">{{ item.controlador }} = </template>{{ item.etiqueta }}
                </span>
                <div class="flex-1 border-t border-dashed border-gray-700/70"></div>
              </div>
              <div
                v-else
                v-show="grupoAbierto(g.name)"
                :class="[item.nivel > 0 ? 'ml-7 border-l-2 border-l-amber-900/40' : '',
                         'grid grid-cols-12 gap-2 items-start p-2 border border-gray-600 rounded hover:bg-gray-700']"
              >
                <!-- Parameter Name -->
                <div class="col-span-2 flex items-center gap-1 pt-1">
                  <input
                    v-model="item.param.paramName"
                    type="text"
                    required
                    :disabled="!!varianteActiva"
                    class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 font-mono disabled:opacity-60"
                    placeholder="param_name"
                  />
                  <div v-if="item.param.hint || item.param.description" class="relative flex-shrink-0">
                    <button
                      type="button"
                      @click="toggleHelp(item.param)"
                      class="text-blue-400 hover:text-blue-300 focus:outline-none"
                      title="Ver descripción"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                    </button>
                    <div
                      v-if="activeHelp === item.param.paramName"
                      class="absolute left-0 top-6 z-50 w-80 p-3 bg-gray-900 border border-blue-500 rounded shadow-lg text-xs text-gray-200 leading-relaxed"
                    >
                      {{ item.param.hint || item.param.description }}
                    </div>
                  </div>
                </div>

                <!-- Data Type -->
                <div class="col-span-2 pt-1">
                   <select
                     v-model="item.param.dataType"
                     required
                     :disabled="!!varianteActiva"
                     class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 disabled:opacity-60"
                     @change="onDataTypeChange(item.param, $event)"
                   >
                     <option value="string">String</option>
                     <option value="integer">Integer</option>
                     <option value="number">Number</option>
                     <option value="boolean">Boolean</option>
                     <option value="json">JSON</option>
                     <option value="bbox">BBox [minx, miny, maxx, maxy]</option>
                     <option value="enum">ENUM</option>
                     <option value="json_filter_map">Filter Map (enum↔enum)</option>
                     <option value="overpass_query">Overpass Query Builder</option>
                   </select>
                   <p v-if="fijadosPorVariante.has(item.param.paramName)"
                      class="text-[10px] text-purple-300/90 mt-1 leading-tight truncate"
                      :title="'La variante «' + varianteActiva.code + '» fija: ' + fijadosPorVariante.get(item.param.paramName)">
                     fijado por «{{ varianteActiva.code }}»
                   </p>
                </div>

                <!-- Required Checkbox -->
                <div class="col-span-1 flex justify-center pt-2">
                  <label class="flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      v-model="item.param.required"
                      :disabled="!!varianteActiva"
                      class="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 disabled:opacity-60"
                    />
                  </label>
                </div>

                <!-- Default Value / Enum Values — ocupa el máximo espacio disponible -->
                <div :class="varianteActiva ? 'col-span-3' : 'col-span-6'" class="space-y-1">
                  <!-- Enum: editar opciones como texto -->
                  <input
                    v-if="item.param.dataType === 'enum'"
                    :value="item.param.enumValuesString || ''"
                    @input="updateEnumValuesString(item.param, $event.target.value)"
                    type="text"
                    class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 font-mono"
                    placeholder="[opcion1, opcion2, opcion3]"
                  />
                  <!-- Enum: default value select (normalizado a {value,label}) -->
                  <select
                    v-if="item.param.dataType === 'enum' && item.param.enumValues && item.param.enumValues.length"
                    v-model="item.param.defaultValue"
                    class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500 text-gray-400"
                  >
                    <option value="">Default (opcional)</option>
                    <option
                      v-for="opt in normalizeOpts(item.param.enumValues)"
                      :key="opt.value"
                      :value="opt.value"
                    >{{ opt.label }}</option>
                  </select>
                  <!-- Otros tipos: campo de texto libre -->
                  <input
                    v-else-if="item.param.dataType !== 'enum'"
                    v-model="item.param.defaultValue"
                    type="text"
                    class="w-full px-2 py-1 text-sm bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
                    placeholder="Valor por defecto (opcional)"
                  />
                </div>

                <!-- Valor en la variante activa (vacío = no fijado: rige el default) -->
                <div v-if="varianteActiva" class="col-span-4 space-y-1">
                  <select v-if="item.param.dataType === 'enum'"
                          :value="valorVariante(item.param.paramName)"
                          @change="setValorVariante(item.param.paramName, $event.target.value)"
                          class="input w-full text-xs"
                          :class="{ 'border-purple-700': valorVariante(item.param.paramName) !== '' }">
                    <option value="">— no fijado —</option>
                    <option v-for="o in normalizeOpts(item.param.enumValues)" :key="o.value" :value="o.value">{{ o.label }}</option>
                  </select>
                  <select v-else-if="item.param.dataType === 'boolean'"
                          :value="valorVariante(item.param.paramName)"
                          @change="setValorVariante(item.param.paramName, $event.target.value)"
                          class="input w-full text-xs"
                          :class="{ 'border-purple-700': valorVariante(item.param.paramName) !== '' }">
                    <option value="">— no fijado —</option>
                    <option value="true">true</option>
                    <option value="false">false</option>
                  </select>
                  <textarea v-else-if="item.param.dataType === 'json' || esValorLargo(valorVariante(item.param.paramName))"
                            :value="valorVariante(item.param.paramName)"
                            @input="setValorVariante(item.param.paramName, $event.target.value)"
                            rows="3" class="input w-full text-xs font-mono"
                            :class="{ 'border-purple-700': valorVariante(item.param.paramName) !== '', 'border-red-700': !!errorJsonValor(item.param) }"
                            placeholder="— no fijado —"></textarea>
                  <input v-else
                         :value="valorVariante(item.param.paramName)"
                         @input="setValorVariante(item.param.paramName, $event.target.value)"
                         class="input w-full text-xs"
                         :class="{ 'border-purple-700': valorVariante(item.param.paramName) !== '' }"
                         placeholder="— no fijado —" />
                  <p v-if="errorJsonValor(item.param)" class="text-[10px] text-red-400">{{ errorJsonValor(item.param) }}</p>
                  <button v-if="valorVariante(item.param.paramName) !== ''" type="button"
                          @click="toggleCandado(item.param.paramName)"
                          class="text-[10px] px-1.5 py-0.5 rounded border transition-colors"
                          :class="estaBloqueado(item.param.paramName)
                            ? 'border-purple-700 bg-purple-950 text-purple-300'
                            : 'border-gray-600 text-gray-500 hover:text-gray-300'"
                          :title="estaBloqueado(item.param.paramName)
                            ? 'Inviolable: el recurso no puede sobrescribir este valor. Clic para liberar.'
                            : 'Pisable: el recurso puede sobrescribirlo. Clic para hacerlo inviolable.'">
                    {{ estaBloqueado(item.param.paramName) ? '🔒 inviolable' : '🔓 pisable' }}
                  </button>
                </div>

                <!-- Actions -->
                <div class="col-span-1 flex justify-center pt-1">
                  <button
                    v-if="!varianteActiva"
                    type="button"
                    @click="removeParameter(parameters.indexOf(item.param))"
                    class="text-red-400 hover:text-red-300"
                    title="Remove parameter"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </div>
              </div>
              </template>
              </template>
            </div>

            <!-- Claves de la variante fuera del catálogo (heredadas): valor editable -->
            <div v-if="varianteActiva && extrasVariante.length" class="mt-3">
              <div class="flex items-center gap-2 mb-1 px-1">
                <span class="text-[11px] uppercase tracking-wide font-semibold text-amber-300">Fuera del catálogo</span>
                <span class="text-[10px] text-gray-500">({{ extrasVariante.length }})</span>
                <div class="flex-1 border-t border-gray-700"></div>
              </div>
              <div v-for="e in extrasVariante" :key="e.key"
                   class="grid grid-cols-12 gap-2 items-start p-2 border border-amber-900/50 rounded">
                <div class="col-span-3 pt-1 text-xs font-mono text-amber-300">{{ e.key }}</div>
                <div class="col-span-8">
                  <textarea v-if="esValorLargo(e.value)" v-model="e.value" rows="3" class="input w-full text-xs font-mono"></textarea>
                  <input v-else v-model="e.value" class="input w-full text-xs" />
                </div>
                <div class="col-span-1 pt-1 text-right">
                  <button type="button" @click="setValorVariante(e.key, '')"
                          class="text-red-400 hover:text-red-300 text-sm" title="Quitar de la variante">✕</button>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>

        <!-- Validation Error -->
        <div v-if="validationError" class="p-3 bg-red-900 border border-red-700 rounded text-red-200 text-sm">
          {{ validationError }}
        </div>

        <!-- Form Actions -->
        <div class="flex justify-end space-x-3 pt-6 border-t border-gray-600">
          <button type="button" @click="$emit('close')" class="btn btn-secondary">
            Cancel
          </button>
          <button 
            type="submit" 
            :disabled="submitting || !isFormValid" 
            class="btn btn-primary"
          >
            {{ submitting ? 'Saving...' : (Fetcher ? 'Update' : 'Create') }}
          </button>
        </div>
       </form>
     </div>
   </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useConfirm } from '../composables/useConfirm'
const confirmar = ref(null)
const { confirm } = useConfirm()
watch(confirmar, async (val) => {
  if (!val) return
  const f = val.onConfirm
  const { ok } = await confirm({ title: val.title, message: val.message, confirmText: val.confirmText, danger: true })
  confirmar.value = null
  if (ok && f) await f()
})
import {
  createFetcher,
  updateFetcher,
  createTypeFetcherParam,
  updateTypeFetcherParam,
  deleteTypeFetcherParam,
  createFetcherPreset,
  updateFetcherPreset,
  deleteFetcherPreset
} from '../api/graphql'

const props = defineProps({
  Fetcher: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close', 'saved'])

// Form data
const formData = ref({
  name: '',
  description: ''
})

const parameters = ref([])
const submitting = ref(false)
const validationError = ref('')
const activeTab = ref('required')
const activeHelp = ref(null)

function toggleHelp(param) {
  activeHelp.value = activeHelp.value === param.paramName ? null : param.paramName
}

// Computed properties
const requiredParams = computed(() => {
  return parameters.value.filter(p => p.required)
})

const optionalParams = computed(() => {
  return parameters.value.filter(p => !p.required)
})

// Unión básicos + específicos de la variante activa, SIN duplicar por colisión:
// una clave fijada por la variante que ya existe en la definición básica cuenta
// una sola vez; solo suman las claves de la variante fuera del catálogo.
const clavesBasicas = computed(() => new Set(parameters.value.map(p => p.paramName)))
const extrasVariante = computed(() => {
  if (!varianteActiva.value) return []
  return varianteActiva.value.entries.filter(e => e.key && !clavesBasicas.value.has(e.key))
})
const totalRequired = computed(() => requiredParams.value.filter(visibleConVariante).length)
const totalOptional = computed(() => optionalParams.value.filter(visibleConVariante).length + extrasVariante.value.length)
const totalAll = computed(() => parameters.value.filter(visibleConVariante).length + extrasVariante.value.length)
const fijadosPorVariante = computed(() => {
  if (!varianteActiva.value) return new Map()
  return new Map(varianteActiva.value.entries.filter(e => e.key).map(e => [e.key, e.value]))
})

function visibleConVariante(p) {
  // En modo variante, el árbol se PODA con las decisiones que la variante toma:
  // un parámetro condicional solo aparece si su controlador (valor de la
  // variante, o default de la especie en su defecto) activa su rama. En modo
  // Genérico no se poda: la definición muestra el árbol completo.
  if (!varianteActiva.value) return true
  const vw = _vw(p)
  if (!vw || !vw.param) return true
  let actual = valorVariante(vw.param)
  if (actual === '' || actual == null) {
    const ctrl = parameters.value.find(x => x.paramName === vw.param)
    actual = ctrl?.defaultValue != null ? String(ctrl.defaultValue) : ''
  }
  const vals = vw.in || (vw.eq != null ? [vw.eq] : [])
  return vals.map(String).includes(String(actual))
}

const filteredParams = computed(() => {
  let base
  if (activeTab.value === 'required') base = requiredParams.value
  else if (activeTab.value === 'optional') base = optionalParams.value
  else base = parameters.value
  return base.filter(visibleConVariante)
})

const ETIQUETAS_GRUPO = {
  peticion: 'Parámetros de petición',
  paginacion: 'Parámetros de paginación',
  extraccion: 'Parámetros de extracción',
  http: 'Parámetros de conexión',
  query: 'Parámetros de consulta',
  otros: 'Otros parámetros',
}
function tituloGrupo(n) { return ETIQUETAS_GRUPO[n] || ('Parámetros de ' + n.replace(/_/g, ' ')) }
const gruposColapsados = ref(new Set())
function grupoAbierto(n) { return !gruposColapsados.value.has(n) }
function toggleGrupo(n) {
  const next = new Set(gruposColapsados.value)
  next.has(n) ? next.delete(n) : next.add(n)
  gruposColapsados.value = next
}
function _vw(p) {
  if (!p.visibleWhen) return null
  try { return typeof p.visibleWhen === 'string' ? JSON.parse(p.visibleWhen) : p.visibleWhen } catch { return null }
}
const filteredParamGroups = computed(() => {
  // Anidamiento por controlador: dentro de cada grupo, los parámetros sin
  // condición van al nivel raíz; los condicionales se cuelgan como RAMAS bajo
  // su parámetro controlador, agrupados por el valor que los activa
  // (pagination ▸ cursor ▸ cursor_param, next_cursor_field…). El árbol de
  // decisiones se ve como árbol.
  const grupos = new Map()
  for (const p of filteredParams.value) {
    const g = p.group || 'otros'
    if (!grupos.has(g)) grupos.set(g, [])
    grupos.get(g).push(p)
  }
  const nombres = [...grupos.keys()].sort((a, b) =>
    tituloGrupo(a).localeCompare(tituloGrupo(b), 'es'))
  return nombres.map(n => {
    const todos = grupos.get(n)
    const raiz = todos.filter(p => !_vw(p))
    // ramas por (controlador, valores que activan), respetando orden de aparición
    const ramas = new Map()
    for (const p of todos) {
      const vw = _vw(p)
      if (!vw || !vw.param) continue
      const vals = vw.in || (vw.eq != null ? [vw.eq] : [])
      const clave = vw.param + ' = ' + vals.join(' | ')
      if (!ramas.has(clave)) ramas.set(clave, { controlador: vw.param, etiqueta: vals.join(' | '), params: [] })
      ramas.get(clave).params.push(p)
    }
    // lista de render: cada raíz seguida de sus ramas; huérfanas (controlador
    // fuera del grupo o inexistente) al final con etiqueta completa
    const items = []
    const colgadas = new Set()
    for (const p of raiz) {
      items.push({ tipo: 'param', param: p, nivel: 0 })
      for (const [clave, rama] of ramas) {
        if (rama.controlador === p.paramName) {
          items.push({ tipo: 'rama', clave, controlador: rama.controlador, etiqueta: rama.etiqueta, nivel: 1 })
          for (const hijo of rama.params) items.push({ tipo: 'param', param: hijo, nivel: 1 })
          colgadas.add(clave)
        }
      }
    }
    for (const [clave, rama] of ramas) {
      if (colgadas.has(clave)) continue
      items.push({ tipo: 'rama', clave, controlador: rama.controlador, etiqueta: rama.etiqueta, externa: true, nivel: 0 })
      for (const hijo of rama.params) items.push({ tipo: 'param', param: hijo, nivel: 1 })
    }
    return { name: n, params: todos, items }
  })
})

const isFormValid = computed(() => {
  // Basic fields must be filled
  if (!formData.value.name.trim()) {
    return false
  }

  // All parameter names must be unique and filled
  const paramNames = parameters.value.map(p => p.paramName?.trim()).filter(n => n)
  const uniqueNames = new Set(paramNames)
  if (uniqueNames.size !== paramNames.length) {
    return false
  }
  
  // All required fields in parameters must be filled
  for (const param of parameters.value) {
    if (!param.paramName?.trim() || !param.dataType) {
      return false
    }
  }
  
  return true
})

// Initialize form when Fetcher prop changes
watch(() => props.Fetcher, (newFetcher) => {
  if (newFetcher) {
    formData.value = {
      name: newFetcher.name || '',
      description: newFetcher.description || ''
    }

    // Load existing parameters
    if (newFetcher.paramsDef && Array.isArray(newFetcher.paramsDef)) {
      parameters.value = newFetcher.paramsDef.map(p => ({
        id: p.id || null,
        paramName: p.paramName || '',
        dataType: p.dataType || 'string',
        hint: p.hint || p.description || null,
        required: p.required !== undefined ? p.required : true,
        defaultValue: p.defaultValue ?? null,
        enumValues: p.enumValues || null,
        group: p.group || null,
        visibleWhen: p.visibleWhen || null,
        enumValuesString: p.enumValues && Array.isArray(p.enumValues)
          ? (typeof p.enumValues[0] === 'string'
              ? '[' + p.enumValues.join(', ') + ']'
              : '(opciones complejas — editar por script)')
          : '',
        description: p.description || null
      }))
    } else {
      parameters.value = []
    }
  } else {
    formData.value = {
      name: '',
      description: ''
    }
    parameters.value = []
  }
}, { immediate: true })

function addParameter() {
  parameters.value.push({
    id: null,
    paramName: '',
    dataType: 'string',
    required: true,
    defaultValue: null,
    enumValues: null,
    enumValuesString: ''
  })
}

function removeParameter(index) {
  parameters.value.splice(index, 1)
}

async function submitForm() {
  if (!isFormValid.value) {
    validationError.value = 'Please fill in all required fields correctly'
    return
  }

  try {
    submitting.value = true
    validationError.value = null

    const input = {
      name: formData.value.name,
      description: formData.value.description || null
    }

    let fetcherId
    if (props.Fetcher) {
      // Update existing fetcher
      await updateFetcher(props.Fetcher.id, input)
      fetcherId = props.Fetcher.id
    } else {
      // Create new fetcher
      const result = await createFetcher(input)
      fetcherId = result.createFetcher.id
    }

    // Now sync parameters
    await syncParameters(fetcherId)

    emit('saved', `Fetcher "${formData.value.name}" ${props.Fetcher ? 'updated' : 'created'} successfully`)

  } catch (e) {
    validationError.value = e.message || 'Failed to save Fetcher'
  } finally {
    submitting.value = false
  }
}

async function syncParameters(fetcherId) {
  const existingParams = props.Fetcher?.paramsDef || []
  const existingParamIds = new Set(existingParams.map(p => p.id))
  const currentParamIds = new Set(parameters.value.filter(p => p.id).map(p => p.id))

  // Delete removed parameters
  for (const existingParam of existingParams) {
    if (!currentParamIds.has(existingParam.id)) {
      await deleteTypeFetcherParam(existingParam.id)
    }
  }

  // Create or update parameters
  for (const param of parameters.value) {
    const paramInput = {
      fetcherId: fetcherId,
      paramName: param.paramName,
      dataType: param.dataType,
      required: param.required,
      defaultValue: param.defaultValue || null,
      enumValues: param.enumValues || null
    }

    if (param.id && existingParamIds.has(param.id)) {
      // Update existing parameter
      const updateInput = {
        paramName: param.paramName,
        dataType: param.dataType,
        required: param.required,
        defaultValue: param.defaultValue || null,
        enumValues: param.enumValues || null
      }
      await updateTypeFetcherParam(param.id, updateInput)
    } else {
      // Create new parameter
      const result = await createTypeFetcherParam(paramInput)
      param.id = result.createTypeFetcherParam.id
    }
  }
}

/** Normaliza enum_values a [{value, label}] para mostrar en selects. */
function normalizeOpts(vals) {
  if (!vals) return []
  return vals.map(v => typeof v === 'string' ? { value: v, label: v } : { value: v.value ?? v, label: v.label ?? v.value ?? String(v) })
}

// ENUM helper function
function updateEnumValuesString(param, value) {
  // Update the string as-is (let user type freely)
  param.enumValuesString = value

  // Parse to array for saving
  let cleanValue = value.trim()

  // Remove surrounding brackets if present
  if (cleanValue.startsWith('[')) {
    cleanValue = cleanValue.substring(1)
  }
  if (cleanValue.endsWith(']')) {
    cleanValue = cleanValue.substring(0, cleanValue.length - 1)
  }

  // Parse comma-separated values
  const values = cleanValue
    .split(',')
    .map(v => v.trim())
    .filter(v => v.length > 0)

  param.enumValues = values.length > 0 ? values : null
}


// ── Variantes: implementaciones concretas de la tecnología ──────────────────
// Panel básico colapsable: abierto al crear (hay que definir params), plegado al editar
const seccionBasicaAbierta = ref(!props.Fetcher)
// Textareas que crecen con el contenido (sin scroll interno)
const vAutogrow = {
  mounted(el) {
    el.style.overflowY = 'hidden'
    const ajustar = () => { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px' }
    el.addEventListener('input', ajustar)
    requestAnimationFrame(ajustar)
  },
  updated(el) { el.style.height = 'auto'; el.style.height = el.scrollHeight + 'px' },
}
const variantes = ref([])
const varianteActiva = ref(null)
let _tmpSeq = 0

function _aEntries(paramsObj) {
  return Object.entries(paramsObj || {}).map(([key, v]) => ({
    key, value: (v !== null && typeof v === 'object') ? JSON.stringify(v, null, 1) : String(v ?? ''),
  }))
}
function _deEntries(entries) {
  const out = {}
  for (const e of entries) {
    if (!e.key) continue
    const dt = tipoDe(e.key)
    let v = e.value
    if (dt === 'json' || esJsonTexto(v)) { try { v = JSON.parse(v) } catch { /* se valida antes */ } }
    else if (dt === 'integer' || dt === 'number') { const n = Number(v); if (!Number.isNaN(n) && v !== '') v = n }
    else if (dt === 'boolean') { v = String(v) === 'true' }
    out[e.key] = v
  }
  return out
}
function esJsonTexto(v) { const t = String(v ?? '').trim(); return t.startsWith('{') || t.startsWith('[') }
function esValorLargo(v) { return String(v ?? '').length > 70 || esJsonTexto(v) }
function tipoDe(k) { return parameters.value.find(p => p.paramName === k)?.dataType || 'string' }
function estaBloqueado(pn) {
  return (varianteActiva.value?.locked || []).includes(pn)
}
function toggleCandado(pn) {
  const va = varianteActiva.value
  if (!va) return
  va.locked = va.locked || []
  const i = va.locked.indexOf(pn)
  if (i >= 0) va.locked.splice(i, 1)
  else va.locked.push(pn)
}
function valorVariante(pn) {
  const e = varianteActiva.value?.entries.find(x => x.key === pn)
  return e ? e.value : ''
}
function setValorVariante(pn, v) {
  const va = varianteActiva.value
  if (!va) return
  const i = va.entries.findIndex(x => x.key === pn)
  if (v === '' || v == null) {
    if (i >= 0) va.entries.splice(i, 1)
    const li = (va.locked || []).indexOf(pn)
    if (li >= 0) va.locked.splice(li, 1)
  }
  else if (i >= 0) va.entries[i].value = v
  else va.entries.push({ key: pn, value: v })
}
function errorJsonValor(param) {
  const v = valorVariante(param.paramName)
  if (v === '') return null
  if (param.dataType !== 'json' && !esJsonTexto(v)) return null
  try { JSON.parse(v); return null } catch (e) { return 'JSON inválido: ' + e.message }
}
function seleccionarVariante(v) { varianteActiva.value = varianteActiva.value === v ? null : v }
function nuevaVariante() {
  const v = { id: null, _tmp: ++_tmpSeq, code: '', description: '', entries: [], locked: [], _error: null, _saving: false }
  variantes.value.push(v)
  varianteActiva.value = v
}
watch(() => props.Fetcher, (f) => {
  variantes.value = (f?.presets || []).map(p => {
    const entries = _aEntries(p.params)
    const locked = [...(p.lockedParams || [])]
    return {
      id: p.id, code: p.code, description: p.description || '',
      entries, locked, _error: null, _saving: false,
      _orig: { code: p.code, description: p.description || '', entries: JSON.parse(JSON.stringify(entries)), locked: [...locked] },
    }
  })
  varianteActiva.value = null
}, { immediate: true })

async function guardarVariante(v) {
  v._error = null
  const conError = v.entries.find(e => {
    const t = String(e.value ?? '').trim()
    if (!t.startsWith('{') && !t.startsWith('[')) return false
    try { JSON.parse(t); return false } catch { return true }
  })
  if (conError) { v._error = `El parámetro '${conError.key}' tiene JSON inválido`; return }
  v._saving = true
  try {
    const params = _deEntries(v.entries)
    if (v.id) {
      await updateFetcherPreset(v.id, { code: v.code, description: v.description, params, lockedParams: v.locked || [] })
    } else {
      const res = await createFetcherPreset(props.Fetcher.id, v.code, v.description, params, v.locked || [])
      v.id = res.createFetcherPreset.id
    }
    v._orig = { code: v.code, description: v.description, entries: JSON.parse(JSON.stringify(v.entries)), locked: [...(v.locked || [])] }
    emit('saved', `Variante "${v.code}" guardada`)
  } catch (e) {
    v._error = e?.message || String(e)
  } finally {
    v._saving = false
  }
}
function cerrarVariante(v) {
  // Cerrar sin guardar: las variantes guardadas vuelven a su último estado
  // persistido; una variante nueva sin guardar se descarta del listado.
  if (v.id && v._orig) {
    v.code = v._orig.code
    v.description = v._orig.description
    v.entries = JSON.parse(JSON.stringify(v._orig.entries))
    v.locked = [...(v._orig.locked || [])]
    v._error = null
  } else if (!v.id) {
    variantes.value = variantes.value.filter(x => x !== v)
  }
  varianteActiva.value = null
}
async function retirarVariante(v) {
  confirmar.value = {
    title: 'Retirar variante', confirmText: 'Retirar',
    message: `¿Retirar la variante «${v.code}»? Se bloqueará si algún recurso la usa.`,
    onConfirm: async () => {
      v._error = null
      try {
        await deleteFetcherPreset(v.id)
        variantes.value = variantes.value.filter(x => x !== v)
        varianteActiva.value = null
        emit('saved', `Variante "${v.code}" retirada`)
      } catch (e) { v._error = e?.message || String(e) }
    },
  }
}

</script>