<template>
  <div :class="['page-header', { 'page-header--tight': tight }]">
    <div class="page-header__text">
      <h1 class="page-title">{{ title }}</h1>
      <p v-if="subtitle" class="page-subtitle">{{ subtitle }}</p>
      <slot name="subtitle" />
    </div>
    <div v-if="$slots.actions" class="page-header__actions"><slot name="actions" /></div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  tight: { type: Boolean, default: false },
})
</script>

<style scoped>
.page-header{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;margin-bottom:1.5rem}
.page-header--tight{margin-bottom:0}
.page-title{font-size:1.6rem;line-height:1.2;font-weight:700;color:#fff;margin:0}
.page-subtitle{font-size:.8rem;color:#9ca3af;margin:.3rem 0 0}
.page-header__actions{display:flex;align-items:center;gap:.6rem;flex-shrink:0}
</style>
