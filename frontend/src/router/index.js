import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Sources from '../views/Sources.vue'
import SourceTest from '../views/SourceTest.vue'
import Applications from '../views/Applications.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
  },
  {
    path: '/sources',
    name: 'Sources',
    component: Sources,
  },
  {
    path: '/sources/:id/test',
    name: 'SourceTest',
    component: SourceTest,
  },
  {
    path: '/applications',
    name: 'Applications',
    component: Applications,
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
