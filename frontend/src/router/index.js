import { createRouter, createWebHistory } from 'vue-router'
import Dashboard from '../views/Dashboard.vue'
import Sources from '../views/Sources.vue'
import SourceTest from '../views/SourceTest.vue'
import Applications from '../views/Applications.vue'
import FetcherTypes from '../views/FetcherTypes.vue'

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
