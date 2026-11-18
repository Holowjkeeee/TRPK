<template>
  <main class="container-fluid app-content px-3 px-lg-4 pb-5">
    <div class="competition-breadcrumb mb-3">
      <RouterLink to="/competitions">← Все соревнования</RouterLink>
    </div>

    <section class="competition-hero mb-3">
      <div v-if="competition" class="competition-hero-main">
        <div>
          <div class="competition-number">Соревнование #{{ competition.id }}</div>
          <h1>{{ competition.name }}</h1>
          <div class="hero-meta">
            <span>◷ {{ formatDate(competition.date) }}</span>
            <span>⌖ {{ competition.venue }}</span>
            <span>▦ {{ competition.mat_count }} ковра</span>
          </div>
        </div>
        <div class="hero-status">
          <span class="status-dot"></span>{{ competition.status_display || statusLabel(competition.status) }}
        </div>
      </div>
      <div v-else class="text-muted">Загрузка соревнования...</div>
    </section>

    <nav class="competition-nav mb-4">
      <RouterLink :to="basePath"><span>01</span>Обзор</RouterLink>
      <RouterLink :to="`${basePath}/applications`"><span>02</span>Заявки</RouterLink>
      <RouterLink :to="`${basePath}/weigh-in`"><span>03</span>Взвешивание</RouterLink>
      <RouterLink :to="`${basePath}/categories`"><span>04</span>Категории</RouterLink>
      <RouterLink :to="`${basePath}/brackets`"><span>05</span>Сетки и результаты</RouterLink>
      <RouterLink :to="`${basePath}/protocol`"><span>06</span>Протокол</RouterLink>
    </nav>

    <RouterView />
  </main>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http.js'

const route = useRoute()
const competition = ref(null)
const basePath = computed(() => `/competitions/${route.params.id}`)

function formatDate(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU') : ''
}
function statusLabel(value) {
  return { draft: 'Подготовка', registration: 'Приём заявок', weigh_in: 'Взвешивание', running: 'Проводится', finished: 'Завершено' }[value] || value
}
async function load() {
  const response = await http.get(`/competitions/${route.params.id}/`)
  competition.value = response.data
}

onMounted(load)
watch(() => route.params.id, load)
</script>
