import { reactive } from 'vue'

// Cola única de avisos no bloqueantes. Un solo ToastHost la pinta.
const toasts = reactive([])
let _id = 0

function push(type, message, timeout) {
  const t = { id: ++_id, type, message: String(message) }
  toasts.push(t)
  if (timeout) setTimeout(() => remove(t.id), timeout)
  return t.id
}
function remove(id) {
  const i = toasts.findIndex(t => t.id === id)
  if (i !== -1) toasts.splice(i, 1)
}

export function useToast() {
  return {
    toast: {
      success: (m) => push('success', m, 3500),
      error:   (m) => push('error', m, 6000),
      info:    (m) => push('info', m, 4000),
    },
  }
}

// Internos para ToastHost.vue
export const toastList = toasts
export function dismissToast(id) { remove(id) }
