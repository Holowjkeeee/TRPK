<template>
  <div>
    <div class="panel-card p-4 mb-3">
      <h2 class="h5">Добавить возрастно-весовую категорию</h2>
      <form class="row g-3" @submit.prevent="createCategory">
        <div class="col-md-5"><label class="form-label">Название</label><input v-model.trim="form.name" class="form-control" placeholder="Юноши 2012-2013, до 55 кг" required /></div>
        <div class="col-md-3"><label class="form-label">Возрастная группа</label><input v-model.trim="form.age_group" class="form-control" placeholder="Юноши 2012-2013" required /></div>
        <div class="col-md-2"><label class="form-label">С года</label><input v-model.number="form.birth_year_from" type="number" class="form-control" required /></div>
        <div class="col-md-2"><label class="form-label">По год</label><input v-model.number="form.birth_year_to" type="number" class="form-control" required /></div>
        <div class="col-md-3"><label class="form-label">Вес до, кг</label><input v-model.number="form.weight_limit" type="number" step="0.01" class="form-control" required /></div>
        <div class="col-md-3">
          <label class="form-label">Пол</label>
          <select v-model="form.gender" class="form-select"><option value="male">Мужской</option><option value="female">Женский</option></select>
        </div>
        <div class="col-md-3 d-flex align-items-end"><button type="submit" class="btn btn-success w-100" :disabled="saving">Добавить</button></div>
        <div class="col-md-3 d-flex align-items-end"><button type="button" class="btn btn-outline-primary w-100" :disabled="saving" @click="createWeightSet">Добавить набор весов</button></div>
      </form>
      <div v-if="error" class="alert alert-danger mt-3 mb-0">{{ error }}</div>
    </div>

    <div class="panel-card p-4">
      <h2 class="h5">Категории соревнования</h2>
      <div v-if="!categories.length" class="text-muted">Категории ещё не созданы.</div>
      <div v-else class="table-responsive">
        <table class="table table-sm">
          <thead><tr><th>Категория</th><th>Годы рождения</th><th>Вес</th><th>Пол</th><th>Ковёр</th><th>Допущено</th><th>Система</th><th></th></tr></thead>
          <tbody>
            <tr v-for="item in categories" :key="item.id">
              <td>{{ item.name }}</td>
              <td>{{ item.birth_year_from }}-{{ item.birth_year_to }}</td>
              <td>до {{ item.weight_limit }} кг</td>
              <td>{{ item.gender === 'female' ? 'Ж' : 'М' }}</td>
              <td>{{ item.mat_number ? `Ковёр ${item.mat_number}` : 'Не назначен' }}</td>
              <td>{{ item.admitted_count }}</td>
              <td>{{ item.system_type_display || 'Будет выбрана автоматически' }}</td>
              <td><button type="button" class="btn btn-outline-danger btn-sm" @click="remove(item)">Удалить</button></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http.js'

const route = useRoute()
const categories = ref([])
const saving = ref(false)
const error = ref('')
const form = reactive({ name: '', age_group: '', birth_year_from: 2012, birth_year_to: 2013, weight_limit: 55, gender: 'male', system_type: '', status: 'draft' })

async function load() {
  const response = await http.get('/categories/', { params: { competition_id: route.params.id } })
  categories.value = response.data
}

const defaultWeights = [32, 35, 38, 41, 44, 48, 52, 57, 62, 68, 75, 85, 92, 100, 110]

async function createWeightSet() {
  saving.value = true
  error.value = ''
  try {
    const response = await http.post('/categories/bulk-create/', {
      competition: Number(route.params.id),
      age_group: form.age_group || `Юноши ${form.birth_year_from}-${form.birth_year_to}`,
      birth_year_from: form.birth_year_from,
      birth_year_to: form.birth_year_to,
      gender: form.gender,
      weights: defaultWeights,
    })
    categories.value = response.data.categories
  } catch (e) {
    error.value = e.response?.data?.detail || 'Не удалось добавить набор весовых категорий'
  } finally { saving.value = false }
}

async function createCategory() {
  saving.value = true
  error.value = ''
  try {
    await http.post('/categories/', { ...form, competition: Number(route.params.id), system_type: form.system_type || '' })
    form.name = ''
    form.weight_limit = 55
    await load()
  } catch (e) {
    error.value = JSON.stringify(e.response?.data || 'Ошибка создания категории')
  } finally { saving.value = false }
}

async function remove(item) {
  if (!confirm(`Удалить категорию «${item.name}»?`)) return
  try {
    await http.delete(`/categories/${item.id}/`)
    await load()
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось удалить категорию' }
}

onMounted(async () => { try { await load() } catch { error.value = 'Ошибка загрузки категорий' } })
</script>
