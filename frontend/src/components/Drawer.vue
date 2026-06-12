<template>
  <teleport to="body">
    <div :class="['odm-scrim', { show: modelValue }]" @click="$emit('update:modelValue', false)"></div>
    <aside :class="['odm-drawer', { show: modelValue }]" :style="{ width: widthCss }" role="dialog" aria-modal="true">
      <div class="odm-dh">
        <div v-if="icon" class="odm-di">{{ icon }}</div>
        <div class="odm-dt">
          <h2>{{ title }}</h2>
          <p v-if="subtitle">{{ subtitle }}</p>
        </div>
        <button class="odm-x" @click="$emit('update:modelValue', false)" aria-label="Cerrar">✕</button>
      </div>
      <div class="odm-dbody"><slot /></div>
      <div v-if="$slots.footer" class="odm-dfoot"><slot name="footer" /></div>
    </aside>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  icon: { type: String, default: '' },
  width: { type: [Number, String], default: 620 },
})
defineEmits(['update:modelValue'])
const widthCss = computed(() => `min(${typeof props.width === 'number' ? props.width + 'px' : props.width}, 96vw)`)
</script>

<style>
.odm-scrim{position:fixed;inset:0;background:#04060a99;backdrop-filter:blur(3px);opacity:0;pointer-events:none;transition:.25s;z-index:9000}
.odm-scrim.show{opacity:1;pointer-events:auto}
.odm-drawer{position:fixed;top:0;right:0;height:100vh;background:linear-gradient(180deg,#131922,#0f141b);border-left:1px solid #222C39;
  transform:translateX(102%);transition:.3s cubic-bezier(.3,.8,.3,1);z-index:9001;display:flex;flex-direction:column;box-shadow:-30px 0 70px #000a}
.odm-drawer.show{transform:translateX(0)}
.odm-dh{display:flex;align-items:flex-start;gap:12px;padding:20px 24px 16px;border-bottom:1px solid #222C39}
.odm-di{width:40px;height:40px;border-radius:11px;background:#10211d;border:1px solid #1c5b54;display:grid;place-items:center;font-size:19px;flex-shrink:0}
.odm-dt h2{font-family:'Space Grotesk',sans-serif;font-size:18px;margin:0 0 2px;font-weight:600;color:#E7EEF6}
.odm-dt p{margin:0;font-size:12px;color:#5A6878;font-family:'JetBrains Mono',monospace}
.odm-x{margin-left:auto;width:32px;height:32px;border-radius:9px;color:#8595A6;font-size:18px;display:grid;place-items:center;border:1px solid #222C39;background:none;cursor:pointer}
.odm-x:hover{color:#E7EEF6;background:#1c2632}
.odm-dbody{flex:1;overflow-y:auto;padding:18px 24px 28px}
.odm-dfoot{display:flex;align-items:center;gap:10px;padding:14px 24px;border-top:1px solid #222C39;background:#0f141b}
</style>
