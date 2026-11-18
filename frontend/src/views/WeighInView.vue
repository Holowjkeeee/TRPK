<template>
  <div class="panel-card p-4">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h2 class="h5 mb-1">Контроль весовой категории и допуск</h2>
              </div>
      <button type="button" class="btn btn-outline-secondary btn-sm" @click="load">Обновить</button>
    </div>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="message" class="alert alert-success">{{ message }}</div>
    <div v-if="!rows.length" class="text-muted">Сначала импортируйте заявку Word.</div>

    <div v-else class="table-responsive">
      <table class="table table-sm align-middle">
        <thead>
          <tr>
            <th>Спортсмен</th><th>Команда</th><th>Заявленная категория</th><th>Документы</th><th>Мед. виза</th><th>Страховка</th>
            <th>Результат взвешивания</th><th>Итоговая категория</th><th>Допуск</th><th style="min-width:300px">Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in rows" :key="row.id">
            <td>{{ row.athlete.full_name }}<div class="small text-muted">{{ row.athlete.effective_birth_year || '-' }}</div></td>
            <td>{{ row.team?.name || '-' }}</td>
            <td>{{ row.declared_category?.name || row.declared_category_label || 'Не распознана' }}</td>
            <td class="text-center"><input v-model="row._documents_checked" type="checkbox" class="form-check-input" @change="saveDocuments(row)" /></td>
            <td class="text-center"><input v-model="row._medical_clearance" type="checkbox" class="form-check-input" @change="saveDocuments(row)" /></td>
            <td class="text-center"><input v-model="row._insurance_checked" type="checkbox" class="form-check-input" @change="saveDocuments(row)" /></td>
            <td><span class="badge" :class="weighBadge(row.weigh_in_status)">{{ row.weigh_in_status_display }}</span><div v-if="row.weigh_in_comment" class="small text-muted mt-1">{{ row.weigh_in_comment }}</div></td>
            <td>{{ row.confirmed_category?.name || '-' }}</td>
            <td><span class="badge" :class="admissionBadge(row.admission_status)">{{ row.admission_status_display }}</span></td>
            <td>
              <div class="d-flex flex-wrap gap-1">
                <button type="button" class="btn btn-success btn-sm" :disabled="!row.declared_category" @click="confirmCategory(row)">✓ Соответствует</button>
                <button type="button" class="btn btn-warning btn-sm" @click="openTransfer(row)">↔ Перенести</button>
                <button type="button" class="btn btn-outline-warning btn-sm" @click="markTransferRequired(row)">Обсудить перенос</button>
                <button type="button" class="btn btn-outline-danger btn-sm" @click="reject(row)">Не допустить</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="transferRow" class="modal-backdrop-custom">
      <div class="panel-card p-4 transfer-dialog">
        <h3 class="h5">Перенос спортсмена</h3>
        <p class="mb-2"><strong>{{ transferRow.athlete.full_name }}</strong></p>
        <p class="small text-muted">Заявлено: {{ transferRow.declared_category?.name || transferRow.declared_category_label || '-' }}</p>
        <label class="form-label">Новая категория</label>
        <select v-model="transferCategoryId" class="form-select mb-3">
          <option value="">Выберите категорию</option>
          <option v-for="item in transferCategories" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
        <label class="form-label">Комментарий</label>
        <input v-model.trim="transferComment" class="form-control mb-3" placeholder="Например: перенос согласован с представителем команды" />
        <div class="d-flex justify-content-end gap-2">
          <button type="button" class="btn btn-outline-secondary" @click="closeTransfer">Отмена</button>
          <button type="button" class="btn btn-primary" :disabled="!transferCategoryId" @click="confirmTransfer">Подтвердить перенос</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import http from '../api/http.js'

const route = useRoute()
const rows = ref([])
const error = ref('')
const message = ref('')
const transferRow = ref(null)
const transferCategories = ref([])
const transferCategoryId = ref('')
const transferComment = ref('')

function admissionBadge(status) {
  return status === 'admitted' ? 'text-bg-success' : status === 'rejected' ? 'text-bg-danger' : 'text-bg-secondary'
}

function weighBadge(status) {
  return {
    matched: 'text-bg-success', transferred: 'text-bg-primary', transfer_required: 'text-bg-warning', rejected: 'text-bg-danger', pending: 'text-bg-secondary',
  }[status] || 'text-bg-secondary'
}

function hydrate(item) {
  return { ...item, _documents_checked: item.documents_checked, _medical_clearance: item.medical_clearance, _insurance_checked: item.insurance_checked }
}

async function load() {
  error.value = ''
  try {
    const response = await http.get('/participations/', { params: { competition_id: route.params.id } })
    rows.value = response.data.map(hydrate)
  } catch (e) { error.value = e.response?.data?.detail || 'Ошибка загрузки' }
}

async function saveDocuments(row) {
  try {
    const response = await http.patch(`/participations/${row.id}/documents/`, {
      documents_checked: row._documents_checked,
      medical_clearance: row._medical_clearance,
      insurance_checked: row._insurance_checked,
    })
    Object.assign(row, hydrate(response.data))
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось сохранить проверку документов' }
}

async function confirmCategory(row) {
  error.value = ''
  try {
    const response = await http.post(`/participations/${row.id}/confirm-category/`)
    Object.assign(row, hydrate(response.data))
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось подтвердить категорию' }
}

async function markTransferRequired(row) {
  const comment = prompt('Комментарий:', 'Не соответствует заявленной категории, требуется согласовать перенос')
  if (comment === null) return
  try {
    const response = await http.post(`/participations/${row.id}/needs-transfer/`, { comment })
    Object.assign(row, hydrate(response.data))
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось изменить статус' }
}

async function openTransfer(row) {
  error.value = ''
  try {
    const response = await http.get(`/participations/${row.id}/transfer-categories/`)
    transferRow.value = row
    transferCategories.value = response.data
    transferCategoryId.value = ''
    transferComment.value = 'Перенос согласован с представителем команды'
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось получить категории' }
}

function closeTransfer() {
  transferRow.value = null
  transferCategories.value = []
  transferCategoryId.value = ''
  transferComment.value = ''
}

async function confirmTransfer() {
  try {
    const response = await http.post(`/participations/${transferRow.value.id}/transfer/`, {
      category_id: Number(transferCategoryId.value), comment: transferComment.value,
    })
    Object.assign(transferRow.value, hydrate(response.data))
    closeTransfer()
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось выполнить перенос' }
}

async function reject(row) {
  const reason = prompt('Причина недопуска:', 'Не выполнены условия допуска')
  if (reason === null) return
  try {
    const response = await http.post(`/participations/${row.id}/reject/`, { reason })
    Object.assign(row, hydrate(response.data))
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось изменить статус' }
}

onMounted(load)
</script>

<style scoped>
.modal-backdrop-custom { position: fixed; inset: 0; background: rgba(0,0,0,.35); z-index: 1050; display: flex; align-items: center; justify-content: center; padding: 1rem; }
.transfer-dialog { width: min(560px, 100%); box-shadow: 0 1rem 3rem rgba(0,0,0,.25); }
</style>
