<template>
  <div class="p-6 flex flex-col h-full" ref="viewEl">
    <div class="flex justify-between items-center mb-4">
      <h1 class="text-2xl font-bold">Resources</h1>
      <button @click="showCreateModal = true" class="btn btn-primary text-sm">
        + Nuevo recurso
      </button>
    </div>

    <div v-if="loading" class="text-gray-400 text-center py-8">
      Loading...
    </div>

    <div v-else-if="error" class="p-4 bg-red-900 border border-red-700 rounded text-red-200">
      {{ error }}
    </div>

    <div v-else class="card flex flex-col min-h-0 flex-1">
      <!-- Search + filters -->
      <div class="px-3 py-2 border-b border-gray-700 space-y-1.5 text-xs flex-shrink-0" ref="filterEl">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name or publisher..."
          class="input w-full text-xs py-1 px-2"
        />

        <div class="flex flex-wrap gap-4 items-center">
          <!-- Type filter -->
          <div class="flex items-center gap-1.5">
            <span class="text-gray-400 font-medium">Type:</span>
            <select v-model="selectedType" class="input py-0.5 px-2 text-xs" style="min-width:140px">
              <option value="">All</option>
              <option v-for="t in availableTypes" :key="t" :value="t">{{ t }}</option>
            </select>
          </div>

          <!-- Publisher filter -->
          <div class="flex items-center gap-1.5">
            <span class="text-gray-400 font-medium">Publisher:</span>
            <select v-model="selectedPublisher" class="input py-0.5 px-2 text-xs" style="min-width:160px">
              <option value="">All</option>
              <option v-for="p in availablePublishers" :key="p.id" :value="p.id">{{ p.nombre }}</option>
            </select>
          </div>

          <!-- Level filter -->
          <div class="flex items-center gap-1.5">
            <span class="text-gray-400 font-medium">Level:</span>
            <select v-model="selectedNivel" class="input py-0.5 px-2 text-xs" style="min-width:110px">
              <option value="">All</option>
              <option v-for="n in availableNiveles" :key="n" :value="n">{{ n }}</option>
            </select>
          </div>

          <!-- Status filter -->
          <div class="flex items-center gap-2">
            <span class="text-gray-400 font-medium">Status:</span>
            <label class="cursor-pointer flex items-center gap-1">
              <input type="checkbox" v-model="filterAllStatuses" class="accent-blue-500" @change="onAllStatuses" />
              All
            </label>
            <label class="cursor-pointer flex items-center gap-1">
              <input type="checkbox" value="active" v-model="filterStatuses" class="accent-green-500" @change="onStatusChange" />
              <span class="text-green-400">Active</span>
            </label>
            <label class="cursor-pointer flex items-center gap-1">
              <input type="checkbox" value="inactive" v-model="filterStatuses" class="accent-red-500" @change="onStatusChange" />
              <span class="text-red-400">Inactive</span>
            </label>
          </div>

          <!-- Result count + Clear filters -->
          <div class="ml-auto flex items-center gap-3">
            <span class="text-gray-500">
              {{ filteredResources.length }} / {{ resources.length }}
            </span>
            <button @click="clearFilters"
                    :disabled="!hasActiveFilters"
                    class="text-xs px-2 py-0.5 rounded border"
                    :class="hasActiveFilters
                      ? 'border-yellow-600 text-yellow-400 hover:bg-yellow-900/30 cursor-pointer'
                      : 'border-gray-700 text-gray-600 cursor-not-allowed'">
              Clear filters
            </button>
          </div>
        </div>
      </div>

      <div class="overflow-y-auto flex-1">
      <table class="w-full">
        <thead class="sticky top-0 z-10 bg-gray-800">
          <tr class="border-b border-gray-700 text-xs text-gray-400">
            <th class="text-left py-2 px-3 font-medium">Name</th>
            <th class="text-left py-2 px-3 font-medium">Publisher</th>
            <th class="text-left py-2 px-3 font-medium">Type</th>
            <th class="text-left py-2 px-3 font-medium">Status</th>
            <th class="text-right py-2 px-3 font-medium">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="resource in pagedResources"
            :key="resource.id"
            class="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors"
          >
            <td class="py-1.5 px-3 text-xs font-medium text-white whitespace-nowrap">{{ resource.name }}</td>
            <td class="py-1.5 px-3 text-xs text-gray-400 whitespace-nowrap">
              <span v-if="resource.publisherObj?.acronimo"
                    :title="resource.publisherObj.nombre"
                    class="cursor-help">
                {{ resource.publisherObj.acronimo }}
                <span class="inline-flex items-center justify-center w-3 h-3 rounded-full bg-gray-600 text-gray-300 text-[9px] leading-none ml-0.5 align-middle">i</span>
              </span>
              <span v-else>{{ resource.publisherObj?.nombre || resource.publisher || '—' }}</span>
            </td>
            <td class="py-1.5 px-3 whitespace-nowrap">
              <code class="text-xs bg-gray-900 px-1.5 py-0.5 rounded text-blue-400">
                {{ resource.fetcher.code }}
              </code>
            </td>
            <td class="py-1.5 px-3 whitespace-nowrap">
              <div class="flex items-center gap-1.5">
                <span class="inline-block h-1.5 w-1.5 rounded-full flex-shrink-0"
                      :class="resource.active ? 'bg-green-400' : 'bg-red-500'"></span>
                <span class="text-xs" :class="resource.active ? 'text-green-400' : 'text-red-400'">
                  {{ resource.active ? 'Activo' : 'Inactivo' }}
                </span>
                <span v-if="runningResourceIds.has(resource.id)"
                  class="text-xs font-bold bg-blue-900 text-blue-300 border border-blue-700 px-1.5 py-0.5 rounded-full animate-pulse">
                  RUN
                </span>
              </div>
            </td>
            <td class="py-1.5 px-3">
              <div class="flex justify-end gap-1">
                <button
                  @click="openExecuteModal(resource)"
                  class="text-xs px-2 py-0.5 rounded bg-blue-700 hover:bg-blue-600 text-white"
                  title="Ejecutar"
                >Run</button>
                <button
                  @click="showPreviewData(resource)"
                  class="text-xs px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-200"
                >Test</button>
                <button
                  @click="editResource(resource)"
                  class="text-xs px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-200"
                >Edit</button>
                <button
                  @click="handleClone(resource)"
                  class="text-xs px-2 py-0.5 rounded bg-gray-700 hover:bg-gray-600 text-gray-200"
                  title="Clonar"
                >Clone</button>
                <button
                  @click="confirmDelete(resource)"
                  class="text-xs px-2 py-0.5 rounded bg-red-900/60 hover:bg-red-800 text-red-300"
                >
                  Delete
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
      </div>

      <div v-if="filteredResources.length === 0" class="text-gray-400 text-center py-8 space-y-2">
        <div v-if="hasActiveFilters">
          <p>No resources match the active filters.</p>
          <button @click="clearFilters" class="mt-1 text-xs text-yellow-400 hover:text-yellow-300 underline">Clear filters</button>
        </div>
        <p v-else>No resources configured yet. Click "+ New resource" to add one.</p>
      </div>

      <!-- Pagination -->
      <div v-if="filteredResources.length > 0"
           class="flex items-center justify-between px-3 py-1.5 border-t border-gray-700 text-xs flex-shrink-0"
           ref="paginEl">
        <div class="flex items-center gap-3 text-gray-400">
          <span>
            {{ (currentPage - 1) * pageSize + 1 }}–{{ Math.min(currentPage * pageSize, filteredResources.length) }}
            de {{ filteredResources.length }}
          </span>
          <div class="flex items-center gap-1">
            <span>Filas:</span>
            <select v-model.number="pageSizeOverride" class="input py-0 px-1 text-xs">
              <option :value="0">Auto ({{ autoPageSize }})</option>
              <option v-for="n in [10,15,20,25,50]" :key="n" :value="n">{{ n }}</option>
            </select>
          </div>
        </div>
        <div v-if="totalPages > 1" class="flex gap-0.5">
          <button @click="currentPage--" :disabled="currentPage === 1"
            class="px-2 py-0.5 rounded border border-gray-600 text-gray-300 disabled:opacity-30 hover:bg-gray-700">‹</button>
          <button v-for="p in totalPages" :key="p" @click="currentPage = p"
            :class="p === currentPage ? 'bg-blue-600 text-white border-blue-600' : 'text-gray-300 border-gray-600 hover:bg-gray-700'"
            class="px-2 py-0.5 rounded border">{{ p }}</button>
          <button @click="currentPage++" :disabled="currentPage === totalPages"
            class="px-2 py-0.5 rounded border border-gray-600 text-gray-300 disabled:opacity-30 hover:bg-gray-700">›</button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <div
      v-if="showCreateModal || showEditModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="closeModals"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-5xl max-h-[90vh] overflow-y-auto">
        <h2 class="text-xl font-bold mb-4">
          {{ showCreateModal ? 'Create Resource' : 'Edit Resource' }}
        </h2>

        <form @submit.prevent="submitForm" class="space-y-3 text-sm">
          <div class="grid grid-cols-2 gap-4">
            <div>
              <Tooltip :text="getTooltip('name')">
                <label class="block text-xs font-medium mb-1">Name</label>
              </Tooltip>
              <input
                v-model="form.name"
                type="text"
                required
                class="input w-full text-sm"
                :placeholder="getPlaceholder('name')"
              />
            </div>

            <div>
              <label class="block text-xs font-medium mb-1">Publisher</label>
              <select v-model="form.publisherId" class="input w-full text-sm">
                <option :value="null">Sin asignar</option>
                <option v-for="p in publishers" :key="p.id" :value="p.id">{{ p.nombre }}</option>
              </select>
            </div>
          </div>

          <div>
            <Tooltip :text="getTooltip('fetcher_id')">
              <label class="block text-xs font-medium mb-1">Fetcher Type</label>
            </Tooltip>
            <select v-model="form.fetcherId" required class="input w-full text-sm">
              <option value="">Select a type...</option>
              <option
                v-for="type in fetchers"
                :key="type.id"
                :value="type.id"
              >
                {{ type.code }} - {{ type.description }}
              </option>
            </select>
          </div>

          <div>
            <!-- Tabs for Parameters and Concurrency -->
            <div class="flex space-x-1 mb-4 border-b border-gray-600">
              <button
                type="button"
                @click="activeParamTab = 'parameters'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeParamTab === 'parameters'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Parameters
              </button>
              <button
                type="button"
                @click="activeParamTab = 'concurrency'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeParamTab === 'concurrency'
                    ? 'text-blue-400 border-b-2 border-blue-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Concurrency & Parallelism
              </button>
              <button
                v-if="showEditModal"
                type="button"
                @click="activeParamTab = 'outputs'"
                :class="[
                  'px-4 py-2 text-sm font-medium transition-colors',
                  activeParamTab === 'outputs'
                    ? 'text-green-400 border-b-2 border-green-400'
                    : 'text-gray-400 hover:text-gray-300'
                ]"
              >
                Outputs
                <span v-if="derivedConfigs.length > 0" class="ml-1 text-xs bg-green-800 text-green-200 rounded-full px-1.5">{{ derivedConfigs.length }}</span>
              </button>
            </div>

            <!-- Tab Content: Parameters -->
            <div v-if="activeParamTab === 'parameters'" class="h-[400px] overflow-y-auto pr-2">
              <!-- Required Parameters (always shown) -->
            <div v-if="requiredParams.length > 0" class="mb-4">
              <h4 class="text-sm font-medium mb-2 text-red-400">Required Parameters</h4>
              <div class="space-y-1">
                <div
                  v-for="param in requiredParams"
                  :key="`req-${param.paramName}`"
                  class="border border-red-600 rounded p-2 bg-red-950 bg-opacity-20"
                  :class="isFullWidthParam(param.dataType) ? 'space-y-2' : 'flex gap-2 items-center'"
                >
                  <!-- Header row: always flex -->
                  <div :class="isFullWidthParam(param.dataType) ? 'flex items-center justify-between' : 'w-1/5 flex-shrink-0'">
                    <div>
                      <label class="block text-xs text-gray-300 mb-1">{{ param.paramName }}</label>
                      <span class="text-xs text-gray-400">{{ param.dataType }}</span>
                    </div>
                    <div class="flex-shrink-0 flex items-center gap-1.5" :class="!isFullWidthParam(param.dataType) ? 'hidden' : ''" title="Pedir valor al ejecutar">
                      <input type="checkbox" :id="`ext-${param.paramName}-top`"
                             :checked="form.params.find(p=>p.key===param.paramName)?.isExternal"
                             @change="toggleParamExternal(param.paramName)"
                             class="accent-yellow-400 cursor-pointer" />
                      <label :for="`ext-${param.paramName}-top`" class="text-xs text-gray-500 cursor-pointer select-none">runtime</label>
                    </div>
                  </div>
                  <!-- Input area -->
                  <div :class="isFullWidthParam(param.dataType) ? 'w-full' : 'flex-1 min-w-0'">
                    <FilterMapEditor
                      v-if="param.dataType === 'json_filter_map' && param.enumValues"
                      :modelValue="getParamValue(param.paramName) || '{}'"
                      :enumValues="param.enumValues"
                      @update:modelValue="updateParamValue(param.paramName, $event)"
                    />
                    <div v-else-if="param.dataType === 'overpass_query'" class="flex items-center gap-2">
                      <span class="text-xs text-gray-400 font-mono flex-1 truncate">
                        {{ overpassSummary(param.paramName) }}
                      </span>
                      <button type="button" @click="openOverpassModal(param.paramName)"
                              class="px-2 py-0.5 text-xs rounded border border-blue-700 text-blue-400 hover:bg-blue-900">
                        Editar query
                      </button>
                    </div>
                    <div v-else-if="param.dataType === 'enum' && param.enumValues" class="space-y-1.5">
                      <EnumRadioGroup
                        :modelValue="getParamValue(param.paramName)"
                        :options="enumOpts(param.enumValues)"
                        :clearable="!param.required"
                        @update:modelValue="updateParamValue(param.paramName, $event)"
                      />
                      <EnumMetaPreview
                        :filters="selectedEnumMeta(param.paramName, param.enumValues, 'filters')"
                      />
                    </div>
                    <input
                      v-else
                      :value="getParamValue(param.paramName)"
                      type="text"
                      :placeholder="param.defaultValue || `Enter ${param.paramName}...`"
                      class="input w-full text-xs"
                      @input="updateParamValue(param.paramName, $event.target.value)"
                    />
                  </div>
                  <!-- Runtime checkbox (non-fullwidth params) -->
                  <div v-if="!isFullWidthParam(param.dataType)" class="flex-shrink-0 flex items-center gap-1.5" title="Pedir valor al ejecutar">
                    <input
                      type="checkbox"
                      :id="`ext-${param.paramName}`"
                      :checked="form.params.find(p=>p.key===param.paramName)?.isExternal"
                      @change="toggleParamExternal(param.paramName)"
                      class="accent-yellow-400 cursor-pointer"
                    />
                    <label :for="`ext-${param.paramName}`" class="text-xs text-gray-500 cursor-pointer select-none">runtime</label>
                  </div>
                </div>
              </div>
            </div>

            <!-- Add Optional Parameters Dropdown -->
            <div v-if="selectedFetcher && optionalParams.length > 0" class="mb-4">
              <select
                v-model="selectedOptionalParam"
                @change="addOptionalParameter"
                class="w-full text-sm px-3 py-2 bg-gray-700 border border-gray-600 rounded focus:outline-none focus:border-blue-500"
              >
                <option value="">+ Add optional parameter...</option>
                <option
                  v-for="param in availableOptionalParams"
                  :key="param.paramName"
                  :value="param.paramName"
                >
                  {{ param.paramName }} ({{ param.dataType }})
                </option>
              </select>
            </div>

            <!-- Optional Parameters (added by user) -->
            <div v-if="addedOptionalParams.length > 0">
              <h4 class="text-sm font-medium mb-2 text-blue-400">Optional Parameters</h4>
              <div class="space-y-1">
                <div
                  v-for="paramName in addedOptionalParams"
                  :key="`opt-${paramName}`"
                  class="border border-blue-600 rounded p-2 bg-blue-950 bg-opacity-20"
                  :class="isFullWidthParam(getParamType(paramName)) ? 'space-y-2' : 'flex gap-2 items-center'"
                >
                  <!-- Header row -->
                  <div :class="isFullWidthParam(getParamType(paramName)) ? 'flex items-center justify-between' : 'w-1/5 flex-shrink-0'">
                    <div>
                      <label class="block text-xs text-gray-300 mb-1">{{ paramName }}</label>
                      <span class="text-xs text-gray-400">{{ getParamType(paramName) }}</span>
                    </div>
                    <div v-if="isFullWidthParam(getParamType(paramName))" class="flex items-center gap-1">
                      <input type="checkbox" :id="`ext-opt-${paramName}-top`"
                             :checked="form.params.find(p=>p.key===paramName)?.isExternal"
                             @change="toggleParamExternal(paramName)"
                             class="accent-yellow-400 cursor-pointer" title="Pedir valor al ejecutar" />
                      <label :for="`ext-opt-${paramName}-top`" class="text-xs text-gray-500 cursor-pointer select-none">runtime</label>
                      <button type="button" @click="removeOptionalParam(paramName)"
                              class="text-red-400 hover:text-red-300 ml-1" title="Remove optional parameter">
                        <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                  </div>
                  <!-- Input area -->
                  <div :class="isFullWidthParam(getParamType(paramName)) ? 'w-full' : 'flex-1 min-w-0'">
                    <FilterMapEditor
                      v-if="getParamType(paramName) === 'json_filter_map' && getParamEnumValues(paramName)"
                      :modelValue="getParamValue(paramName) || '{}'"
                      :enumValues="getParamEnumValues(paramName)"
                      @update:modelValue="updateParamValue(paramName, $event)"
                    />
                    <div v-else-if="getParamType(paramName) === 'overpass_query'" class="flex items-center gap-2">
                      <span class="text-xs text-gray-400 font-mono flex-1 truncate">
                        {{ overpassSummary(paramName) }}
                      </span>
                      <button type="button" @click="openOverpassModal(paramName)"
                              class="px-2 py-0.5 text-xs rounded border border-blue-700 text-blue-400 hover:bg-blue-900">
                        Editar query
                      </button>
                    </div>
                    <div v-else-if="getParamType(paramName) === 'enum' && getParamEnumValues(paramName)" class="space-y-1.5">
                      <EnumRadioGroup
                        :modelValue="getParamValue(paramName)"
                        :options="enumOpts(getParamEnumValues(paramName))"
                        :clearable="true"
                        @update:modelValue="updateParamValue(paramName, $event)"
                      />
                      <EnumMetaPreview
                        :filters="selectedEnumMeta(paramName, getParamEnumValues(paramName), 'filters')"
                      />
                    </div>
                    <input
                      v-else
                      :value="getParamValue(paramName)"
                      type="text"
                      :placeholder="getParamDefaultValue(paramName) || `Enter ${paramName}...`"
                      class="input w-full text-xs"
                      @input="updateParamValue(paramName, $event.target.value)"
                    />
                  </div>
                  <!-- Runtime + remove (non-fullwidth) -->
                  <div v-if="!isFullWidthParam(getParamType(paramName))" class="flex-shrink-0 flex items-center gap-1">
                    <input
                      type="checkbox"
                      :id="`ext-opt-${paramName}`"
                      :checked="form.params.find(p=>p.key===paramName)?.isExternal"
                      @change="toggleParamExternal(paramName)"
                      class="accent-yellow-400 cursor-pointer"
                      title="Pedir valor al ejecutar"
                    />
                    <label :for="`ext-opt-${paramName}`" class="text-xs text-gray-500 cursor-pointer select-none">runtime</label>
                    <button
                      type="button"
                      @click="removeOptionalParam(paramName)"
                      class="text-red-400 hover:text-red-300"
                      title="Remove optional parameter"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>
                  </div>
                </div>
              </div>
            </div>

              <!-- No parameters message -->
              <div v-if="requiredParams.length === 0 && addedOptionalParams.length === 0" class="text-center py-4 text-gray-400 text-sm">
                <div v-if="!selectedFetcher">
                  Select a Fetcher to see available parameters
                </div>
                <div v-else>
                  This Fetcher has no parameters defined
                </div>
              </div>
            </div>

            <!-- Tab Content: Concurrency & Parallelism -->
            <div v-if="activeParamTab === 'concurrency'" class="h-[400px] overflow-y-auto pr-2 space-y-4">

              <!-- Fieldset: Parallelism -->
              <fieldset class="border border-blue-700 rounded p-3">
                <legend class="text-xs font-semibold text-blue-400 px-2">Parallelism</legend>
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <Tooltip text="Number of parallel workers. 1 = sequential processing.">
                      <label class="block text-xs font-medium mb-1">Workers</label>
                    </Tooltip>
                    <input v-model.number="form.numWorkers" type="number"
                      :min="concurrencyLimits.workers.min" :max="concurrencyLimits.workers.max"
                      class="input w-full text-sm text-center"
                      :placeholder="concurrencyLimits.workers.default" />
                    <p class="text-xs text-gray-500 mt-1">1 = sequential · max {{ concurrencyLimits.workers.max }}</p>
                    <p class="text-xs text-yellow-400 mt-1" v-if="form.numWorkers > concurrencyLimits.workers.max">
                      ⚠️ Exceeds global limit ({{ concurrencyLimits.workers.max }})
                    </p>
                  </div>
                  <div>
                    <Tooltip text="Maximum simultaneous HTTP requests to the external server.">
                      <label class="block text-xs font-medium mb-1">Max concurrent requests</label>
                    </Tooltip>
                    <input v-model.number="form.maxConcurrentRequests" type="number"
                      :min="concurrencyLimits.concReqs.min" :max="concurrencyLimits.concReqs.max"
                      class="input w-full text-sm"
                      :placeholder="concurrencyLimits.concReqs.default" />
                    <p class="text-xs text-gray-500 mt-1">Default: {{ concurrencyLimits.concReqs.default }} · max {{ concurrencyLimits.concReqs.max }}</p>
                  </div>
                  <div>
                    <Tooltip text="Maximum requests per second to the external API.">
                      <label class="block text-xs font-medium mb-1">Rate limit (req/s)</label>
                    </Tooltip>
                    <input v-model.number="form.rateLimitPerSecond" type="number"
                      :min="concurrencyLimits.rateLimit.min" :max="concurrencyLimits.rateLimit.max"
                      class="input w-full text-sm"
                      :placeholder="concurrencyLimits.rateLimit.default" />
                    <p class="text-xs text-gray-500 mt-1">Default: {{ concurrencyLimits.rateLimit.default }}</p>
                  </div>
                  <div>
                    <Tooltip text="Records per request in paginated APIs.">
                      <label class="block text-xs font-medium mb-1">Batch size</label>
                    </Tooltip>
                    <input v-model.number="form.batchSize" type="number"
                      :min="concurrencyLimits.batchSize.min" :max="concurrencyLimits.batchSize.max"
                      class="input w-full text-sm"
                      :placeholder="concurrencyLimits.batchSize.default" />
                    <p class="text-xs text-gray-500 mt-1">Default: {{ concurrencyLimits.batchSize.default }} · max {{ concurrencyLimits.batchSize.max }}</p>
                  </div>
                </div>
              </fieldset>

              <!-- Fieldset: Retries & Timing -->
              <fieldset class="border border-yellow-700 rounded p-3">
                <legend class="text-xs font-semibold text-yellow-400 px-2">Retries & Timing</legend>
                <div class="grid grid-cols-3 gap-3">
                  <div>
                    <Tooltip text="Number of retries on failure before giving up.">
                      <label class="block text-xs font-medium mb-1">Retry attempts</label>
                    </Tooltip>
                    <input v-model.number="form.retryAttempts" type="number"
                      :min="concurrencyLimits.retries.min" :max="concurrencyLimits.retries.max"
                      class="input w-full text-sm" :placeholder="concurrencyLimits.retries.default" />
                    <p class="text-xs text-gray-400 mt-1">max {{ concurrencyLimits.retries.max }}</p>
                  </div>
                  <div>
                    <Tooltip text="Exponential backoff multiplier between retries. 2.0 → 2s, 4s, 8s...">
                      <label class="block text-xs font-medium mb-1">Backoff factor</label>
                    </Tooltip>
                    <input v-model.number="form.retryBackoffFactor" type="number"
                      :min="concurrencyLimits.backoff.min" :max="concurrencyLimits.backoff.max" :step="concurrencyLimits.backoff.step"
                      class="input w-full text-sm" :placeholder="concurrencyLimits.backoff.default" />
                    <p class="text-xs text-gray-400 mt-1">max {{ concurrencyLimits.backoff.max }}</p>
                  </div>
                  <div>
                    <Tooltip text="Fixed delay in ms between consecutive requests.">
                      <label class="block text-xs font-medium mb-1">Request delay (ms)</label>
                    </Tooltip>
                    <input v-model.number="form.requestDelayMs" type="number"
                      :min="concurrencyLimits.delay.min" :max="concurrencyLimits.delay.max"
                      class="input w-full text-sm" :placeholder="concurrencyLimits.delay.default" />
                    <p class="text-xs text-gray-400 mt-1">0 = no delay · max {{ concurrencyLimits.delay.max }}ms</p>
                  </div>
                </div>
              </fieldset>

            </div>

            <!-- Tab Content: Outputs (Derived Datasets) -->
            <div v-if="activeParamTab === 'outputs'" class="h-[400px] overflow-y-auto pr-2 space-y-3">
              <p class="text-xs text-gray-400">
                Define catalog datasets extracted as a side-product of this resource's execution.
                Each config specifies a <strong class="text-gray-300">natural key</strong> and the fields to collect.
              </p>

              <!-- Existing configs table -->
              <div v-if="derivedConfigsLoading" class="text-center text-gray-500 py-4 text-xs">Loading...</div>
              <div v-else>
                <table v-if="derivedConfigs.length > 0" class="w-full text-xs mb-3">
                  <thead>
                    <tr class="border-b border-gray-700 text-gray-400">
                      <th class="text-left py-1.5 pr-2">Target</th>
                      <th class="text-left py-1.5 pr-2">Key field</th>
                      <th class="text-left py-1.5 pr-2">Extract fields</th>
                      <th class="text-left py-1.5 pr-2">Strategy</th>
                      <th class="text-center py-1.5 pr-2">Entries</th>
                      <th class="text-center py-1.5 pr-2">On</th>
                      <th class="py-1.5"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="cfg in derivedConfigs" :key="cfg.id" class="border-b border-gray-800 hover:bg-gray-750">
                      <!-- View mode -->
                      <template v-if="editingDerivedId !== cfg.id">
                        <td class="py-1.5 pr-2 font-mono text-green-300">{{ cfg.targetName }}</td>
                        <td class="py-1.5 pr-2 font-mono text-yellow-300">{{ cfg.keyField }}</td>
                        <td class="py-1.5 pr-2 text-gray-300">{{ (cfg.extractFields || []).join(', ') || '—' }}</td>
                        <td class="py-1.5 pr-2">
                          <span :class="cfg.mergeStrategy === 'upsert' ? 'text-blue-300' : 'text-orange-300'">{{ cfg.mergeStrategy }}</span>
                        </td>
                        <td class="py-1.5 pr-2 text-center text-gray-400">{{ cfg.entryCount ?? '—' }}</td>
                        <td class="py-1.5 pr-2 text-center">
                          <input type="checkbox" :checked="cfg.enabled"
                            @change="toggleDerived(cfg)"
                            class="accent-green-400 cursor-pointer" />
                        </td>
                        <td class="py-1.5 whitespace-nowrap flex gap-1">
                          <button type="button" @click="startEditDerived(cfg)"
                            class="text-blue-400 hover:text-blue-300 text-xs px-1">Edit</button>
                          <button type="button" @click="deleteDerived(cfg.id)"
                            class="text-red-400 hover:text-red-300 text-xs px-1">✕</button>
                        </td>
                      </template>
                      <!-- Inline edit mode -->
                      <template v-else>
                        <td class="py-1 pr-1">
                          <input v-model="editingDerivedData.targetName" class="input w-full text-xs py-0.5" placeholder="beneficiarios" />
                        </td>
                        <td class="py-1 pr-1">
                          <input v-model="editingDerivedData.keyField" class="input w-full text-xs py-0.5" placeholder="nif" />
                        </td>
                        <td class="py-1 pr-1">
                          <input v-model="editingDerivedData.extractFieldsText" class="input w-full text-xs py-0.5" placeholder="nombre,municipio" />
                        </td>
                        <td class="py-1 pr-1">
                          <select v-model="editingDerivedData.mergeStrategy" class="input text-xs py-0.5">
                            <option value="upsert">upsert</option>
                            <option value="insert_only">insert_only</option>
                          </select>
                        </td>
                        <td class="py-1 pr-1 text-center text-gray-500">{{ cfg.entryCount ?? '—' }}</td>
                        <td class="py-1 pr-1 text-center">
                          <input type="checkbox" v-model="editingDerivedData.enabled" class="accent-green-400" />
                        </td>
                        <td class="py-1 whitespace-nowrap flex gap-1">
                          <button type="button" @click="saveEditDerived(cfg.id)"
                            class="text-green-400 hover:text-green-300 text-xs px-1">Save</button>
                          <button type="button" @click="editingDerivedId = null"
                            class="text-gray-400 hover:text-gray-300 text-xs px-1">✕</button>
                        </td>
                      </template>
                    </tr>
                  </tbody>
                </table>
                <p v-else-if="!showAddDerivedForm" class="text-xs text-gray-500 py-2">
                  No derived datasets configured.
                </p>

                <!-- Add new config form -->
                <div v-if="showAddDerivedForm" class="border border-green-800 rounded p-3 bg-green-950 bg-opacity-20 space-y-2">
                  <h4 class="text-xs font-semibold text-green-400">New derived dataset</h4>
                  <div class="grid grid-cols-2 gap-2">
                    <div>
                      <label class="block text-xs text-gray-400 mb-0.5">Target name <span class="text-red-400">*</span></label>
                      <input v-model="newDerivedConfig.targetName" class="input w-full text-xs" placeholder="beneficiarios" />
                    </div>
                    <div>
                      <label class="block text-xs text-gray-400 mb-0.5">Key field <span class="text-red-400">*</span></label>
                      <input v-model="newDerivedConfig.keyField" class="input w-full text-xs" placeholder="nif" />
                    </div>
                  </div>
                  <div>
                    <label class="block text-xs text-gray-400 mb-0.5">Extract fields (comma-separated)</label>
                    <input v-model="newDerivedConfig.extractFieldsText" class="input w-full text-xs" placeholder="nombre, municipio, provincia" />
                  </div>
                  <div class="flex gap-4 items-center">
                    <div>
                      <label class="block text-xs text-gray-400 mb-0.5">Strategy</label>
                      <select v-model="newDerivedConfig.mergeStrategy" class="input text-xs py-1">
                        <option value="upsert">upsert (overwrite)</option>
                        <option value="insert_only">insert_only (keep existing)</option>
                      </select>
                    </div>
                    <div class="flex items-center gap-1.5 mt-4">
                      <input type="checkbox" v-model="newDerivedConfig.enabled" class="accent-green-400" id="new-derived-enabled" />
                      <label for="new-derived-enabled" class="text-xs text-gray-400">Enabled</label>
                    </div>
                  </div>
                  <div>
                    <label class="block text-xs text-gray-400 mb-0.5">Description (optional)</label>
                    <input v-model="newDerivedConfig.description" class="input w-full text-xs" placeholder="NIF + name from concesiones" />
                  </div>
                  <div class="flex gap-2 justify-end">
                    <button type="button" @click="showAddDerivedForm = false" class="btn btn-secondary text-xs py-1">Cancel</button>
                    <button type="button" @click="addDerived" class="btn btn-primary text-xs py-1">Add</button>
                  </div>
                </div>

                <button v-if="!showAddDerivedForm" type="button" @click="showAddDerivedForm = true"
                  class="text-xs text-green-400 hover:text-green-300 border border-green-800 rounded px-3 py-1 mt-1">
                  + Add derived dataset
                </button>
              </div>
            </div>

          </div>

          <div class="flex items-center">
            <input
              v-model="form.active"
              type="checkbox"
              id="active"
              class="mr-2"
            />
            <Tooltip :text="getTooltip('active')">
              <label for="active" class="text-xs cursor-pointer">Active</label>
            </Tooltip>
          </div>

          <div class="flex justify-end space-x-2 pt-3 border-t border-gray-700">
            <button type="button" @click="testResource" class="btn btn-secondary text-sm">
              Test
            </button>

            <button type="button" @click="closeModals" class="btn btn-secondary text-sm">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary text-sm">
              {{ showCreateModal ? 'Create' : 'Update' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Delete Confirmation Modal -->
    <div
      v-if="showDeleteModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showDeleteModal = false"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-2xl font-bold mb-4">Confirm Delete</h2>
        <p class="mb-6">
          Are you sure you want to delete resource "{{ resourceToDelete?.name }}"?
        </p>
        <div class="flex justify-end space-x-2">
          <button @click="showDeleteModal = false" class="btn btn-secondary">
            Cancel
          </button>
          <button @click="handleDelete" class="btn btn-danger">
            Delete
          </button>
        </div>
      </div>
    </div>

    <PreviewDataModal :previewResource="previewResource" :loadingPreview="loadingPreview" :previewError="previewError" :previewData="previewData" :getRecordCount="getRecordCount" v-model:showPreviewModal="showPreviewModal" />

    <!-- Overpass Query Builder Modal -->
    <OverpassQueryModal
      v-if="overpassModalParam"
      :modelValue="getParamValue(overpassModalParam)"
      :presets="getOverpassPresets(overpassModalParam)"
      :demarcacion="getParamValue('demarcacion') || 'España'"
      :elementTypes="getParamValue('element_types') || 'node,way'"
      :timeout="getParamValue('timeout') || 60"
      :outFormat="getParamValue('out_format') || 'center'"
      @update:modelValue="updateParamValue(overpassModalParam, $event)"
      @close="closeOverpassModal"
    />

    <!-- Execute Modal -->
    <div
      v-if="showExecuteModal"
      class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
      @click.self="showExecuteModal = false"
    >
      <div class="bg-gray-800 rounded-lg p-6 w-full max-w-md">
        <h2 class="text-xl font-bold mb-1">Run Resource</h2>
        <p class="text-sm text-gray-400 mb-4">{{ executingResource?.name }}</p>

        <!-- Runtime params form -->
        <div v-if="executingResource?.params?.filter(p => p.isExternal).length" class="space-y-3 mb-4">
          <p class="text-xs text-gray-500">Override runtime parameters — leave blank to use the stored default.</p>
          <div
            v-for="param in executingResource.params.filter(p => p.isExternal)"
            :key="param.key"
            class="space-y-1"
          >
            <div class="flex items-baseline justify-between">
              <label class="text-xs font-semibold text-yellow-300">{{ param.key }}</label>
              <span v-if="param.value" class="text-xs text-gray-500">default: {{ param.value }}</span>
            </div>
            <input
              v-model="executeParams[param.key]"
              type="text"
              :placeholder="param.value ? `Leave blank to use '${param.value}'` : `Enter ${param.key}...`"
              class="input w-full text-sm"
            />
          </div>
        </div>
        <p v-else class="text-sm text-gray-400 mb-4">
          No runtime parameters. The resource will run with its saved configuration.
        </p>

        <div class="flex justify-end gap-2">
          <button @click="showExecuteModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="confirmExecute" class="btn btn-primary">Run</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import Tooltip from '../components/Tooltip.vue'
import FilterMapEditor from '../components/FilterMapEditor.vue'
import EnumMetaPreview from '../components/EnumMetaPreview.vue'
import EnumRadioGroup from '../components/EnumRadioGroup.vue'
import OverpassQueryModal from '../components/OverpassQueryModal.vue'
import {
  fetchResources,
  fetchResourceExecutions,
  fetchFetchers,
  fetchFieldMetadata,
  createResource,
  updateResource,
  deleteResource,
  cloneResource,
  previewResourceData,
  executeResource,
  fetchAppConfig,
  fetchDerivedDatasetConfigs,
  createDerivedDatasetConfig,
  updateDerivedDatasetConfig,
  deleteDerivedDatasetConfig,
  toggleDerivedDatasetConfig,
  fetchPublishers,
} from '../api/graphql'
import PreviewDataModal from './PreviewDataModal.vue'

// ── Refs para medición de altura dinámica ─────────────────────────────────────
const viewEl    = ref(null)
const filterEl  = ref(null)
const paginEl   = ref(null)

const ROW_H        = 33   // px estimado por fila (py-1.5 + text-xs)
const THEAD_H      = 33   // cabecera de tabla
const autoPageSize = ref(15)
const pageSizeOverride = ref(0)   // 0 = usar auto
const pageSize = computed(() => pageSizeOverride.value || autoPageSize.value)

function recalcPageSize() {
  if (!filterEl.value) return
  const winH    = window.innerHeight
  const cardTop = filterEl.value.closest('.card')?.getBoundingClientRect().top ?? 120
  const filterH = filterEl.value.clientHeight
  const paginH  = paginEl.value?.clientHeight ?? 36
  const available = winH - cardTop - filterH - THEAD_H - paginH - 16
  autoPageSize.value = Math.max(5, Math.floor(available / ROW_H))
}

let _ro = null

const resources = ref([])
const fetchers = ref([])
const publishers = ref([])
const fieldMetadata = ref({}) // Metadata for tooltips
const appConfig = ref({})  // key→value map
const sysInfo   = ref(null)

// Limits derived from settings + hardware — used in the concurrency inputs
const concurrencyLimits = computed(() => {
  const ram  = sysInfo.value?.ram_total_gb  ?? 4
  const ramMb = sysInfo.value?.ram_total_mb ?? 4096
  const cpu  = sysInfo.value?.cpu_logical   ?? 2
  const maxProc = appConfig.value['max_concurrent_processes'] ?? 3
  const defPageSize = appConfig.value['default_page_size'] ?? 100

  return {
    // Workers: bounded by global max_concurrent_processes and hardware
    workers:    { min: 1, max: Math.min(maxProc, cpu * 2), default: 1 },
    // Concurrent HTTP requests: independent of process limit but bounded by CPU
    concReqs:   { min: 1, max: Math.min(50, cpu * 10), default: 5 },
    // Rate limit: pure API concern, no hardware constraint
    rateLimit:  { min: 1, max: 200, default: 10 },
    // Batch size: bounded by default_page_size setting and RAM
    batchSize:  { min: 1, max: Math.min(5000, Math.floor(ramMb / 5)), default: defPageSize },
    // Retries: fixed sensible range
    retries:    { min: 0, max: 10, default: 3 },
    backoff:    { min: 1, max: 5,  default: 2, step: 0.1 },
    delay:      { min: 0, max: 30000, default: 0 },
  }
})
const loading = ref(true)
const error = ref(null)
const searchQuery = ref('')
const currentPage = ref(1)

// Filter state
const selectedType      = ref('')
const selectedPublisher = ref('')
const selectedNivel     = ref('')
const filterAllStatuses = ref(true)
const filterStatuses    = ref([])

const availableTypes = computed(() =>
  [...new Set(resources.value.map(r => r.fetcher?.code).filter(Boolean))].sort()
)
// Publishers that actually appear in resources
const availablePublishers = computed(() => {
  const ids = new Set(resources.value.map(r => r.publisherId).filter(Boolean))
  return publishers.value.filter(p => ids.has(p.id))
})
const availableNiveles = computed(() =>
  [...new Set(availablePublishers.value.map(p => p.nivel).filter(Boolean))].sort()
)

function onAllStatuses() {
  if (filterAllStatuses.value) filterStatuses.value = []
}
function onStatusChange() {
  filterAllStatuses.value = filterStatuses.value.length === 0
}

const hasActiveFilters = computed(() =>
  !!(searchQuery.value || selectedType.value || selectedPublisher.value || selectedNivel.value || !filterAllStatuses.value)
)

function clearFilters() {
  searchQuery.value      = ''
  selectedType.value     = ''
  selectedPublisher.value = ''
  selectedNivel.value    = ''
  filterAllStatuses.value = true
  filterStatuses.value   = []
  currentPage.value      = 1
}

const showCreateModal = ref(false)
const showEditModal = ref(false)
const showDeleteModal = ref(false)
const showPreviewModal = ref(false)
const showExecuteModal = ref(false)
const resourceToDelete = ref(null)
const executingResource = ref(null)
const executeParams = ref({})
const executeLoading = ref(false)
const executeResult = ref(null)
const editingResource = ref(null)
const previewResource = ref(null)
const previewData = ref(null)
const loadingPreview = ref(false)
const previewError = ref(null)

const form = ref({
  name: '',
  publisherId: null,
  fetcherId: '',
  params: [],
  active: true,
  schedule: null,
  numWorkers: 1,
  maxConcurrentRequests: null,
  rateLimitPerSecond: null,
  requestDelayMs: null,
  retryAttempts: null,
  retryBackoffFactor: null,
  batchSize: null,
})

const activeParamTab = ref('parameters')

// Derived datasets state
const derivedConfigs = ref([])
const derivedConfigsLoading = ref(false)
const newDerivedConfig = ref({
  targetName: '',
  keyField: '',
  extractFieldsText: '',
  mergeStrategy: 'upsert',
  enabled: true,
  description: '',
})
const showAddDerivedForm = ref(false)
const editingDerivedId = ref(null)
const editingDerivedData = ref({})

// Computed property for selected fetcher
const selectedFetcher = computed(() => {
  if (!fetchers.value || fetchers.value.length === 0) return null
  return fetchers.value.find(type => type.id === form.value.fetcherId)
})

// Computed property for required parameters
const requiredParams = computed(() => {
  if (!selectedFetcher.value || !selectedFetcher.value.paramsDef) {
    return []
  }
  return selectedFetcher.value.paramsDef.filter(param => param.required === true)
})

// Computed property for optional parameters
const optionalParams = computed(() => {
  if (!selectedFetcher.value || !selectedFetcher.value.paramsDef) {
    return []
  }
  return selectedFetcher.value.paramsDef.filter(param => param.required !== true)
})

// Computed property for added optional parameters
const addedOptionalParams = computed(() => {
  const allRequired = requiredParams.value.map(p => p.paramName)
  return form.value.params
    .map(p => p.key)
    .filter(key => !allRequired.includes(key))
})

// Computed property for available optional parameters
const availableOptionalParams = computed(() => {
  const currentParamNames = form.value.params.map(p => p.key)
  return optionalParams.value.filter(param => !currentParamNames.includes(param.paramName))
})

// Computed property to filter resources based on search query and filters
const filteredResources = computed(() => {
  const q = searchQuery.value.toLowerCase()
  const list = resources.value.filter(r => {
    const pubName = r.publisherObj?.nombre || r.publisher || ''
    if (q && !r.name.toLowerCase().includes(q) && !pubName.toLowerCase().includes(q))
      return false
    if (selectedType.value && r.fetcher?.code !== selectedType.value)
      return false
    if (selectedPublisher.value && r.publisherId !== selectedPublisher.value)
      return false
    if (selectedNivel.value && r.publisherObj?.nivel !== selectedNivel.value)
      return false
    if (!filterAllStatuses.value && filterStatuses.value.length) {
      const status = r.active ? 'active' : 'inactive'
      if (!filterStatuses.value.includes(status)) return false
    }
    return true
  })
  return list.sort((a, b) => a.name.localeCompare(b.name, 'es'))
})

const totalPages = computed(() => Math.ceil(filteredResources.value.length / pageSize.value))

const pagedResources = computed(() => {
  const ps = pageSize.value
  const start = (currentPage.value - 1) * ps
  return filteredResources.value.slice(start, start + ps)
})

watch([searchQuery, selectedType, selectedPublisher, selectedNivel, filterStatuses, pageSize], () => { currentPage.value = 1 })

const selectedOptionalParam = ref('')

async function loadData() {
  try {
    loading.value = true
    error.value = null
    const [resourcesData, typesData, publishersData, resourceMetadata, paramMetadata, cfgData, infoData] = await Promise.all([
      fetchResources(false),
      fetchFetchers(),
      fetchPublishers(),
      fetchFieldMetadata('resource'),
      fetchFieldMetadata('resource_param'),
      fetchAppConfig(),
      fetch('/api/system/info').then(r => r.json()).catch(() => null),
    ])
    resources.value = resourcesData.resources
    fetchers.value = typesData.fetchers
    publishers.value = publishersData?.publishers || []

    // Organize metadata by field_name for easy lookup
    const metaMap = {}
    resourceMetadata.fieldMetadata.forEach(m => {
      metaMap[m.fieldName] = m
    })
    paramMetadata.fieldMetadata.forEach(m => {
      metaMap[m.fieldName] = m
    })
    fieldMetadata.value = metaMap

    // Build key→value map from appConfig array
    if (cfgData?.appConfig) {
      const map = {}
      cfgData.appConfig.forEach(c => { map[c.key] = c.value })
      appConfig.value = map
    }
    if (infoData) sysInfo.value = infoData
  } catch (e) {
    error.value = 'Failed to load data: ' + e.message
  } finally {
    loading.value = false
  }
}

// Helper to get tooltip text for a field
function getTooltip(fieldName) {
  return fieldMetadata.value[fieldName]?.helpText || ''
}

// Helper to get placeholder for a field
function getPlaceholder(fieldName) {
  return fieldMetadata.value[fieldName]?.placeholder || ''
}

// ── Helpers para enum con {value, label, group?} o string[] ─────────────────

/**
 * Normaliza enum_values a [{value, label, ...rest}] independientemente de si
 * es string[], {value,label}[] o {value,label,group,filters,...}[].
 */
function enumOpts(vals) {
  if (!vals) return []
  return vals.map(v => typeof v === 'string' ? { value: v, label: v } : v)
}

/**
 * Devuelve [{group, options[{value,label}]}] si los items tienen 'group',
 * o null si es una lista plana.
 */
function enumGroups(vals) {
  const opts = enumOpts(vals)
  if (!opts.length || !opts[0].group) return null
  const map = new Map()
  for (const opt of opts) {
    const g = opt.group || ''
    if (!map.has(g)) map.set(g, [])
    map.get(g).push(opt)
  }
  return Array.from(map.entries()).map(([group, options]) => ({ group, options }))
}

/**
 * Devuelve el campo extra de la opción seleccionada (p.ej. 'filters' del preset use_type).
 * Devuelve null si la opción no existe o no tiene ese campo.
 */
function selectedEnumMeta(paramName, enumValues, field) {
  const selected = getParamValue(paramName)
  if (!selected || !enumValues) return null
  const opt = enumOpts(enumValues).find(o => o.value === selected)
  return opt?.[field] ?? null
}

// Helper functions for parameters
function getParamValue(paramName) {
  const param = form.value.params.find(p => p.key === paramName)
  return param ? param.value : ''
}

function getParamType(paramName) {
  const param = optionalParams.value.find(p => p.paramName === paramName)
  return param ? param.dataType : 'string'
}

function getParamEnumValues(paramName) {
  const param = optionalParams.value.find(p => p.paramName === paramName)
  return param ? param.enumValues : null
}

function getOverpassPresets(paramName) {
  const req = requiredParams.value.find(p => p.paramName === paramName)
  if (req) return req.enumValues || {}
  return getParamEnumValues(paramName) || {}
}

/** Tipos de param que necesitan layout de ancho completo (sin flex-row). */
function isFullWidthParam(dataType) {
  return dataType === 'json_filter_map' || dataType === 'overpass_query'
}

/** Modal Overpass: qué param está siendo editado (null = cerrada). */
const overpassModalParam = ref(null)

function openOverpassModal(paramName) {
  overpassModalParam.value = paramName
}
function closeOverpassModal() {
  overpassModalParam.value = null
}

/**
 * Muestra un resumen legible del valor almacenado en un param overpass_query.
 * El valor es un JSON array de bloques: [{preset, pairs, mode}].
 */
function overpassSummary(paramName) {
  const raw = getParamValue(paramName)
  if (!raw) return 'sin condiciones'
  try {
    const blocks = JSON.parse(raw)
    if (!Array.isArray(blocks) || !blocks.length) return 'sin condiciones'
    const labels = blocks.map(b => b.preset || `(${b.pairs?.length || 0} pares)`)
    return labels.join(' + ')
  } catch {
    return raw.slice(0, 60)
  }
}

function getParamDefaultValue(paramName) {
  // Check required params first
  const requiredParam = requiredParams.value.find(p => p.paramName === paramName)
  if (requiredParam && requiredParam.defaultValue) {
    return requiredParam.defaultValue
  }

  // Then check optional params
  const optionalParam = optionalParams.value.find(p => p.paramName === paramName)
  if (optionalParam && optionalParam.defaultValue) {
    return optionalParam.defaultValue
  }

  return null
}

function updateParamValue(paramName, value) {
  const param = form.value.params.find(p => p.key === paramName)
  if (param) {
    param.value = value
  } else {
    form.value.params.push({ key: paramName, value, isExternal: false })
  }
}

function toggleParamExternal(paramName) {
  const param = form.value.params.find(p => p.key === paramName)
  if (param) param.isExternal = !param.isExternal
}

function addOptionalParameter() {
  if (!selectedOptionalParam.value) return

  const paramName = selectedOptionalParam.value
  const existingParam = form.value.params.find(p => p.key === paramName)

  if (!existingParam) {
    const defaultValue = getParamDefaultValue(paramName) || ''
    form.value.params.push({ key: paramName, value: defaultValue, isExternal: false })
  }

  selectedOptionalParam.value = ''
}

function removeOptionalParam(paramName) {
  const index = form.value.params.findIndex(p => p.key === paramName)
  if (index !== -1) {
    form.value.params.splice(index, 1)
  }
}

function editResource(resource) {
  editingResource.value = resource

  // Helper to extract concurrency params
  const getParam = (key, defaultValue = null) => {
    const param = resource.params.find(p => p.key === key)
    return param ? (defaultValue === null ? param.value : parseInt(param.value)) : defaultValue
  }

  // Extract concurrency parameters
  const concurrencyKeys = [
    'num_workers',
    'max_concurrent_requests',
    'rate_limit_per_second',
    'request_delay_ms',
    'retry_attempts',
    'retry_backoff_factor',
    'batch_size'
  ]

  // Filter out concurrency params from regular params
  const regularParams = resource.params.filter(p => !concurrencyKeys.includes(p.key))

  form.value = {
    name: resource.name,
    publisherId: resource.publisherId || null,
    fetcherId: resource.fetcher.id,
    params: regularParams.map(p => ({ key: p.key, value: p.value, isExternal: p.isExternal || false })),
    active: resource.active,
    schedule: resource.schedule || null,
    numWorkers: parseInt(getParam('num_workers', 1)),
    maxConcurrentRequests: getParam('max_concurrent_requests') ? parseInt(getParam('max_concurrent_requests')) : null,
    rateLimitPerSecond: getParam('rate_limit_per_second') ? parseInt(getParam('rate_limit_per_second')) : null,
    requestDelayMs: getParam('request_delay_ms') ? parseInt(getParam('request_delay_ms')) : null,
    retryAttempts: getParam('retry_attempts') ? parseInt(getParam('retry_attempts')) : null,
    retryBackoffFactor: getParam('retry_backoff_factor') ? parseFloat(getParam('retry_backoff_factor')) : null,
    batchSize: getParam('batch_size') ? parseInt(getParam('batch_size')) : null,
  }
  showEditModal.value = true
  loadDerivedConfigs(resource.id)
}

function testResource() {
  if (editingResource.value) {
    showPreviewData(editingResource.value)
  }
}

async function showPreviewData(resource) {
  previewResource.value = resource
  previewData.value = null
  previewError.value = null
  showPreviewModal.value = true
  loadingPreview.value = true

  try {
    const result = await previewResourceData(resource.id, 100)
    previewData.value = result.previewResourceData
  } catch (e) {
    previewError.value = 'Failed to load preview data: ' + e.message
  } finally {
    loadingPreview.value = false
  }
}

function getRecordCount(data) {
  if (!data) return 0

  // If it's an array, check if first element has a 'content' array
  if (Array.isArray(data)) {
    if (data.length > 0 && data[0].content && Array.isArray(data[0].content)) {
      return data[0].content.length
    }
    return data.length
  }

  // If it's an object with a 'content' array property
  if (typeof data === 'object' && data.content && Array.isArray(data.content)) {
    return data.content.length
  }

  // Regular object
  if (typeof data === 'object') return Object.keys(data).length > 0 ? 1 : 0

  return 1
}

function openExecuteModal(resource) {
  executingResource.value = resource
  executeResult.value = null
  executeParams.value = {}   // start empty — user fills only what they want to override
  showExecuteModal.value = true
}

async function confirmExecute() {
  // Only send params the user explicitly typed (non-empty strings)
  const overrides = Object.fromEntries(
    Object.entries(executeParams.value).filter(([, v]) => v !== '' && v !== null && v !== undefined)
  )
  const externalParams = Object.keys(overrides).length > 0 ? overrides : null
  showExecuteModal.value = false
  executeResource(executingResource.value.id, externalParams).catch(() => {})
}

function confirmDelete(resource) {
  resourceToDelete.value = resource
  showDeleteModal.value = true
}

async function handleClone(resource) {
  try {
    const result = await cloneResource(resource.id)
    if (result?.cloneResource) {
      await loadResources()
    }
  } catch (error) {
    console.error('Error cloning resource:', error)
  }
}

async function handleDelete() {
  try {
    await deleteResource(resourceToDelete.value.id)
    showDeleteModal.value = false
    resourceToDelete.value = null
    await loadData()
  } catch (e) {
    error.value = 'Failed to delete resource: ' + e.message
  }
}

async function submitForm() {
  try {
    error.value = null

    // Combine regular params with concurrency params
    const allParams = [...form.value.params.filter(p => p.key && p.value).map(p => ({
      key: p.key, value: p.value, isExternal: p.isExternal || false
    }))]

    // Add concurrency params if not default/null
    const concurrencyParams = {
      'num_workers': { value: form.value.numWorkers, default: 1 },
      'max_concurrent_requests': { value: form.value.maxConcurrentRequests, default: null },
      'rate_limit_per_second': { value: form.value.rateLimitPerSecond, default: null },
      'request_delay_ms': { value: form.value.requestDelayMs, default: null },
      'retry_attempts': { value: form.value.retryAttempts, default: null },
      'retry_backoff_factor': { value: form.value.retryBackoffFactor, default: null },
      'batch_size': { value: form.value.batchSize, default: null },
    }

    for (const [key, config] of Object.entries(concurrencyParams)) {
      const value = config.value
      const defaultValue = config.default

      if (value !== null && value !== defaultValue) {
        allParams.push({ key, value: String(value) })
      }
    }

    const input = {
      name: form.value.name,
      publisherId: form.value.publisherId || null,
      fetcherId: form.value.fetcherId,
      params: allParams,
      active: form.value.active,
      schedule: form.value.schedule || null,
    }

    if (showCreateModal.value) {
      await createResource(input)
    } else {
      await updateResource(editingResource.value.id, input)
    }

    closeModals()
    await loadData()
  } catch (e) {
    error.value = 'Failed to save resource: ' + e.message
  }
}

function closeModals() {
  showCreateModal.value = false
  showEditModal.value = false
  editingResource.value = null
  activeParamTab.value = 'parameters'
  derivedConfigs.value = []
  showAddDerivedForm.value = false
  editingDerivedId.value = null
  form.value = {
    name: '',
    publisher: '',
    fetcherId: '',
    params: [],
    active: true,
    schedule: null,
    numWorkers: 1,
    maxConcurrentRequests: null,
    rateLimitPerSecond: null,
    requestDelayMs: null,
    retryAttempts: null,
    retryBackoffFactor: null,
    batchSize: null,
  }
}

// ── Derived datasets ─────────────────────────────────────────────────────────

async function loadDerivedConfigs(resourceId) {
  derivedConfigsLoading.value = true
  try {
    const result = await fetchDerivedDatasetConfigs(resourceId)
    derivedConfigs.value = result?.derivedDatasetConfigs || []
  } catch (e) {
    // silently ignore — not critical
  } finally {
    derivedConfigsLoading.value = false
  }
}

function parseFields(text) {
  return (text || '').split(',').map(s => s.trim()).filter(Boolean)
}

async function addDerived() {
  const cfg = newDerivedConfig.value
  if (!cfg.targetName || !cfg.keyField) return
  try {
    await createDerivedDatasetConfig({
      sourceResourceId: editingResource.value.id,
      targetName: cfg.targetName,
      keyField: cfg.keyField,
      extractFields: parseFields(cfg.extractFieldsText),
      mergeStrategy: cfg.mergeStrategy,
      enabled: cfg.enabled,
      description: cfg.description || null,
    })
    newDerivedConfig.value = { targetName: '', keyField: '', extractFieldsText: '', mergeStrategy: 'upsert', enabled: true, description: '' }
    showAddDerivedForm.value = false
    await loadDerivedConfigs(editingResource.value.id)
  } catch (e) {
    error.value = 'Failed to add derived dataset: ' + e.message
  }
}

async function deleteDerived(id) {
  try {
    await deleteDerivedDatasetConfig(id)
    await loadDerivedConfigs(editingResource.value.id)
  } catch (e) {
    error.value = 'Failed to delete: ' + e.message
  }
}

async function toggleDerived(cfg) {
  try {
    const result = await toggleDerivedDatasetConfig(cfg.id, !cfg.enabled)
    const updated = result?.toggleDerivedDatasetConfig
    if (updated) {
      const idx = derivedConfigs.value.findIndex(c => c.id === cfg.id)
      if (idx !== -1) derivedConfigs.value[idx] = { ...derivedConfigs.value[idx], ...updated }
    }
  } catch (e) {
    error.value = 'Failed to toggle: ' + e.message
  }
}

function startEditDerived(cfg) {
  editingDerivedId.value = cfg.id
  editingDerivedData.value = {
    targetName: cfg.targetName,
    keyField: cfg.keyField,
    extractFieldsText: (cfg.extractFields || []).join(', '),
    mergeStrategy: cfg.mergeStrategy,
    enabled: cfg.enabled,
    description: cfg.description || '',
  }
}

async function saveEditDerived(id) {
  const d = editingDerivedData.value
  try {
    await updateDerivedDatasetConfig(id, {
      targetName: d.targetName,
      keyField: d.keyField,
      extractFields: parseFields(d.extractFieldsText),
      mergeStrategy: d.mergeStrategy,
      enabled: d.enabled,
      description: d.description || null,
    })
    editingDerivedId.value = null
    await loadDerivedConfigs(editingResource.value.id)
  } catch (e) {
    error.value = 'Failed to update: ' + e.message
  }
}

const runningResourceIds = ref(new Set())
let runningPollTimer = null

async function pollRunning() {
  try {
    const data = await fetchResourceExecutions()
    const ids = new Set(
      (data?.resourceExecutions ?? [])
        .filter(e => e.status === 'running')
        .map(e => e.resourceId)
    )
    runningResourceIds.value = ids
  } catch {}
}

onMounted(() => {
  loadData()
  pollRunning()
  runningPollTimer = setInterval(pollRunning, 5000)

  // Cálculo dinámico de filas por página
  _ro = new ResizeObserver(recalcPageSize)
  // Observamos el filterEl cuando esté disponible (nextTick por si acaso)
  setTimeout(() => {
    if (filterEl.value) _ro.observe(filterEl.value)
    recalcPageSize()
  }, 100)
  window.addEventListener('resize', recalcPageSize)
})

onUnmounted(() => {
  clearInterval(runningPollTimer)
  _ro?.disconnect()
  window.removeEventListener('resize', recalcPageSize)
})
</script>
