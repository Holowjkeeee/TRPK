import { defineStore } from 'pinia'
import http from '../api/http.js'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    loading: false,
    initialized: false,
    accessToken: localStorage.getItem('access_token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.accessToken),
  },
  actions: {
    setTokens(access, refresh = this.refreshToken) {
      this.accessToken = access || ''
      this.refreshToken = refresh || ''
      if (this.accessToken) localStorage.setItem('access_token', this.accessToken)
      else localStorage.removeItem('access_token')
      if (this.refreshToken) localStorage.setItem('refresh_token', this.refreshToken)
      else localStorage.removeItem('refresh_token')
    },
    async login(username, password) {
      this.loading = true
      try {
        const response = await http.post('/token/', { username, password })
        this.setTokens(response.data.access, response.data.refresh)
        await this.loadUser()
        this.initialized = true
        return this.user
      } catch (error) {
        this.clearSession()
        throw error
      } finally {
        this.loading = false
      }
    },
    async loadUser() {
      if (!this.isAuthenticated) {
        this.user = null
        this.initialized = true
        return null
      }
      try {
        const response = await http.get('/me/')
        this.user = response.data
        return this.user
      } finally {
        this.initialized = true
      }
    },
    clearSession() {
      this.setTokens('', '')
      this.user = null
      this.initialized = true
    },
    logout() {
      this.clearSession()
    },
  },
})
