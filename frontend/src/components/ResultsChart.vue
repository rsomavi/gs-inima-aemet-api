<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from 'vue'
import Chart from 'chart.js/auto'
import type { Measurement } from '../types'

const props = defineProps<{
  results: Measurement[]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
let chartInstance: Chart | null = null

const VARIABLE_CONFIG = [
  { key: 'Temperature (ºC)', axisId: 'yTemp', color: 'rgb(54, 162, 235)' },
  { key: 'Pressure (hpa)', axisId: 'yPres', color: 'rgb(255, 99, 132)' },
  { key: 'Speed (m/s)', axisId: 'ySpeed', color: 'rgb(255, 159, 64)' },
] as const

function buildChart() {
  if (!canvasRef.value || props.results.length === 0) return

  const labels = props.results.map((row) => row.Datetime)

  const presentVariables = VARIABLE_CONFIG.filter((v) => v.key in props.results[0]!)

  const datasets = presentVariables.map((variable) => ({
    label: variable.key,
    data: props.results.map((row) => row[variable.key] ?? null),
    borderColor: variable.color,
    yAxisID: variable.axisId,
  }))

  const scales: Record<string, object> = {}
  presentVariables.forEach((variable, index) => {
    scales[variable.axisId] = {
      type: 'linear',
      position: index === 0 ? 'left' : 'right',
      title: { display: true, text: variable.key },
      grid: { drawOnChartArea: index === 0 },
    }
  })

  if (chartInstance) {
    chartInstance.destroy()
  }

  chartInstance = new Chart(canvasRef.value, {
    type: 'line',
    data: { labels, datasets },
    options: { scales },
  })
}

onMounted(buildChart)
watch(() => props.results, buildChart)
onUnmounted(() => chartInstance?.destroy())
</script>

<template>
  <canvas ref="canvasRef"></canvas>
</template>

<style scoped>
canvas {
  max-height: 380px;
}
</style>