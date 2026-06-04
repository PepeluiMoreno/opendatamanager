import { ref, computed } from 'vue'
import { onAuthError } from '../api/graphql'

// Estado de sesión compartido (singleton de módulo). Modelo invitado-primero:
// la app carga sin credenciales con los permisos públicos; iniciar sesión
// amplía permisos según los roles del usuario (RBAC en el servidor).
const usuario = ref(null)          // username, o null si invitado
const roles = ref([])
const permisos = ref(new Set())
const inicializado = ref(false)
const mostrarLogin = ref(false)

async function cargarSesion() {
  try {
    const r = await fetch('/api/auth/me', { credentials: 'same-origin' })
    const d = await r.json()
    usuario.value = d.invitado ? null : d.username
    roles.value = d.roles || []
    permisos.value = new Set(d.permisos || [])
  } catch {
    usuario.value = null
    roles.value = []
    permisos.value = new Set()
  } finally {
    inicializado.value = true
  }
}

// Sesión caducada o permiso denegado en alguna llamada → re-sincronizar perfil.
onAuthError(() => { cargarSesion() })

// Carga inicial al arrancar la app (promesa exportada para las guardas de ruta).
const sesionLista = cargarSesion()

// Comprobación de permiso utilizable fuera de componentes (router).
function puedePermiso(code) {
  return permisos.value.has(code)
}

export { sesionLista, puedePermiso }

export function useAuth() {
  async function login(username, password) {
    const r = await fetch('/api/auth/login', {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: (username || '').trim(), password }),
    })
    if (r.status === 401) throw new Error('Usuario o contraseña incorrectos.')
    if (!r.ok) throw new Error('No se pudo iniciar sesión (¿servidor disponible?).')
    const d = await r.json()
    usuario.value = d.username
    roles.value = d.roles || []
    permisos.value = new Set(d.permisos || [])
    mostrarLogin.value = false
    return true
  }

  async function logout() {
    try {
      await fetch('/api/auth/logout', { method: 'POST', credentials: 'same-origin' })
    } catch { /* sin red: el estado local se resetea igualmente */ }
    await cargarSesion()
  }

  function puede(code) {
    return permisos.value.has(code)
  }

  const esInvitado = computed(() => !usuario.value)

  return { usuario, roles, permisos, esInvitado, inicializado, mostrarLogin, login, logout, puede, cargarSesion }
}
