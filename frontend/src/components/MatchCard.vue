<template>
  <article class="match-card" :class="[`match-${match.status}`, { compact }]">
    <div class="match-meta">
      <span>{{ match.stage_label }}</span>
      <span v-if="match.mat_number">Ковёр {{ match.mat_number }} · {{ match.scheduled_order }}</span>
    </div>

    <div class="corner corner-red" :class="{ winner: match.winner?.id === match.red?.id }">
      <div class="corner-mark">R</div>
      <div class="fighter">
        <strong>{{ match.red?.athlete?.full_name || 'Ожидается участник' }}</strong>
        <small>{{ match.red?.team?.name || '-' }}<template v-if="match.red?.draw_number"> · №{{ match.red.draw_number }}</template></small>
      </div>
      <div class="score">{{ match.red_score ?? '-' }}</div>
    </div>

    <div class="corner corner-blue" :class="{ winner: match.winner?.id === match.blue?.id }">
      <div class="corner-mark">B</div>
      <div class="fighter">
        <strong>{{ match.blue?.athlete?.full_name || 'Ожидается участник' }}</strong>
        <small>{{ match.blue?.team?.name || '-' }}<template v-if="match.blue?.draw_number"> · №{{ match.blue.draw_number }}</template></small>
      </div>
      <div class="score">{{ match.blue_score ?? '-' }}</div>
    </div>

    <div class="match-footer">
      <div class="match-state">
        <span class="match-status" :class="`status-${match.status}`">{{ match.status_display }}</span>
        <span v-if="match.victory_method_display" class="method-label">{{ match.victory_method_display }}</span>
      </div>
      <button
        v-if="match.status === 'ready'"
        class="btn match-action-btn"
        type="button"
        @click="$emit('result', match)"
      >
        Внести результат
      </button>
    </div>
  </article>
</template>

<script setup>
defineProps({
  match: { type: Object, required: true },
  compact: { type: Boolean, default: false },
})
defineEmits(['result'])
</script>
