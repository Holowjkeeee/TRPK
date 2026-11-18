<template>
  <main class="login-screen" :style="screenStyle">
    <div class="login-screen-overlay"></div>

    <div class="login-theme-switch" role="group" aria-label="Выбор темы">
      <button
        type="button"
        class="login-theme-icon"
        :class="{ active: theme === 'light' }"
        title="Светлая тема"
        aria-label="Светлая тема"
        @click="setTheme('light')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <circle cx="12" cy="12" r="4.2" fill="none" stroke="currentColor" stroke-width="1.8" />
          <path d="M12 2.8v2.2M12 19v2.2M21.2 12H19M5 12H2.8M18.45 5.55l-1.55 1.55M7.1 16.9l-1.55 1.55M18.45 18.45l-1.55-1.55M7.1 7.1 5.55 5.55" fill="none" stroke="currentColor" stroke-linecap="round" stroke-width="1.8" />
        </svg>
      </button>
      <button
        type="button"
        class="login-theme-icon"
        :class="{ active: theme === 'dark' }"
        title="Тёмная тема"
        aria-label="Тёмная тема"
        @click="setTheme('dark')"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true">
          <path d="M17 15.2A7.2 7.2 0 0 1 10.48 5 7.8 7.8 0 1 0 20 14.52 7.12 7.12 0 0 1 17 15.2Z" fill="none" stroke="currentColor" stroke-linejoin="round" stroke-width="1.8" />
        </svg>
      </button>
    </div>

    <section class="login-screen-shell" aria-labelledby="login-title">
      <div class="login-screen-left" aria-hidden="true"></div>

      <div class="login-screen-right">
        <div class="login-brand-hero">
          <div class="login-brand-logo" aria-hidden="true">
            <svg viewBox="0 0 260 125" role="img">
              <ellipse cx="130" cy="48" rx="93" ry="23" fill="none" stroke="#e42932" stroke-width="7" />
              <path d="M95 62c8-8 10-18 16-26 7-10 15-14 21-14 6 0 12 3 17 10 4 6 6 11 9 17 4-6 8-12 13-18 5-6 11-9 18-9 7 0 14 4 21 13 7 8 10 17 17 27" fill="none" stroke="#ffffff" stroke-linecap="round" stroke-linejoin="round" stroke-width="8" />
              <path d="M118 36c7 5 11 12 12 19M143 55c1-7 5-14 12-19" fill="none" stroke="#ffffff" stroke-linecap="round" stroke-width="6" />
            </svg>
          </div>
          <h1 class="login-brand-name">MAT<span>FLOW</span></h1>
          <p class="login-brand-subtitle">Система проведения соревнований<br />по вольной борьбе</p>
        </div>

        <section class="login-auth-card">
          <div v-if="error" class="alert alert-danger py-2 mb-3" role="alert">{{ error }}</div>

          <form class="login-auth-form" @submit.prevent="submit" novalidate>
            <label class="login-input-shell" for="username">
              <span class="login-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M12 12a4.25 4.25 0 1 0 0-8.5A4.25 4.25 0 0 0 12 12Zm0 2.1c-4.55 0-8.25 2.74-8.25 6.12 0 .42.34.78.77.78h14.96c.43 0 .77-.36.77-.78 0-3.38-3.7-6.12-8.25-6.12Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                </svg>
              </span>
              <input id="username" v-model.trim="username" class="login-input" autocomplete="username" :disabled="auth.loading" required autofocus placeholder="Логин" />
            </label>

            <label class="login-input-shell" for="password">
              <span class="login-input-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M7.25 10V7.7A4.75 4.75 0 0 1 12 3a4.75 4.75 0 0 1 4.75 4.7V10M6.2 10h11.6c.66 0 1.2.54 1.2 1.2v8.6c0 .66-.54 1.2-1.2 1.2H6.2c-.66 0-1.2-.54-1.2-1.2v-8.6c0-.66.54-1.2 1.2-1.2Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round" />
                </svg>
              </span>
              <input id="password" v-model="password" :type="showPassword ? 'text' : 'password'" class="login-input login-input-password" autocomplete="current-password" :disabled="auth.loading" required placeholder="Пароль" />
              <button
                class="login-password-toggle"
                type="button"
                :aria-label="showPassword ? 'Скрыть пароль' : 'Показать пароль'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M2.7 12s3.35-5.8 9.3-5.8 9.3 5.8 9.3 5.8-3.35 5.8-9.3 5.8S2.7 12 2.7 12Z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
                  <circle cx="12" cy="12" r="2.9" fill="none" stroke="currentColor" stroke-width="1.8" />
                </svg>
                <svg v-else viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M3.4 3.4 20.6 20.6M9.9 9.9A3 3 0 0 0 14.1 14.1M6.35 6.35C4.15 7.72 2.7 10.2 2.7 12c0 0 3.35 5.8 9.3 5.8 1.81 0 3.39-.54 4.74-1.31M9.54 6.43A10.34 10.34 0 0 1 12 6.2c5.95 0 9.3 5.8 9.3 5.8a12.84 12.84 0 0 1-2.83 3.3" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" />
                </svg>
              </button>
            </label>

            <button type="submit" class="login-submit-button" :disabled="auth.loading || !username || !password">
              <span v-if="auth.loading" class="spinner-border spinner-border-sm me-2" aria-hidden="true"></span>
              {{ auth.loading ? 'Выполняется вход...' : 'Войти' }}
            </button>
          </form>

          <div class="login-auth-meta">
            <div class="login-divider"></div>
            <div class="login-meta-row">
              <span class="login-meta-icon" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M8.25 12a3.75 3.75 0 1 0 0-7.5A3.75 3.75 0 0 0 8.25 12Zm7.5 0a3.75 3.75 0 1 0 0-7.5A3.75 3.75 0 0 0 15.75 12ZM2.8 19.5c0-2.56 2.43-4.65 5.45-4.65s5.45 2.09 5.45 4.65M12.4 19.5c.25-1.92 2.17-3.48 4.57-3.48 2.56 0 4.63 1.75 4.63 3.9" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.7" />
                </svg>
              </span>
              <p>Авторизация судейской коллегии<br />и организатора соревнований</p>
            </div>
            <div class="login-demo-hint">Демо-доступ: <strong>admin</strong> / <strong>admin123</strong></div>
          </div>
        </section>
      </div>
    </section>
  </main>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import { useTheme } from '../theme.js'
import loginBackground from '../assets/login-hall-bg.png'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const { theme, setTheme } = useTheme()

const username = ref('admin')
const password = ref('admin123')
const error = ref('')
const showPassword = ref(false)

const screenStyle = computed(() => ({
  '--login-bg-image': `url(${loginBackground})`
}))

async function submit() {
  if (auth.loading || !username.value || !password.value) return
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : '/competitions'
    await router.replace(next)
  } catch (e) {
    if (!e.response) error.value = 'Не удалось подключиться к серверу. Проверьте, запущен ли backend.'
    else if (e.response.status === 401) error.value = 'Неверный логин или пароль.'
    else error.value = e.response?.data?.detail || 'Не удалось выполнить вход.'
  }
}
</script>
