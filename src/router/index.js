import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/register', name: 'Register', component: () => import('../views/Register.vue'), meta: { public: true } },
  { path: '/forgot-password', name: 'ForgotPassword', component: () => import('../views/ForgotPassword.vue'), meta: { public: true } },
  { path: '/reset-password', name: 'ResetPassword', component: () => import('../views/ResetPassword.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    children: [
      { path: '', name: 'Dashboard', component: () => import('../views/Dashboard.vue') },
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { role: 'teacher' } },
      { path: 'models', name: 'Models', component: () => import('../views/Models.vue') },
      { path: 'knowledge', name: 'Knowledge', component: () => import('../views/Knowledge.vue') },
      { path: 'prompts', name: 'Prompts', component: () => import('../views/Prompts.vue') },
      { path: 'chat', name: 'Chat', component: () => import('../views/Chat.vue') },
    ],
  },
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach((to, _from, next) => {
  const store = useAuthStore()
  if (to.meta.public) {
    if (store.isLoggedIn && (to.name === 'Login' || to.name === 'Register')) {
      next({ path: '/' })
    } else {
      next()
    }
    return
  }
  if (!store.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }
  if (to.meta.role === 'teacher' && !store.canManageTA) {
    next({ path: '/' })
    return
  }
  next()
})

export default router
