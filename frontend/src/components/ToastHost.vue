<template>
  <teleport to="body">
    <div class="tst-wrap">
      <transition-group name="tst">
        <div v-for="t in list" :key="t.id" :class="['tst', 'tst-' + t.type]" @click="dismiss(t.id)">
          <span class="tst-ico">{{ t.type === 'error' ? '✕' : t.type === 'success' ? '✓' : 'ℹ' }}</span>
          <span class="tst-msg">{{ t.message }}</span>
        </div>
      </transition-group>
    </div>
  </teleport>
</template>

<script setup>
import { toastList as list, dismissToast } from '../composables/useToast'
function dismiss(id) { dismissToast(id) }
</script>

<style scoped>
.tst-wrap{position:fixed;right:1rem;bottom:1rem;z-index:10001;display:flex;flex-direction:column;gap:.5rem;max-width:26rem}
.tst{display:flex;align-items:flex-start;gap:.55rem;padding:.6rem .85rem;border-radius:.55rem;font-size:.82rem;line-height:1.4;color:#E7EEF6;background:#161D27;border:1px solid #222C39;box-shadow:0 12px 30px #0008;cursor:pointer}
.tst-ico{font-weight:700;flex-shrink:0}
.tst-error{border-color:#7f1d1d;background:#1f1416}.tst-error .tst-ico{color:#f87171}
.tst-success{border-color:#1c5b54;background:#101e1c}.tst-success .tst-ico{color:#3FE0CB}
.tst-info{border-color:#1e3a8a;background:#121a2b}.tst-info .tst-ico{color:#93c5fd}
.tst-enter-active,.tst-leave-active{transition:all .2s}
.tst-enter-from,.tst-leave-to{opacity:0;transform:translateX(20px)}
</style>
