<template>
  <div>
    <div class="panel-card p-4 mb-3">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <h2 class="h5 mb-1">Заявки команд</h2>
                  </div>
        <button type="button" class="btn btn-outline-primary" @click="downloadTemplate">Скачать шаблон Word</button>
      </div>

      <hr />

      <form class="row g-3 align-items-end" @submit.prevent="uploadApplication">
        <div class="col-md-8">
          <label class="form-label">Заполненная заявка .docx</label>
          <input ref="fileInput" class="form-control" type="file" accept=".docx" @change="onFileChange" required />
        </div>
        <div class="col-md-4">
          <button type="button" class="btn btn-success w-100" :disabled="uploading || !selectedFile">
            {{ uploading ? 'Импорт...' : 'Импортировать заявку' }}
          </button>
        </div>
      </form>

      <div v-if="importResult" class="alert mt-3 mb-0" :class="importResult.error_rows || importResult.duplicate_rows ? 'alert-warning' : 'alert-success'">
        <strong>{{ importResult.original_name }}</strong><br />
        Импортировано: {{ importResult.imported_rows }}, дубликатов: {{ importResult.duplicate_rows }}, ошибок: {{ importResult.error_rows }}.
        <ul v-if="importResult.errors?.length" class="mb-0 mt-2">
          <li v-for="item in importResult.errors" :key="`${item.row}-${item.error}`">Строка {{ item.row }}: {{ item.error }}</li>
        </ul>
      </div>
      <div v-if="error" class="alert alert-danger mt-3 mb-0">{{ error }}</div>
    </div>

    <div class="panel-card p-4 mb-3">
      <h2 class="h5">История импортов</h2>
      <div v-if="!applications.length" class="text-muted">Заявки ещё не импортировались.</div>
      <div v-else class="table-responsive">
        <table class="table table-sm">
          <thead><tr><th>Файл</th><th>Команда</th><th>Статус</th><th>Импортировано</th><th>Дубли</th><th>Ошибки</th></tr></thead>
          <tbody>
            <tr v-for="item in applications" :key="item.id">
              <td>{{ item.original_name }}</td>
              <td>{{ item.team?.name || '-' }}</td>
              <td>{{ item.status_display }}</td>
              <td>{{ item.imported_rows }}</td>
              <td>{{ item.duplicate_rows }}</td>
              <td>{{ item.error_rows }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="panel-card p-4">
      <h2 class="h5">Предварительный список спортсменов</h2>
      <div v-if="!participations.length" class="text-muted">После импорта здесь появятся спортсмены.</div>
      <div v-else class="table-responsive">
        <table class="table table-sm">
          <thead><tr><th>Спортсмен</th><th>Год рождения</th><th>Команда</th><th>Заявленная категория</th><th>Проверка данных</th><th>Допуск</th></tr></thead>
          <tbody>
            <tr v-for="item in participations" :key="item.id">
              <td>{{ item.athlete.full_name }}</td>
              <td>{{ item.athlete.effective_birth_year || '-' }}</td>
              <td>{{ item.team?.name || '-' }}</td>
              <td>{{ item.declared_category?.name || item.declared_category_label || '-' }}</td>
              <td><span class="badge" :class="item.review_status === 'ok' ? 'text-bg-success' : 'text-bg-warning'">{{ item.review_status_display }}</span></td>
              <td>{{ item.admission_status_display }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http.js'

const route = useRoute()
const applications = ref([])
const participations = ref([])
const selectedFile = ref(null)
const fileInput = ref(null)
const uploading = ref(false)
const importResult = ref(null)
const error = ref('')

function onFileChange(event) {
  selectedFile.value = event.target.files?.[0] || null
}

async function load() {
  const [apps, parts] = await Promise.all([
    http.get('/applications/', { params: { competition_id: route.params.id } }),
    http.get('/participations/', { params: { competition_id: route.params.id } }),
  ])
  applications.value = apps.data
  participations.value = parts.data
}

async function downloadTemplate() {
  error.value = ''
  try {
    const response = await http.get(`/competitions/${route.params.id}/application-template/`, { responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const a = document.createElement('a')
    a.href = url
    a.download = `Заявка_соревнование_${route.params.id}.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    error.value = 'Не удалось скачать шаблон Word'
  }
}

async function uploadApplication() {
  if (!selectedFile.value) return
  uploading.value = true
  error.value = ''
  importResult.value = null
  try {
    const data = new FormData()
    data.append('file', selectedFile.value)
    const response = await http.post(`/competitions/${route.params.id}/import-application/`, data)
    importResult.value = response.data
    selectedFile.value = null
    if (fileInput.value) fileInput.value.value = ''
    await load()
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка импорта заявки'
  } finally {
    uploading.value = false
  }
}

onMounted(async () => {
  try { await load() } catch (e) { error.value = 'Ошибка загрузки данных' }
})
</script>
