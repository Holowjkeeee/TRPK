<template>
  <div>
    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div class="row g-3 mb-4">
      <div class="col-md-3"><div class="panel-card p-4 stat-card"><div class="text-muted">Заявок</div><strong>{{ applications.length }}</strong></div></div>
      <div class="col-md-3"><div class="panel-card p-4 stat-card"><div class="text-muted">Спортсменов</div><strong>{{ participations.length }}</strong></div></div>
      <div class="col-md-3"><div class="panel-card p-4 stat-card"><div class="text-muted">Допущено</div><strong>{{ admitted }}</strong></div></div>
      <div class="col-md-3"><div class="panel-card p-4 stat-card"><div class="text-muted">Категорий</div><strong>{{ categories.length }}</strong></div></div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http.js'

const route = useRoute()
const applications = ref([])
const participations = ref([])
const categories = ref([])
const error = ref('')
const admitted = computed(() => participations.value.filter((x) => x.admission_status === 'admitted').length)

async function load() {
  try {
    const [apps, parts, cats] = await Promise.all([
      http.get('/applications/', { params: { competition_id: route.params.id } }),
      http.get('/participations/', { params: { competition_id: route.params.id } }),
      http.get('/categories/', { params: { competition_id: route.params.id } }),
    ])
    applications.value = apps.data
    participations.value = parts.data
    categories.value = cats.data
  } catch (e) {
    error.value = e.response?.data?.detail || 'Ошибка загрузки'
  }
}

onMounted(load)
</script>

