<template>
  <!-- Inline (≤4 opciones) o grid 2 cols (>4) -->
  <div
    class="flex flex-wrap gap-x-4 gap-y-1.5"
    :class="cols > 1 ? 'grid grid-cols-2' : ''"
  >
    <label
      v-for="opt in normalizedOpts"
      :key="opt.value"
      class="flex items-center gap-1.5 cursor-pointer group"
      :title="opt.value !== opt.label ? opt.value : ''"
    >
      <input
        type="radio"
        :name="name"
        :value="opt.value"
        :checked="modelValue === opt.value"
        @change="$emit('update:modelValue', opt.value)"
        class="accent-blue-500 cursor-pointer flex-shrink-0"
      />
      <span class="text-xs text-gray-200 group-hover:text-white leading-tight">
        {{ opt.label }}
      </span>
    </label>

    <!-- Opción "ninguno" si el param no es required -->
    <label v-if="clearable" class="flex items-center gap-1.5 cursor-pointer group">
      <input
        type="radio"
        :name="name"
        value=""
        :checked="!modelValue"
        @change="$emit('update:modelValue', '')"
        class="accent-gray-500 cursor-pointer flex-shrink-0"
      />
      <span class="text-xs text-gray-500 italic group-hover:text-gray-400">ninguno</span>
    </label>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: { type: String, default: '' },
  options:    { type: Array,  required: true },   // string[] o {value,label}[]
  name:       { type: String, default: () => `rg-${Math.random().toString(36).slice(2)}` },
  clearable:  { type: Boolean, default: false },
})
defineEmits(['update:modelValue'])

const normalizedOpts = computed(() =>
  props.options.map(o => typeof o === 'string' ? { value: o, label: o } : o)
)

// Grid 2 cols cuando hay más de 4 opciones
const cols = computed(() => normalizedOpts.value.length > 4 ? 2 : 1)
</script>
