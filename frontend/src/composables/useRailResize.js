import { ref } from 'vue'

// Rail redimensionable de las consolas (Resources, Subscribers…). DRY: misma
// lógica de ancho/colapso y arrastre del divisor en todas las vistas con rail.
export function useRailResize({ initial = 264, min = 200, max = 440, breakpoint = 880 } = {}) {
  const railW = ref(initial)
  const railOpen = ref(typeof window === 'undefined' || window.innerWidth >= breakpoint)
  let dragging = false
  function startDrag(e) {
    dragging = true
    e.preventDefault()
    const move = ev => { if (dragging) railW.value = Math.min(max, Math.max(min, ev.clientX)) }
    const up = () => {
      dragging = false
      window.removeEventListener('mousemove', move)
      window.removeEventListener('mouseup', up)
    }
    window.addEventListener('mousemove', move)
    window.addEventListener('mouseup', up)
  }
  return { railW, railOpen, startDrag }
}
