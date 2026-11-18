<template>
  <section class="workspace-section protocol-page">
    <div class="section-heading mb-3 no-print">
      <div>
        <div class="section-label">Документы соревнования</div>
        <h2>Протокол соревнования</h2>
      </div>
      <div class="d-flex gap-2 flex-wrap">
        <button type="button" class="btn btn-ghost" :disabled="loading" @click="load">Обновить</button>
        <button type="button" class="btn btn-primary" :disabled="!data?.can_finalize || generating" @click="generateProtocol">
          {{ generating ? 'Формирование...' : data?.generated_protocol ? 'Сформировать заново' : 'Сформировать протокол' }}
        </button>
        <button type="button" v-if="data?.generated_protocol" class="btn btn-outline-primary" @click="downloadProtocol">Скачать DOCX</button>
        <button type="button" v-if="data?.generated_protocol" class="btn btn-outline-secondary" @click="printProtocol">Печать / PDF</button>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger no-print">{{ error }}</div>
    <div v-if="message" class="alert alert-success no-print">{{ message }}</div>
    <div v-if="loading" class="panel-card p-5 text-center text-muted">Загрузка...</div>

    <template v-else-if="data">
      <div v-if="!data.can_finalize" class="panel-card p-4 mb-3 protocol-blockers no-print">
        <div class="protocol-state-title">Протокол пока нельзя выпустить</div>
        <ul class="mb-0">
          <li v-for="issue in data.blocking_issues" :key="issue">{{ issue }}</li>
        </ul>
      </div>

      <article id="printable-protocol" class="protocol-document panel-card">
        <header class="protocol-header">
          <div class="protocol-kicker">ИТОГОВЫЙ ПРОТОКОЛ</div>
          <h1>{{ data.competition.name }}</h1>
          <div class="protocol-meta">
            <span>{{ formatDate(data.competition.date) }}</span>
            <span>{{ data.competition.venue }}</span>
            <span>{{ data.competition.mat_count }} ковра</span>
          </div>
        </header>

        <section class="protocol-summary-grid">
          <div><strong>{{ data.summary.categories_count }}</strong><span>категорий</span></div>
          <div><strong>{{ data.summary.admitted_count }}</strong><span>допущено</span></div>
          <div><strong>{{ data.summary.matches_count }}</strong><span>поединков</span></div>
          <div><strong>{{ data.summary.finished_matches_count }}</strong><span>завершено</span></div>
        </section>

        <section v-if="data.team_medals?.length" class="protocol-section">
          <h2>Командный медальный зачёт</h2>
          <div class="table-responsive">
            <table class="table protocol-table mb-0">
              <thead><tr><th>#</th><th>Команда</th><th>1 место</th><th>2 место</th><th>3 место</th><th>Всего</th></tr></thead>
              <tbody>
                <tr v-for="item in data.team_medals" :key="item.team">
                  <td>{{ item.place }}</td><td><strong>{{ item.team }}</strong></td><td>{{ item.gold }}</td><td>{{ item.silver }}</td><td>{{ item.bronze }}</td><td>{{ item.total }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-for="category in data.categories" :key="category.id" class="protocol-section category-protocol-section">
          <div class="protocol-category-head">
            <div>
              <h2>{{ category.name }}</h2>
              <div class="protocol-category-meta">{{ category.age_group }} · {{ category.system_type_display }}</div>
            </div>
            <span class="soft-pill">{{ category.finished_matches_count }}/{{ category.matches_count }} поединков</span>
          </div>

          <div v-if="category.podium?.length" class="protocol-podium">
            <div v-for="item in category.podium" :key="`${item.place}-${item.participation_id}-${item.branch || ''}`" class="protocol-medalist">
              <span>{{ item.place }}</span>
              <div><strong>{{ item.athlete }}</strong><small>{{ item.team }}<template v-if="item.branch"> · ветка {{ item.branch }}</template></small></div>
            </div>
          </div>

          <div v-if="category.standings?.length" class="table-responsive mt-3">
            <table class="table protocol-table mb-0">
              <thead><tr><th>Место</th><th>Спортсмен</th><th>Команда</th><th>Победы</th><th>Кл. очки</th><th>Баллы</th></tr></thead>
              <tbody>
                <tr v-for="row in category.standings" :key="row.participation_id">
                  <td>{{ row.place }}</td><td>{{ row.athlete }}</td><td>{{ row.team }}</td><td>{{ row.wins }}</td><td>{{ row.classification_points }}</td><td>{{ row.points_for }}:{{ row.points_against }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <details class="protocol-matches" :open="false">
            <summary>Результаты поединков ({{ category.finished_matches_count }})</summary>
            <div class="table-responsive mt-2">
              <table class="table protocol-table mb-0">
                <thead><tr><th>Этап</th><th>Красный</th><th>Счёт</th><th>Синий</th><th>Победитель</th><th>Способ победы</th></tr></thead>
                <tbody>
                  <tr v-for="match in finishedMatches(category)" :key="match.id">
                    <td>{{ match.stage_label }}</td>
                    <td>{{ match.red?.athlete || '-' }}</td>
                    <td>{{ match.score || '-' }}</td>
                    <td>{{ match.blue?.athlete || '-' }}</td>
                    <td>{{ match.winner?.athlete || '-' }}</td>
                    <td>{{ match.victory_method || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </details>
        </section>

        <footer class="protocol-footer">
          <span v-if="data.generated_protocol">Сформирован {{ formatDateTime(data.generated_protocol.generated_at) }} · {{ data.generated_protocol.generated_by }}</span>
          <span v-else>Предварительный просмотр</span>
        </footer>
      </article>
    </template>
  </section>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http.js'

const route = useRoute()
const data = ref(null)
const loading = ref(false)
const generating = ref(false)
const error = ref('')
const message = ref('')

function formatDate(value) {
  return value ? new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU') : '-'
}
function formatDateTime(value) {
  return value ? new Date(value).toLocaleString('ru-RU') : '-'
}
function finishedMatches(category) {
  return (category.matches || []).filter((match) => match.status === 'finished')
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    data.value = (await http.get(`/competitions/${route.params.id}/protocol/`)).data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Не удалось загрузить протокол'
  } finally {
    loading.value = false
  }
}

async function generateProtocol() {
  generating.value = true
  error.value = ''
  message.value = ''
  try {
    data.value = (await http.post(`/competitions/${route.params.id}/protocol/`)).data
    message.value = 'Итоговый протокол сформирован.'
  } catch (e) {
    data.value = e.response?.data?.competition ? e.response.data : data.value
    error.value = e.response?.data?.detail || 'Не удалось сформировать итоговый протокол'
  } finally {
    generating.value = false
  }
}

async function downloadProtocol() {
  error.value = ''
  try {
    const response = await http.get(`/competitions/${route.params.id}/protocol-download/`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = `Итоговый_протокол_${route.params.id}.docx`
    link.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = 'Не удалось скачать итоговый протокол'
  }
}

function printProtocol() {
  window.print()
}

onMounted(load)
</script>
