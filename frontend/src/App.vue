<script setup lang="ts">
import { ref } from 'vue'
import QueryForm from './components/QueryForm.vue'
import { fetchAntarcticaData, type QueryParams } from './api'
import type { Measurement } from './types'

const results = ref<Measurement[] | null>(null)
const isLoading = ref(false)
const errorMessage = ref<string | null>(null)

async function handleQuery(params: QueryParams) {
  isLoading.value = true
  errorMessage.value = null
  results.value = null

  try {
    results.value = await fetchAntarcticaData(params)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : 'Unknown error'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main>
    <h1>Antarctica Weather Data</h1>
    <QueryForm @query="handleQuery" />

    <p v-if="isLoading">Loading...</p>
    <p v-else-if="errorMessage" style="color: red">{{ errorMessage }}</p>
    <p v-else-if="results && results.length === 0">No data found for this query.</p>
    <pre v-else-if="results">{{ results }}</pre>
  </main>
</template>