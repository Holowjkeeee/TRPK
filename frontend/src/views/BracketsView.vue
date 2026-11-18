<template>
  <section class="workspace-section">
    <div class="section-heading mb-3">
      <div>
        <div class="section-label">Сетка категории</div>
        <h2>Сетки и результаты</h2>
      </div>
      <button type="button" class="btn btn-ghost" @click="loadCategories">Обновить</button>
    </div>

    <div v-if="error" class="alert alert-danger">{{ error }}</div>
    <div v-if="message" class="alert alert-success">{{ message }}</div>

    <div class="category-picker panel-card mb-3">
      <div class="category-picker-copy">
        <span class="category-picker-label">Категория</span>
        <strong>{{ selectedCategory?.name || 'Выберите категорию' }}</strong>
        <small v-if="selectedCategory">{{ selectedCategory.admitted_count }} допущено · {{ selectedCategory.mat_number ? `ковёр ${selectedCategory.mat_number}` : 'ковёр не назначен' }}</small>
      </div>
      <select
        class="form-select category-select"
        :value="selectedCategoryId || ''"
        :disabled="loading || !categories.length"
        @change="selectCategory(Number($event.target.value))"
      >
        <option value="" disabled>Выберите возраст и вес</option>
        <optgroup v-for="group in groupedCategories" :key="group.ageGroup" :label="group.ageGroup">
          <option v-for="item in group.items" :key="item.id" :value="item.id">
            {{ item.weight_limit ? `до ${item.weight_limit} кг` : item.name }} · {{ item.admitted_count }} допущено{{ item.mat_number ? ` · ковёр ${item.mat_number}` : '' }}
          </option>
        </optgroup>
      </select>
    </div>

    <div v-if="selectedCategory" class="panel-card p-4 mb-3">
      <div class="d-flex flex-wrap justify-content-between align-items-center gap-3">
        <div>
          <div class="section-label">{{ selectedCategory.age_group }}</div>
          <h3 class="h4 mb-2">{{ selectedCategory.name }}</h3>
          <div class="d-flex flex-wrap gap-2">
            <span class="system-pill">{{ selectedCategory.system_type_display || 'Система не выбрана' }}</span>
            <span class="soft-pill">{{ selectedCategory.admitted_count }} спортсменов</span>
            <span v-if="selectedCategory.mat_number" class="soft-pill">Ковёр {{ selectedCategory.mat_number }}</span>
            <span class="soft-pill">{{ selectedCategory.matches_count }} поединков</span>
          </div>
        </div>
        <div class="d-flex gap-2 flex-wrap">
          <button type="button" class="btn btn-outline-primary" :disabled="busy || selectedCategory.admitted_count < 2" @click="generateBracket">
            {{ selectedCategory.bracket_generated ? 'Сформировать заново' : 'Сформировать сетку' }}
          </button>
          <button type="button" v-if="selectedCategory.bracket_generated && auth.user?.is_staff" class="btn btn-demo" :disabled="busy" @click="simulateResults">
            Заполнить тестовыми результатами
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="panel-card p-5 text-center text-muted">Загрузка...</div>

    <template v-else-if="bracket && bracket.matches?.length">
      <div v-if="selectedCategory.system_type === 'round_robin'" class="round-system-layout">
        <div class="stage-accordion-list">
          <details
            v-for="round in roundRobinRounds"
            :key="round.key"
            class="stage-accordion panel-card"
            :open="round.round === currentRoundNumber"
          >
            <summary>
              <span>{{ round.title }}</span>
              <small>{{ round.finished }}/{{ round.matches.length }}</small>
            </summary>
            <div class="stage-match-grid">
              <MatchCard v-for="match in round.matches" :key="match.id" :match="match" @result="openResult" />
            </div>
          </details>
        </div>
        <StandingsTable title="Текущая классификация" :rows="bracket.standings || []" />
      </div>

      <div v-else-if="selectedCategory.system_type === 'nordic'" class="nordic-layout">
        <section class="panel-card p-3">
          <div class="nordic-groups">
            <div v-for="group in nordicGroups" :key="group.label" class="nordic-group">
              <div class="group-title">Группа {{ group.label }}</div>
              <details
                v-for="round in group.rounds"
                :key="round.key"
                class="stage-accordion compact-accordion"
                :open="round.round === group.currentRound"
              >
                <summary>
                  <span>{{ round.title }}</span>
                  <small>{{ round.finished }}/{{ round.matches.length }}</small>
                </summary>
                <div class="stage-match-grid one-column">
                  <MatchCard v-for="match in round.matches" :key="match.id" :match="match" compact @result="openResult" />
                </div>
              </details>
            </div>
          </div>
        </section>

        <section class="panel-card p-3">
          <div class="group-title">Финальный этап</div>
          <details
            v-for="(section, index) in nordicFinalSections"
            :key="section.key"
            class="stage-accordion compact-accordion"
            :open="section.hasReady || index === 0"
          >
            <summary>
              <span>{{ section.title }}</span>
              <small>{{ section.finished }}/{{ section.matches.length }}</small>
            </summary>
            <div class="stage-match-grid one-column">
              <MatchCard v-for="match in section.matches" :key="match.id" :match="match" compact @result="openResult" />
            </div>
          </details>
        </section>

        <div class="nordic-standings">
          <StandingsTable title="Группа A" :rows="groupA" />
          <StandingsTable title="Группа B" :rows="groupB" />
        </div>
      </div>

      <div v-else class="elimination-layout">
        <details v-if="qualificationMatches.length" class="stage-accordion panel-card mb-3" open>
          <summary>
            <span>Квалификация</span>
            <small>{{ qualificationFinished }}/{{ qualificationMatches.length }}</small>
          </summary>
          <div class="stage-match-grid">
            <MatchCard v-for="match in qualificationMatches" :key="match.id" :match="match" @result="openResult" />
          </div>
        </details>

        <div class="elimination-tree-scroll panel-card">
          <div class="elimination-tree" :style="treeCanvasStyle">
            <svg class="tree-links" :width="treeWidth" :height="treeCanvasHeight" aria-hidden="true">
              <path v-for="link in treeLinks" :key="link.key" :d="link.path" />
            </svg>

            <div
              v-for="(round, roundIndex) in eliminationRounds"
              :key="round.key"
              class="tree-round-column"
              :style="treeRoundStyle(roundIndex)"
            >
              <div class="tree-round-title">{{ round.title }}</div>
              <div
                v-for="(match, matchIndex) in round.matches"
                :key="match.id"
                class="tree-match-shell"
                :style="treeMatchStyle(roundIndex, matchIndex)"
              >
                <MatchCard :match="match" compact @result="openResult" />
              </div>
            </div>
          </div>
        </div>

        <div v-if="repechageSections.length" class="repechage-grid mt-3">
          <details v-for="section in repechageSections" :key="section.key" class="stage-accordion panel-card" open>
            <summary>
              <span>{{ section.title }}</span>
              <small>{{ section.finished }}/{{ section.matches.length }}</small>
            </summary>
            <div class="stage-match-grid one-column">
              <MatchCard v-for="match in section.matches" :key="match.id" :match="match" compact @result="openResult" />
            </div>
          </details>
        </div>
      </div>

      <div v-if="bracket.podium?.length" class="panel-card p-4 mt-3">
        <div class="section-heading compact mb-3"><div><h3>Призовые места</h3></div></div>
        <div class="podium-grid">
          <div v-for="item in bracket.podium" :key="`${item.place}-${item.participation_id}-${item.branch || ''}`" class="podium-card" :class="`place-${item.place}`">
            <span class="podium-place">{{ item.place }}</span>
            <strong>{{ item.athlete }}</strong>
            <small>{{ item.team }}</small>
          </div>
        </div>
      </div>
    </template>

    <div v-else-if="selectedCategory" class="empty-state panel-card">
      <div class="empty-icon">◎</div>
      <h3>{{ selectedCategory.admitted_count >= 2 ? 'Сетка ещё не сформирована' : 'Недостаточно участников' }}</h3>
    </div>

    <div v-if="resultMatch" class="modal-backdrop-custom" @click.self="closeResult">
      <div class="result-dialog panel-card p-4">
        <div class="d-flex justify-content-between align-items-start gap-3 mb-3">
          <div><div class="eyebrow">{{ resultMatch.stage_label }}</div><h3 class="h4 mb-0">Результат поединка</h3></div>
          <button type="button" class="btn-close" @click="closeResult"></button>
        </div>

        <div class="result-fighters mb-4">
          <button type="button" class="result-fighter red" :class="{ selected: resultForm.winner_id === resultMatch.red?.id }" @click="resultForm.winner_id = resultMatch.red?.id">
            <span>Красный угол</span><strong>{{ resultMatch.red?.athlete?.full_name }}</strong><small>{{ resultMatch.red?.team?.name }}</small>
          </button>
          <div class="result-vs">VS</div>
          <button type="button" class="result-fighter blue" :class="{ selected: resultForm.winner_id === resultMatch.blue?.id }" @click="resultForm.winner_id = resultMatch.blue?.id">
            <span>Синий угол</span><strong>{{ resultMatch.blue?.athlete?.full_name }}</strong><small>{{ resultMatch.blue?.team?.name }}</small>
          </button>
        </div>

        <div class="row g-3">
          <div class="col-6"><label class="form-label">Баллы красного</label><input v-model.number="resultForm.red_score" min="0" type="number" class="form-control form-control-lg" /></div>
          <div class="col-6"><label class="form-label">Баллы синего</label><input v-model.number="resultForm.blue_score" min="0" type="number" class="form-control form-control-lg" /></div>
          <div class="col-12">
            <label class="form-label">Способ победы</label>
            <select v-model="resultForm.victory_method" class="form-select form-select-lg">
              <option value="points">По баллам</option>
              <option value="technical_superiority">Техническое превосходство</option>
              <option value="fall">Туше</option>
              <option value="no_show">Неявка</option>
              <option value="medical_forfeit">Медицинское снятие</option>
              <option value="disqualification">Дисквалификация</option>
            </select>
          </div>
        </div>
        <div class="d-flex justify-content-end gap-2 mt-4">
          <button type="button" class="btn btn-ghost" @click="closeResult">Отмена</button>
          <button type="button" class="btn btn-primary" :disabled="!resultForm.winner_id || busy" @click="saveResult">Зафиксировать результат</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, defineComponent, h, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth.js'
import http from '../api/http.js'
import MatchCard from '../components/MatchCard.vue'

const route = useRoute()
const auth = useAuthStore()
const categories = ref([])
const selectedCategoryId = ref(null)
const bracket = ref(null)
const loading = ref(false)
const busy = ref(false)
const error = ref('')
const message = ref('')
const groupA = ref([])
const groupB = ref([])
const resultMatch = ref(null)
const resultForm = reactive({ winner_id: null, red_score: 0, blue_score: 0, victory_method: 'points' })

const TREE_UNIT = 205
const TREE_CARD_HEIGHT = 172
const TREE_COLUMN_WIDTH = 300
const TREE_COLUMN_GAP = 80
const TREE_HEADER = 54

const selectedCategory = computed(() => categories.value.find((x) => x.id === selectedCategoryId.value) || null)
const groupedCategories = computed(() => {
  const groups = new Map()
  for (const item of categories.value) {
    const ageGroup = item.age_group || 'Без возрастной группы'
    if (!groups.has(ageGroup)) groups.set(ageGroup, [])
    groups.get(ageGroup).push(item)
  }
  return [...groups.entries()].map(([ageGroup, items]) => ({
    ageGroup,
    items: items.slice().sort((a, b) => (a.weight_limit ?? 999) - (b.weight_limit ?? 999) || a.name.localeCompare(b.name, 'ru')),
  }))
})
const matches = computed(() => bracket.value?.matches || [])

function makeRounds(items, titleFactory) {
  const groups = new Map()
  for (const match of items) {
    const round = match.round_number
    if (!groups.has(round)) groups.set(round, [])
    groups.get(round).push(match)
  }
  return [...groups.entries()].sort((a, b) => a[0] - b[0]).map(([round, roundMatches]) => ({
    key: `round-${round}`,
    round,
    title: titleFactory(round, roundMatches),
    matches: roundMatches.sort((a, b) => a.order_index - b.order_index),
    finished: roundMatches.filter((x) => x.status === 'finished').length,
  }))
}

const roundRobinRounds = computed(() => makeRounds(matches.value.filter((x) => x.stage === 'round_robin'), (round) => `${round} круг`))
const currentRoundNumber = computed(() => {
  const current = roundRobinRounds.value.find((round) => round.matches.some((match) => match.status !== 'finished'))
  return current?.round || roundRobinRounds.value.at(-1)?.round || 1
})

function nordicGroup(label) {
  const rounds = makeRounds(matches.value.filter((x) => x.stage === 'group' && x.group_label === label), (round) => `${round} тур`)
  const current = rounds.find((round) => round.matches.some((match) => match.status !== 'finished'))
  return { label, rounds, currentRound: current?.round || rounds.at(-1)?.round || 1 }
}

const nordicGroups = computed(() => [nordicGroup('A'), nordicGroup('B')])
const nordicFinalSections = computed(() => {
  const definitions = [
    { key: 'semifinal', title: 'Полуфиналы', stages: ['semifinal'] },
    { key: 'final', title: 'Финал', stages: ['final'] },
    { key: 'bronze', title: 'За 3 место', stages: ['bronze'] },
  ]
  return definitions.map((definition) => {
    const sectionMatches = matches.value.filter((match) => definition.stages.includes(match.stage)).sort((a, b) => a.order_index - b.order_index)
    return {
      ...definition,
      matches: sectionMatches,
      finished: sectionMatches.filter((x) => x.status === 'finished').length,
      hasReady: sectionMatches.some((x) => x.status === 'ready'),
    }
  }).filter((section) => section.matches.length)
})

const qualificationMatches = computed(() => matches.value.filter((x) => x.stage === 'qualification').sort((a, b) => a.order_index - b.order_index))
const qualificationFinished = computed(() => qualificationMatches.value.filter((x) => x.status === 'finished').length)

const eliminationRounds = computed(() => {
  const mainMatches = matches.value.filter((x) => ['main', 'semifinal', 'final'].includes(x.stage) && x.round_number > 0)
  const grouped = makeRounds(mainMatches, (_round, roundMatches) => roundMatches[0]?.stage_label || 'Раунд')
  return grouped.map((group) => ({ ...group, key: `tree-${group.round}` }))
})

const treeHeight = computed(() => Math.max(1, eliminationRounds.value[0]?.matches.length || 1) * TREE_UNIT)
const treeCanvasHeight = computed(() => treeHeight.value + TREE_HEADER + 18)
const treeWidth = computed(() => Math.max(1, eliminationRounds.value.length) * TREE_COLUMN_WIDTH + Math.max(0, eliminationRounds.value.length - 1) * TREE_COLUMN_GAP)
const treeCanvasStyle = computed(() => ({ width: `${treeWidth.value}px`, height: `${treeCanvasHeight.value}px` }))

function treeRoundStyle(roundIndex) {
  return {
    left: `${roundIndex * (TREE_COLUMN_WIDTH + TREE_COLUMN_GAP)}px`,
    width: `${TREE_COLUMN_WIDTH}px`,
    height: `${treeCanvasHeight.value}px`,
  }
}

function treeCenter(roundIndex, matchIndex) {
  const span = 2 ** roundIndex
  return TREE_HEADER + (matchIndex + 0.5) * span * TREE_UNIT
}

function treeMatchStyle(roundIndex, matchIndex) {
  return { top: `${treeCenter(roundIndex, matchIndex) - TREE_CARD_HEIGHT / 2}px` }
}

const treeLinks = computed(() => {
  const positions = new Map()
  eliminationRounds.value.forEach((round, roundIndex) => {
    round.matches.forEach((match, matchIndex) => positions.set(match.id, { roundIndex, matchIndex }))
  })
  const links = []
  for (const [matchId, source] of positions.entries()) {
    const match = eliminationRounds.value[source.roundIndex].matches[source.matchIndex]
    if (!match.next_match || !positions.has(match.next_match)) continue
    const target = positions.get(match.next_match)
    const x1 = source.roundIndex * (TREE_COLUMN_WIDTH + TREE_COLUMN_GAP) + TREE_COLUMN_WIDTH
    const y1 = treeCenter(source.roundIndex, source.matchIndex)
    const x2 = target.roundIndex * (TREE_COLUMN_WIDTH + TREE_COLUMN_GAP)
    const y2 = treeCenter(target.roundIndex, target.matchIndex)
    const mid = x1 + (x2 - x1) / 2
    links.push({ key: `${matchId}-${match.next_match}`, path: `M ${x1} ${y1} H ${mid} V ${y2} H ${x2}` })
  }
  return links
})

const repechageSections = computed(() => {
  const relevant = matches.value.filter((x) => ['repechage', 'bronze'].includes(x.stage))
  const groups = new Map()
  for (const match of relevant) {
    const branch = match.branch_label || 'N'
    if (!groups.has(branch)) groups.set(branch, [])
    groups.get(branch).push(match)
  }
  return [...groups.entries()].sort(([a], [b]) => a.localeCompare(b)).map(([branch, branchMatches]) => ({
    key: branch,
    title: branch === 'N' ? 'Встреча за 3 место' : `Утешительная ветка ${branch}`,
    matches: branchMatches.sort((a, b) => a.order_index - b.order_index),
    finished: branchMatches.filter((x) => x.status === 'finished').length,
  }))
})

const StandingsTable = defineComponent({
  props: { title: String, rows: Array },
  setup(props) {
    return () => h('div', { class: 'panel-card p-4 h-100' }, [
      h('div', { class: 'section-heading compact mb-3' }, [h('div', {}, [h('h3', {}, props.title)])]),
      !props.rows?.length ? h('div', { class: 'text-muted' }, 'Нет результатов') :
        h('div', { class: 'table-responsive' }, [h('table', { class: 'table modern-table mb-0' }, [
          h('thead', {}, [h('tr', {}, ['#', 'Спортсмен', 'В', 'Кл. очки', 'Баллы', '+/−'].map((x) => h('th', {}, x)))]),
          h('tbody', {}, props.rows.map((row) => h('tr', {}, [
            h('td', { class: 'fw-bold' }, String(row.place)), h('td', {}, [h('strong', {}, row.athlete), h('div', { class: 'small text-muted' }, row.team)]),
            h('td', {}, String(row.wins)), h('td', {}, String(row.classification_points)), h('td', {}, `${row.points_for}:${row.points_against}`), h('td', {}, String(row.score_difference)),
          ]))),
        ])]),
    ])
  },
})

async function loadCategories() {
  error.value = ''
  try {
    const response = await http.get('/categories/', { params: { competition_id: route.params.id } })
    categories.value = response.data
    if (!selectedCategoryId.value && categories.value.length) selectedCategoryId.value = categories.value[0].id
    if (selectedCategoryId.value) await loadBracket()
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось загрузить категории' }
}

async function selectCategory(id) {
  selectedCategoryId.value = id
  await loadBracket()
}

async function loadBracket() {
  if (!selectedCategoryId.value) return
  loading.value = true
  error.value = ''
  groupA.value = []
  groupB.value = []
  try {
    const response = await http.get(`/categories/${selectedCategoryId.value}/bracket/`)
    bracket.value = response.data
    const index = categories.value.findIndex((x) => x.id === selectedCategoryId.value)
    if (index >= 0) categories.value[index] = response.data.category
    if (response.data.category.system_type === 'nordic' && response.data.matches?.length) {
      const [a, b] = await Promise.all([
        http.get(`/categories/${selectedCategoryId.value}/standings/`, { params: { group: 'A' } }),
        http.get(`/categories/${selectedCategoryId.value}/standings/`, { params: { group: 'B' } }),
      ])
      groupA.value = a.data
      groupB.value = b.data
    }
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось загрузить сетку' }
  finally { loading.value = false }
}

async function generateBracket() {
  if (selectedCategory.value?.bracket_generated && !confirm('Сформировать сетку заново? Текущая незавершённая сетка будет удалена.')) return
  busy.value = true
  error.value = ''
  message.value = ''
  try {
    const response = await http.post(`/categories/${selectedCategoryId.value}/generate-bracket/`)
    const index = categories.value.findIndex((x) => x.id === response.data.id)
    if (index >= 0) categories.value[index] = response.data
    message.value = `Сетка сформирована: ${response.data.system_type_display}.`
    await loadBracket()
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось сформировать сетку' }
  finally { busy.value = false }
}

async function simulateResults() {
  if (!confirm('Заполнить тестовыми результатами все доступные поединки категории?')) return
  busy.value = true
  error.value = ''
  try {
    const response = await http.post(`/categories/${selectedCategoryId.value}/simulate-results/`)
    bracket.value = response.data
    message.value = 'Тестовые результаты заполнены.'
    await loadCategories()
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось заполнить результаты' }
  finally { busy.value = false }
}

function openResult(match) {
  resultMatch.value = match
  resultForm.winner_id = null
  resultForm.red_score = 0
  resultForm.blue_score = 0
  resultForm.victory_method = 'points'
}

function closeResult() { resultMatch.value = null }

async function saveResult() {
  busy.value = true
  error.value = ''
  try {
    await http.post(`/matches/${resultMatch.value.id}/result/`, { ...resultForm })
    closeResult()
    await loadBracket()
  } catch (e) { error.value = e.response?.data?.detail || 'Не удалось зафиксировать результат' }
  finally { busy.value = false }
}

onMounted(loadCategories)
</script>
