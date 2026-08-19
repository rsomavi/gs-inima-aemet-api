<script setup lang="ts">
import { ref } from 'vue'
import QueryForm from './components/QueryForm.vue'
import ResultsTable from './components/ResultsTable.vue'
import ResultsChart from './components/ResultsChart.vue'
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
    <header class="page-header">
      <h1>Antarctica Weather Data</h1>
      <p>Historical measurements from AEMET's Antarctic weather stations.</p>
    </header>

    <div class="card">
      <h2>Query</h2>
      <QueryForm @query="handleQuery" />
    </div>

    <p v-if="isLoading" class="status-message loading">Loading data…</p>
    <p v-else-if="errorMessage" class="status-message error">{{ errorMessage }}</p>
    <p v-else-if="results && results.length === 0" class="status-message empty">
      No data found for this query.
    </p>
    <template v-else-if="results && results.length > 0">
      <div class="card">
        <h2>Chart</h2>
        <ResultsChart :results="results" />
      </div>
      <div class="card">
        <h2>Results</h2>
        <ResultsTable :results="results" />
      </div>
    </template>
  </main>
</template>