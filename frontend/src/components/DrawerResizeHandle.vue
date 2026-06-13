<template>
  <div class="dgrip" @mousedown.prevent="start" title="Arrastra para ensanchar"></div>
</template>

<script setup>
import { onMounted } from 'vue'

const props = defineProps({
  modelValue: { type: Number, default: 760 },
  storageKey: { type: String, default: '' },   // persiste la anchura entre sesiones
  min: { type: Number, default: 480 },
})
const emit = defineEmits(['update:modelValue'])
const key = () => 'odm:dw:' + props.storageKey

onMounted(() => {
  if (props.storageKey && typeof localStorage !== 'undefined') {
    const saved = parseInt(localStorage.getItem(key()) || '', 10)
    if (!isNaN(saved)) emit('update:modelValue', saved)
  }
})

let dragging = false
function start() {
  dragging = true
  const move = ev => {
    if (!dragging) return
    // drawer anclado a la derecha: la anchura es la distancia del borde izq. al borde derecho.
    emit('update:modelValue', Math.min(window.innerWidth * 0.96, Math.max(props.min, window.innerWidth - ev.clientX)))
  }
  const up = () => {
    dragging = false
    document.removeEventListener('mousemove', move)
    document.removeEventListener('mouseup', up)
    if (props.storageKey && typeof localStorage !== 'undefined') localStorage.setItem(key(), String(Math.round(props.modelValue)))
  }
  document.addEventListener('mousemove', move)
  document.addEventListener('mouseup', up)
}
</script>

<style scoped>
.dgrip{position:absolute;left:0;top:0;height:100%;width:12px;cursor:ew-resize;z-index:61;display:flex;align-items:center}
.dgrip::before{content:"";width:3px;height:100%;background:#222C39;transition:background .15s}
.dgrip:hover::before,.dgrip:active::before{background:#3FE0CB}
.dgrip::after{content:"";position:absolute;left:1px;top:50%;transform:translateY(-50%);width:4px;height:34px;border-radius:3px;background:#3a4a5a;transition:background .15s}
.dgrip:hover::after{background:#3FE0CB}
</style>
