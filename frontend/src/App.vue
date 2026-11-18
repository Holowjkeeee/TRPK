<template>
  <div class="app-shell">
    <header v-if="auth.isAuthenticated" class="app-navbar">
      <div class="container-fluid px-3 px-lg-4 d-flex align-items-center justify-content-between gap-3">
        <RouterLink class="brand-link" to="/competitions" aria-label="MATFLOW - соревнования">
          <span class="brand-mark" aria-hidden="true"><i class="red"></i><i class="blue"></i></span>
          <span class="brand-copy"><strong>MATFLOW</strong><small>Соревнования по борьбе</small></span>
        </RouterLink>
        <div class="header-actions">
          <button class="btn btn-header theme-toggle" type="button" :title="themeButtonTitle" @click="toggleTheme">
            <span class="theme-toggle-icon" aria-hidden="true">{{ theme === 'dark' ? '☀' : '☾' }}</span>
            <span class="theme-toggle-text">{{ theme === 'dark' ? 'Светлая' : 'Тёмная' }}</span>
          </button>
          <div v-if="auth.user" class="user-chip" title="Текущий пользователь">
            <span class="user-dot"></span>
            <span><strong>{{ auth.user.username }}</strong><small>{{ auth.user.role_display }}</small></span>
          </div>
          <button class="btn btn-header" type="button" @click="logout">Выйти</button>
        </div>
      </div>
    </header>
    <RouterView />
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth.js'
import { useTheme } from './theme.js'

const auth = useAuthStore()
const router = useRouter()
const { theme, toggleTheme } = useTheme()

const themeButtonTitle = computed(() => theme.value === 'dark' ? 'Переключить на светлую тему' : 'Переключить на тёмную тему')

async function logout() {
  auth.logout()
  await router.replace('/login')
  window.location.reload()
}

async function handleAuthExpired() {
  auth.logout()
  if (router.currentRoute.value.name !== 'login') await router.replace('/login')
}

onMounted(() => window.addEventListener('matflow-auth-expired', handleAuthExpired))
onBeforeUnmount(() => window.removeEventListener('matflow-auth-expired', handleAuthExpired))
</script>
