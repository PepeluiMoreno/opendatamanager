import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Resources from '../views/Resources.vue'
import ResourceTest from '../views/ResourceTest.vue'
import Applications from '../views/Applications.vue'
import fetchers from '../views/Fetchers.vue'
import Executions from '../views/Executions.vue'
import Settings from '../views/Settings.vue'
import Schedule from '../views/Schedule.vue'
import DataExplorer from '../views/DataExplorer.vue'
import Publishers from '../views/Publishers.vue'
import Subscriptions from '../views/Subscriptions.vue'
import Trash from '../views/Trash.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
  },
  {
    path: '/resources',
    name: 'Resources',
    component: Resources,
  },
  {
    path: '/fetchers',
    name: 'Fetchers',
    component: fetchers,
  },
  {
    path: '/resources/:id/test',
    name: 'ResourceTest',
    component: ResourceTest,
  },
  {
    path: '/applications',
    name: 'Applications',
    component: Applications,
  },
  {
    path: '/processes',
    name: 'Processes',
    component: Executions,
  },
  {
    path: '/schedule',
    name: 'Schedule',
    component: Schedule,
  },
  {
    path: '/settings',
    name: 'Settings',
    component: Settings,
  },
  {
    path: '/explorer',
    name: 'DataExplorer',
    component: DataExplorer,
  },
  {
    path: '/publishers',
    name: 'Publishers',
    component: Publishers,
  },
  {
    path: '/subscriptions',
    name: 'Subscriptions',
    component: Subscriptions,
  },
  {
    path: '/trash',
    name: 'Trash',
    component: Trash,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
