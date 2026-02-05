import { defineStore } from 'pinia'
import { auth as authApi } from '../api'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isTeacher: (s) => s.user?.role === 'teacher',
    isTA: (s) => s.user?.role === 'ta',
    canManageTA: (s) => s.user?.role === 'teacher',
  },
  actions: {
    setAuth(token, user) {
      this.token = token
      this.user = user
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify(user))
    },
    async fetchMe() {
      const u = await authApi.me()
      this.user = u
      localStorage.setItem('user', JSON.stringify(u))
      return u
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
