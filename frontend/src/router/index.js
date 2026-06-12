import { sesionLista, puedePermiso } from '../composables/useAuth'
import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import MisDatos from '../views/MisDatos.vue'
import Resources from '../views/Resources.vue'
import ResourcesConsole from '../views/ResourcesConsole.vue'
import SubscribersConsole from '../views/SubscribersConsole.vue'
import ResourceTest from '../views/ResourceTest.vue'
import Fetchers from '../views/Fetchers.vue'
import Executions from '../views/Executions.vue'
import Settings from '../views/Settings.vue'
import Schedule from '../views/Schedule.vue'
import DataExplorer from '../views/DataExplorer.vue'
import Publishers from '../views/Publishers.vue'
import Trash from '../views/Trash.vue'
import Usuarios from '../views/Usuarios.vue'
import Candidates from '../views/Discovering.vue'
import Collections from '../views/Collections.vue'
import Aprobaciones from '../views/Aprobaciones.vue'
import Subscribers from '../views/SubscribersTabs.vue'

const routes = [
  { path: '/mis-datos',      name: 'MisDatos',      component: MisDatos },
  { path: '/',               name: 'Dashboard',    component: Dashboard },
  { path: '/resources',      name: 'Resources',     component: Resources },
  { path: '/console',        name: 'ResourcesConsole', component: ResourcesConsole },
  { path: '/subscribers-console', name: 'SubscribersConsole', component: SubscribersConsole },
  { path: '/collections',    name: 'Collections',   component: Collections },
  { path: '/fetchers',       name: 'Fetchers',      component: Fetchers },
  { path: '/resources/:id/test', name: 'ResourceTest', component: ResourceTest },
  { path: '/subscribers',    name: 'Subscribers',   component: Subscribers },
  { path: '/applications',   redirect: '/subscribers' },
  { path: '/aprobaciones',   redirect: '/subscribers' },
  { path: '/processes',      name: 'Processes',     component: Executions },
  { path: '/schedule',       name: 'Schedule',      component: Schedule, meta: { permiso: 'programacion.gestionar' } },
  { path: '/settings',       name: 'Settings',      component: Settings, meta: { permiso: 'settings.gestionar' } },
  { path: '/explorer',       name: 'DataExplorer',  component: DataExplorer },
  { path: '/publishers',     name: 'Publishers',    component: Publishers },
  { path: '/trash',          name: 'Trash',         component: Trash, meta: { permiso: 'recursos.borrar' } },
  { path: '/resources/:id/candidates', name: 'ResourceCandidates', component: Candidates, meta: { permiso: 'recursos.crear' } },
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
