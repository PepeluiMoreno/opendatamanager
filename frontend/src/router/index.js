import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Sources from '../views/Sources.vue'
import SourceTest from '../views/SourceTest.vue'
import Applications from '../views/Applications.vue'
import fetchers from '../views/fetchers.vue'

const routes = [
  {
    path: '/',
    name: 'Dashboard',
    component: Dashboard,
  },
  {
    path: '/resources',
    name: 'Resources',
    component: Sources,
  },
  {
    path: '/fetchers',
    name: 'Fetchers',
    component: fetchers,
  },
  {
    path: '/resources/:id/test',
    name: 'ResourceTest',
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
