<template>
  <div class="fixed inset-0 bg-black bg-opacity-60 flex items-start justify-center z-50 p-4 pt-16 overflow-y-auto"
       @click.self="$emit('close')">
    <div class="bg-gray-800 rounded-lg w-full max-w-4xl border border-gray-700 shadow-2xl">

      <!-- Header -->
      <div class="flex justify-between items-center px-6 py-4 border-b border-gray-700">
        <div>
          <h2 class="text-xl font-bold">Discover Sections</h2>
          <p class="text-sm text-gray-400 mt-0.5">{{ resourceName }}</p>
        </div>
        <button @click="$emit('close')" class="text-gray-400 hover:text-white text-2xl leading-none">&times;</button>
      </div>

      <!-- Body -->
      <div class="p-6">

        <!-- State: no artifact yet -->
        <div v-if="state === 'idle'" class="text-center py-10">
          <p class="text-gray-400 mb-4">No discover run found for this resource.</p>
          <button @click="runDiscover" class="btn btn-primary">Run Discovery</button>
        </div>

        <!-- State: running -->
        <div v-else-if="state === 'running'" class="text-center py-10">
          <div class="inline-block w-8 h-8 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mb-4"></div>
          <p class="text-gray-300">Discovery in progress…</p>
          <p class="text-xs text-gray-500 mt-1">Crawling the portal without downloading files</p>
        </div>

        <!-- State: error -->
        <div v-else-if="state === 'error'" class="py-6">
          <div class="bg-red-900 border border-red-700 rounded p-4 text-red-200 mb-4">{{ errorMsg }}</div>
          <button @click="runDiscover" class="btn btn-primary">Retry</button>
        </div>

        <!-- State: sections loaded -->
        <div v-else-if="state === 'done'">
          <div class="flex justify-between items-center mb-4">
            <p class="text-sm text-gray-400">
              {{ sections.length }} section{{ sections.length !== 1 ? 's' : '' }} discovered.
              Check the ones you want to create as child resources.
            </p>
            <div class="flex gap-2">
              <button @click="selectAll(true)" class="text-xs text-purple-400 hover:text-purple-300">Select all</button>
              <span class="text-gray-600">|</span>
              <button @click="selectAll(false)" class="text-xs text-gray-400 hover:text-gray-300">Deselect all</button>
              <span class="text-gray-600">|</span>
              <button @click="runDiscover" class="text-xs text-gray-400 hover:text-gray-300">Re-run</button>
            </div>
          </div>

          <div class="space-y-3 max-h-[55vh] overflow-y-auto pr-1">
            <div
              v-for="(sec, i) in sections" :key="i"
              class="border rounded-lg p-4 transition-colors"
              :class="sec.selected ? 'border-purple-600 bg-gray-750' : 'border-gray-700 bg-gray-800'"
            >
              <div class="flex items-start gap-3">
                <input type="checkbox" v-model="sec.selected" class="accent-purple-500 mt-1 flex-shrink-0" />
                <div class="flex-1 min-w-0">
                  <!-- Name (editable) -->
                  <input
                    v-model="sec.name"
                    class="input text-sm w-full mb-2 font-medium"
                    placeholder="Resource name…"
                  />
                  <!-- target_table (editable) -->
                  <input
                    v-model="sec.targetTable"
                    class="input text-xs font-mono w-full mb-2 text-gray-400"
                    placeholder="target_table (snake_case)"
                  />
                  <!-- Meta -->
                  <div class="flex flex-wrap gap-3 text-xs text-gray-500">
                    <span>{{ sec.page_count }} page{{ sec.page_count !== 1 ? 's' : '' }}</span>
                    <span>{{ sec.total_file_count }} file{{ sec.total_file_count !== 1 ? 's' : '' }}</span>
                    <span v-for="ext in sec.extensions" :key="ext"
                          class="px-1.5 py-0.5 rounded bg-gray-700 text-gray-300 font-mono uppercase">{{ ext }}</span>
                  </div>
                  <!-- URL pattern -->
                  <p class="text-xs font-mono text-gray-600 mt-1 truncate" :title="sec.url_pattern">{{ sec.url_pattern }}</p>
                  <!-- Sample files -->
                  <div v-if="sec.sample_files?.length" class="mt-2">
                    <p v-for="f in sec.sample_files.slice(0,2)" :key="f.url"
                       class="text-xs text-gray-600 truncate" :title="f.url">
                      {{ f.anchor || f.url }}
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="errorMsg" class="bg-red-900 border border-red-700 rounded p-3 text-red-200 text-sm mb-4">{{ errorMsg }}</div>

          <div class="flex justify-end gap-3 mt-6">
            <button @click="$emit('close')" class="btn btn-secondary">Cancel</button>
            <button
              @click="createResources"
              :disabled="creating || selectedCount === 0"
              class="btn btn-primary"
              :class="creating || selectedCount === 0 ? 'opacity-50 cursor-not-allowed' : ''"
            >
              <span v-if="creating">Creating…</span>
              <span v-else>Create {{ selectedCount }} resource{{ selectedCount !== 1 ? 's' : '' }}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { fetchDiscoverArtifact, createChildResources } from '../api/graphql'

const props = defineProps({
  resourceId: { type: String, required: true },
  resourceName: { type: String, required: true },
  fetcherCode: { type: String, default: '' },
})
const emit = defineEmits(['close', 'created'])

const state = ref('idle')   // idle | running | done | error
const sections = ref([])
const errorMsg = ref('')
const creating = ref(false)

const selectedCount = computed(() => sections.value.filter(s => s.selected).length)

function selectAll(val) {
  sections.value.forEach(s => { s.selected = val })
}

function nameToTable(name) {
  return name.toLowerCase()
    .replace(/[^a-z0-9\s_]/g, '')
    .trim()
    .replace(/\s+/g, '_')
    .substring(0, 60)
}

function loadArtifact(json) {
  const raw = JSON.parse(json)
  sections.value = raw.map(s => ({
    ...s,
    selected: true,
    name: props.resourceName + ' — ' + s.suggested_name,
    targetTable: nameToTable(s.suggested_name),
  }))
  state.value = 'done'
}

async function runDiscover() {
  state.value = 'running'
  errorMsg.value = ''
  try {
    // Trigger a discover execution using existing executeResource with _discover_mode flag
    const { executeResource } = await import('../api/graphql')
    const res = await executeResource(props.resourceId, { _discover_mode: true })
    if (!res?.executeResource?.success) {
      throw new Error(res?.executeResource?.message || 'Failed to start discover')
    }
    // Poll until the execution completes (discover is fast — no file downloads)
    await pollUntilDone()
  } catch (e) {
    state.value = 'error'
    errorMsg.value = e.message || String(e)
  }
}

async function pollUntilDone() {
  const MAX_POLLS = 120   // 2 min at 1s intervals
  for (let i = 0; i < MAX_POLLS; i++) {
    await new Promise(r => setTimeout(r, 2000))
    const res = await fetchDiscoverArtifact(props.resourceId)
    if (res?.discoverArtifact) {
      loadArtifact(res.discoverArtifact)
      return
    }
  }
  throw new Error('Discovery timed out — check the execution log')
}

async function createResources() {
  creating.value = true
  try {
    const approved = sections.value.filter(s => s.selected)
    const input = approved.map(s => ({
      urlPattern: s.url_pattern,
      name: s.name,
      targetTable: s.targetTable,
      pageIncludePatterns: JSON.stringify(s.suggested_page_include_patterns || []),
      extensions: s.extensions,
    }))
    const res = await createChildResources(props.resourceId, input)
    const created = res?.createChildResources || []
    emit('created', created)
    emit('close')
  } catch (e) {
    errorMsg.value = e.message || String(e)
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  // Check if a discover artifact already exists
  try {
    const res = await fetchDiscoverArtifact(props.resourceId)
    if (res?.discoverArtifact) {
      loadArtifact(res.discoverArtifact)
    }
  } catch (_) {}
})
</script>
