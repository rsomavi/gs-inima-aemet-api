<script setup lang="ts">
import { computed } from 'vue'
import type { Measurement } from '../types'

const props = defineProps<{
  results: Measurement[]
}>()

const columns = computed(() => {
  if (props.results.length === 0) return []
  return Object.keys(props.results[0]!)
})
</script>

<template>
  <table>
    <thead>
      <tr>
        <th v-for="column in columns" :key="column">{{ column }}</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="(row, index) in results" :key="index">
        <td v-for="column in columns" :key="column">
          {{ row[column as keyof Measurement] ?? '-' }}
        </td>
      </tr>
    </tbody>
  </table>
</template>

<style scoped>
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

th,
td {
  padding: 0.65rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid var(--color-border);
}

th {
  color: var(--color-text-muted);
  font-weight: 600;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

tbody tr:hover {
  background: var(--color-bg-soft);
}

tbody tr:last-child td {
  border-bottom: none;
}
</style>