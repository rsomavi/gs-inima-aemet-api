<script setup lang="ts">
import QueryForm from './components/QueryForm.vue'
import type { QueryParams } from './api'

function handleQuery(params: QueryParams) {
  console.log('Query submitted:', params)
}
</script>

<template>
  <main>
    <h1>Antarctica Weather Data</h1>
    <QueryForm @query="handleQuery" />
  </main>
</template>