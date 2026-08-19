<script setup lang="ts">
import { computed } from 'vue'
import type { Measurement } from '../types'

const props = defineProps<{
  results: Measurement[]
}>()

const columns = computed(() => {
  if (props.results.length === 0) return []
  return Object.keys(props.results[0])
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