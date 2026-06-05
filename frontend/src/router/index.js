import { sesionLista, puedePermiso } from '../composables/useAuth'
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import MisDatos from '../views/MisDatos.vue'
import Resources from '../views/Resources.vue'
import ResourceTest from '../views/ResourceTest.vue'
import Applications from '../views/Applications.vue'
import Fetchers from '../views/Fetchers.vue'
import Executions from '../views/Executions.vue'
import Settings from '../views/Settings.vue'
import Schedule from '../views/Schedule.vue'
import DataExplorer from '../views/DataExplorer.vue'
import Publishers from '../views/Publishers.vue'
import Subscriptions from '../views/Subscriptions.vue'
import Trash from '../views/Trash.vue'
import Usuarios from '../views/Usuarios.vue'
import Candidates from '../views/Discovering.vue'

const routes = [
  { path: '/mis-datos',      name: 'MisDatos',      component: MisDatos },
  { path: '/',               name: 'Dashboard',    component: Dashboard },
  { path: '/resources',      name: 'Resources',     component: Resources },
  { path: '/fetchers',       name: 'Fetchers',      component: Fetchers },
  { path: '/resources/:id/test', name: 'ResourceTest', component: ResourceTest },
  { path: '/applications',   name: 'Applications',  component: Applications, meta: { permiso: 'aplicaciones.gestionar' } },
  { path: '/processes',      name: 'Processes',     component: Executions },
  { path: '/schedule',       name: 'Schedule',      component: Schedule, meta: { permiso: 'programacion.gestionar' } },
  { path: '/settings',       name: 'Settings',      component: Settings, meta: { permiso: 'settings.gestionar' } },
  { path: '/explorer',       name: 'DataExplorer',  component: DataExplorer },
  { path: '/publishers',     name: 'Publishers',    component: Publishers },
  { path: '/subscriptions',  name: 'Subscriptions', component: Subscriptions, meta: { permiso: 'aplicaciones.gestionar' } },
  { path: '/trash',          name: 'Trash',         component: Trash, meta: { permiso: 'recursos.borrar' } },
  { path: '/candidates',     name: 'Candidates',    component: Candidates, meta: { permiso: 'recursos.crear' } },
  { path: '/usuarios',       name: 'Usuarios',      component: Usuarios, meta: { permiso: 'usuarios.gestionar' } },
]

const router = createRouter({ history: createWebHistory(), routes })
// Guarda de permisos: espera a conocer la sesión y bloquea vistas sin permiso.
router.beforeEach(async (to) => {
  if (!to.meta?.permiso) return true
  await sesionLista
  return puedePermiso(to.meta.permiso) ? true : '/'
})

export default router
