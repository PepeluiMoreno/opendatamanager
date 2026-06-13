import { reactive } from 'vue'

// Estado único de confirmación para toda la app. Un solo ConfirmHost lo pinta.
const state = reactive({
  open: false,
  title: '',
  message: '',
  confirmText: 'Confirmar',
  cancelText: 'Cancelar',
  danger: false,
  checkbox: null,   // { label } opcional (p. ej. borrado permanente)
  checked: false,
  _resolve: null,
})

function settle(ok) {
  state.open = false
  const r = state._resolve
  state._resolve = null
  if (r) r({ ok, checked: state.checkbox ? state.checked : false })
}

export function useConfirm() {
  /**
   * confirm({ title, message, confirmText, cancelText, danger, checkbox })
   * Devuelve Promise<{ ok: boolean, checked: boolean }>.
   */
  function confirm(opts = {}) {
    return new Promise((resolve) => {
      state.title = opts.title || '¿Confirmar?'
      state.message = opts.message || ''
      state.confirmText = opts.confirmText || 'Confirmar'
      state.cancelText = opts.cancelText || 'Cancelar'
      state.danger = !!opts.danger
      state.checkbox = opts.checkbox || null
      state.checked = false
      state._resolve = resolve
      state.open = true
    })
  }
  return { confirm }
}

// Internos para ConfirmHost.vue
export const confirmState = state
export function confirmAccept() { settle(true) }
export function confirmCancel() { settle(false) }
