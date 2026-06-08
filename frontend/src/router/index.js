import { createRouter, createWebHashHistory } from 'vue-router'
import { useUserStore } from '../store/user'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue')
      },
      {
        path: 'batches',
        name: 'Batches',
        component: () => import('../views/BatchList.vue')
      },
      {
        path: 'batches/:id',
        name: 'BatchDetail',
        component: () => import('../views/BatchDetail.vue')
      },
      {
        path: 'orders',
        name: 'Orders',
        component: () => import('../views/OrderList.vue')
      },
      {
        path: 'orders/:id',
        name: 'OrderDetail',
        component: () => import('../views/OrderDetail.vue')
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('../views/AuditLog.vue')
      },
      {
        path: 'stock-takes',
        name: 'StockTakes',
        component: () => import('../views/StockTakeList.vue')
      },
      {
        path: 'stock-takes/:id',
        name: 'StockTakeDetail',
        component: () => import('../views/StockTakeDetail.vue')
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

router.beforeEach((to, from, next) => {
  const userStore = useUserStore()
  if (to.meta.requiresAuth && !userStore.token) {
    next('/login')
  } else if (to.path === '/login' && userStore.token) {
    next('/')
  } else {
    next()
  }
})

export default router
