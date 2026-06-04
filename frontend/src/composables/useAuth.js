import { ref } from 'vue'
import { gql } from 'graphql-request'
import { client, getAdminToken, setAdminToken, clearAdminToken, onAuthError } from '../api/graphql'

// Estado de autenticación reactivo y compartido por toda la app.
// El modelo es mono-admin: el "token de acceso" (ODM_ADMIN_TOKEN) ES la clave.
// No hay JWT ni usuarios; el token se guarda y se adjunta como Bearer.
const isAuthenticated = ref(!!getAdminToken())

// Si cualquier petición devuelve 401/403, cerramos sesión y volvemos al login.
onAuthError(() => {
  clearAdminToken()
  isAuthenticated.value = false
})

export function useAuth() {
  // Valida la clave contra la API protegida y, si es correcta, autentica.
  async function login(token) {
    const clean = (token || '').trim()
    if (!clean) throw new Error('Introduce la clave de administración.')
    setAdminToken(clean)
    try {
      // Petición mínima a la API de administración: 200 = clave válida.
      await client.request(gql`{ __typename }`)
      isAuthenticated.value = true
      return true
    } catch (err) {
      // 401/403 ya habrá limpiado el token vía onAuthError.
      const status = err?.response?.status
      if (status === 401 || status === 403) {
        throw new Error('Clave incorrecta.')
      }
      // Otro error (red, servidor): conservamos el token, informamos.
      isAuthenticated.value = !!getAdminToken()
      throw new Error('No se pudo verificar la clave (¿servidor disponible?).')
    }
  }

  function logout() {
    clearAdminToken()
    isAuthenticated.value = false
  }

  return { isAuthenticated, login, logout }
}
