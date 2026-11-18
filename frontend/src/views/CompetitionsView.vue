<template>
  <main class="container-fluid app-content px-3 px-lg-4 pb-5">
    <div class="page-hero mb-4">
      <div>
        <h1>Соревнования</h1>
        <p class="page-subtitle">Создание и управление соревнованиями.</p>
              </div>
      <div class="d-flex gap-2 flex-wrap">
        <button type="button" class="btn btn-ghost" :disabled="generating" @click="generateTestData">{{ generating ? 'Создание...' : 'Создать тестовые данные' }}</button>
        <button type="button" class="btn btn-primary" data-bs-toggle="collapse" data-bs-target="#createForm">+ Новое соревнование</button>
      </div>
    </div>

    <div v-if="testMessage" class="alert alert-success">{{ testMessage }}</div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>

    <div id="createForm" class="collapse mb-4">
      <div class="panel-card p-4">
        <div class="section-heading compact mb-3"><div><h2>Новое соревнование</h2></div></div>
        <form class="row g-3" @submit.prevent="createCompetition">
          <div class="col-md-6"><label class="form-label">Название</label><input v-model.trim="form.name" class="form-control" required /></div>
          <div class="col-md-3"><label class="form-label">Дата</label><input v-model="form.date" type="date" class="form-control" required /></div>
          <div class="col-md-3"><label class="form-label">Количество ковров</label><input v-model.number="form.mat_count" type="number" min="1" max="10" class="form-control" required /></div>
          <div class="col-md-8"><label class="form-label">Место проведения</label><input v-model.trim="form.venue" class="form-control" required /></div>
          <div class="col-md-4"><label class="form-label">Статус</label><select v-model="form.status" class="form-select"><option value="draft">Подготовка</option><option value="registration">Приём заявок</option><option value="weigh_in">Взвешивание</option><option value="running">Проводится</option><option value="finished">Завершено</option></select></div>
          <div class="col-12"><button type="submit" class="btn btn-primary" :disabled="saving">{{ saving ? 'Сохранение...' : 'Создать соревнование' }}</button></div>
        </form>
      </div>
    </div>

    <div v-if="loading" class="panel-card p-5 text-center text-muted">Загрузка...</div>
    <div v-else class="competition-grid">
      <RouterLink v-for="item in competitions" :key="item.id" :to="`/competitions/${item.id}`" class="competition-card">
        <div class="competition-card-top">
          <div class="competition-index">#{{ item.id }}</div>
          <span class="status-chip">{{ item.status_display || statusLabel(item.status) }}</span>
        </div>
        <h2>{{ item.name }}</h2>
        <div class="competition-place">{{ formatDate(item.date) }} · {{ item.venue }}</div>
        <div class="competition-metrics">
          <div><strong>{{ item.categories_count }}</strong><span>категорий</span></div>
          <div><strong>{{ item.participants_count }}</strong><span>участников</span></div>
          <div><strong>{{ item.admitted_count }}</strong><span>допущено</span></div>
          <div><strong>{{ item.matches_count || 0 }}</strong><span>поединков</span></div>
        </div>
        <div class="competition-card-footer"><span>Открыть соревнование</span><b>→</b></div>
      </RouterLink>
    </div>
  </main>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import http from '../api/http.js'

const competitions = ref([])
const loading = ref(false)
const saving = ref(false)
const generating = ref(false)
const error = ref('')
const testMessage = ref('')
const form = reactive({ name: '', date: '', venue: '', mat_count: 2, status: 'draft' })

function statusLabel(value) { return { draft: 'Подготовка', registration: 'Приём заявок', weigh_in: 'Взвешивание', running: 'Проводится', finished: 'Завершено' }[value] || value }
function formatDate(value) { return value ? new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU') : '' }

async function load() {
  loading.value = true
  error.value = ''
  try { competitions.value = (await http.get('/competitions/')).data }
  catch (e) { error.value = e.response?.data?.detail || 'Ошибка загрузки соревнований' }
  finally { loading.value = false }
}

async function createCompetition() {
  saving.value = true
  error.value = ''
  try {
    await http.post('/competitions/', form)
    Object.assign(form, { name: '', date: '', venue: '', mat_count: 2, status: 'draft' })
    await load()
  } catch (e) { error.value = JSON.stringify(e.response?.data || 'Ошибка сохранения') }
  finally { saving.value = false }
}

async function generateTestData() {
  if (!confirm('Пересоздать тестовые соревнования? Старые соревнования с префиксом [ТЕСТ] будут удалены.')) return
  generating.value = true
  error.value = ''
  testMessage.value = ''
  try {
    const response = await http.post('/competitions/generate-test-data/')
    testMessage.value = `${response.data.detail}. Сетки 5 / 7 / 10 уже сформированы.`
    await load()
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось создать тестовые данные' }
  finally { generating.value = false }
}

onMounted(load)
</script>
