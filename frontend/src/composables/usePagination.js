import { ref, computed, watch } from 'vue'

/**
 * Paginación en memoria sobre una fuente reactiva (ref/computed de array).
 * Devuelve la página actual (slice), controles y total. Reinicia a la página 1
 * cuando la fuente cambia de tamaño (p. ej. al filtrar).
 */
export function usePagination(sourceRef, defaultPerPage = 25) {
  const page = ref(1)
  const perPage = ref(defaultPerPage)
  const total = computed(() => (sourceRef.value || []).length)
  const paged = computed(() => {
    const arr = sourceRef.value || []
    const start = (page.value - 1) * perPage.value
    return arr.slice(start, start + perPage.value)
  })
  // Si el filtrado deja la página actual fuera de rango, vuelve a una válida.
  watch(total, (n) => {
    const maxPage = Math.max(1, Math.ceil(n / perPage.value))
    if (page.value > maxPage) page.value = maxPage
  })
  return { page, perPage, total, paged }
}
