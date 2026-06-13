<template>
  <teleport to="body">
    <div v-if="s.open" class="cfm-scrim" @click.self="cancel">
      <div class="cfm-box" role="alertdialog" aria-modal="true">
        <h3 class="cfm-title">{{ s.title }}</h3>
        <p v-if="s.message" class="cfm-msg">{{ s.message }}</p>
        <label v-if="s.checkbox" class="cfm-check">
          <input type="checkbox" v-model="s.checked">
          <span>{{ s.checkbox.label }}</span>
        </label>
        <div class="cfm-actions">
          <button class="cfm-btn cfm-ghost" @click="cancel">{{ s.cancelText }}</button>
          <button class="cfm-btn" :class="s.danger || s.checked ? 'cfm-danger' : 'cfm-primary'" @click="accept">{{ s.confirmText }}</button>
        </div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { confirmState as s, confirmAccept, confirmCancel } from '../composables/useConfirm'
function accept() { confirmAccept() }
function cancel() { confirmCancel() }
</script>

<style scoped>
.cfm-scrim{position:fixed;inset:0;background:#04060acc;backdrop-filter:blur(3px);display:flex;align-items:center;justify-content:center;z-index:10000;padding:1rem}
.cfm-box{background:linear-gradient(180deg,#161D27,#11161e);border:1px solid #222C39;border-radius:.85rem;padding:1.4rem 1.5rem;width:100%;max-width:30rem;box-shadow:0 30px 70px #000a}
.cfm-title{font-size:1.05rem;font-weight:700;color:#E7EEF6;margin:0 0 .5rem}
.cfm-msg{font-size:.85rem;color:#b6c2d0;line-height:1.5;margin:0}
.cfm-check{display:flex;align-items:flex-start;gap:.5rem;margin-top:.85rem;font-size:.8rem;color:#FF9B9B;cursor:pointer}
.cfm-check input{margin-top:.15rem;accent-color:#FF6B6B}
.cfm-actions{display:flex;justify-content:flex-end;gap:.6rem;margin-top:1.3rem}
.cfm-btn{font-size:.82rem;font-weight:600;border:0;border-radius:.5rem;padding:.5rem .95rem;cursor:pointer}
.cfm-ghost{background:#222c39;color:#cbd5e1}
.cfm-ghost:hover{background:#2b3a4b;color:#fff}
.cfm-primary{background:#2563eb;color:#fff}
.cfm-primary:hover{background:#3b82f6}
.cfm-danger{background:#dc2626;color:#fff}
.cfm-danger:hover{background:#ef4444}
</style>
