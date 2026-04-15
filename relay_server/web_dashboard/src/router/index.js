import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/devices'
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/devices',
    name: 'DeviceList',
    component: () => import('../views/DeviceList.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/devices/:id',
    name: 'DeviceDetail',
    component: () => import('../views/DeviceDetail.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/reports',
    name: 'ReportView',
    component: () => import('../views/ReportView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/deploy',
    name: 'DeployView',
    component: () => import('../views/DeployView.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/fleets',
    name: 'Fleets',
    component: () => import('../views/Fleets.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('../views/Settings.vue'),
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
