<template>
  <div :class="['view', { 'view--fill': fill }]">
    <div class="view__inner" :style="maxWidth ? { maxWidth, margin: '0 auto', width: '100%' } : undefined">
      <PageHeader :title="title" :subtitle="subtitle" :tight="fill">
        <template v-if="$slots.subtitle" #subtitle><slot name="subtitle" /></template>
        <template v-if="$slots.actions" #actions><slot name="actions" /></template>
      </PageHeader>
      <div :class="['view__body', bodyClass, { 'view__body--fill': fill }]"><slot /></div>
    </div>
  </div>
</template>

<script setup>
import PageHeader from './PageHeader.vue'
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  fill: { type: Boolean, default: false },     // altura completa (barra fija + cuerpo con scroll)
  maxWidth: { type: String, default: '' },     // vistas centradas (p.ej. formularios)
  bodyClass: { type: String, default: '' },    // ritmo de espaciado del cuerpo (p.ej. 'space-y-6')
})
</script>

<style scoped>
.view{padding:2rem}
.view--fill{height:100%;padding:0;display:flex;flex-direction:column;min-height:0}
.view__inner{display:flex;flex-direction:column}
.view--fill .view__inner{flex:1;min-height:0;height:100%;padding:1.25rem 1.5rem}
.view__body--fill{flex:1;min-height:0;overflow:auto}
</style>
