import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, getCurrentUser } from '../api/auth'

export const useUserStore = defineStore('user', () => {
  const token = ref(localStorage.getItem('token') || '')
  const userInfo = ref(JSON.parse(localStorage.getItem('userInfo') || 'null'))

  const isKeeper = computed(() => userInfo.value?.role === 'warehouse_keeper')
  const isDuty = computed(() => userInfo.value?.role === 'duty_officer')
  const roleText = computed(() => {
    const map = {
      'warehouse_keeper': '仓库管理员',
      'duty_officer': '值班员'
    }
    return map[userInfo.value?.role] || ''
  })

  async function login(username, password) {
    const res = await apiLogin(username, password)
    token.value = res.access_token
    userInfo.value = res.user
    localStorage.setItem('token', res.access_token)
    localStorage.setItem('userInfo', JSON.stringify(res.user))
    return res
  }

  async function fetchUserInfo() {
    if (!token.value) return null
    try {
      const res = await getCurrentUser()
      userInfo.value = res
      localStorage.setItem('userInfo', JSON.stringify(res))
      return res
    } catch (e) {
      logout()
      throw e
    }
  }

  function logout() {
    token.value = ''
    userInfo.value = null
    localStorage.removeItem('token')
    localStorage.removeItem('userInfo')
  }

  return {
    token,
    userInfo,
    isKeeper,
    isDuty,
    roleText,
    login,
    fetchUserInfo,
    logout
  }
})
