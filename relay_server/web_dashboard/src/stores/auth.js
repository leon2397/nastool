import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || null)
  const user = ref(null)
  const relayUrl = ref(localStorage.getItem('relayUrl') || 'wss://qizhiainas.com')

  const login = async (username, password, url) => {
    try {
      const response = await authApi.login(username, password)
      token.value = response.data.token
      user.value = response.data.user
      
      localStorage.setItem('token', response.data.token)
      
      if (url) {
        relayUrl.value = url
        localStorage.setItem('relayUrl', url)
      }
      
      return { success: true }
    } catch (error) {
      return { success: false, error: error.response?.data?.message || '登录失败' }
    }
  }

  const logout = () => {
    token.value = null
    user.value = null
    localStorage.removeItem('token')
  }

  const refreshToken = async () => {
    try {
      const response = await authApi.refresh()
      token.value = response.data.token
      localStorage.setItem('token', response.data.token)
      return { success: true }
    } catch (error) {
      logout()
      return { success: false }
    }
  }

  return {
    token,
    user,
    relayUrl,
    login,
    logout,
    refreshToken
  }
})
