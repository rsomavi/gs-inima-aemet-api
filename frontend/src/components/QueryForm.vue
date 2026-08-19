<script setup lang="ts">
import { ref } from 'vue'
import { STATIONS, type AggregationLevel, type FieldName, type StationCode } from '../types'
import type { QueryParams } from '../api'

const emit = defineEmits<{
  query: [params: QueryParams]
}>()

const fechaIni = ref('2026-01-15T00:00')
const fechaFin = ref('2026-01-15T01:00')
const estacion = ref<StationCode>('89070')
const aggregation = ref<AggregationLevel>('none')
const selectedFields = ref<Set<FieldName>>(new Set())

function toggleField(field: FieldName) {
  if (selectedFields.value.has(field)) {
    selectedFields.value.delete(field)
  } else {
    selectedFields.value.add(field)
  }
}

function handleSubmit() {
  emit('query', {
    fechaIni: fechaIni.value + ':00',
    fechaFin: fechaFin.value + ':00',
    estacion: estacion.value,
    aggregation: aggregation.value,
    fields: Array.from(selectedFields.value),
  })
}
</script>

<template>
  <form @submit.prevent="handleSubmit">
    <div>
      <label>
        Start date/time
        <input v-model="fechaIni" type="datetime-local" required />
      </label>
    </div>

    <div>
      <label>
        End date/time
        <input v-model="fechaFin" type="datetime-local" required />
      </label>
    </div>

    <div>
      <label>
        Station
        <select v-model="estacion">
          <option v-for="(name, code) in STATIONS" :key="code" :value="code">
            {{ name }}
          </option>
        </select>
      </label>
    </div>

    <div>
      <label>
        Aggregation
        <select v-model="aggregation">
          <option value="none">None</option>
          <option value="hourly">Hourly</option>
          <option value="daily">Daily</option>
          <option value="monthly">Monthly</option>
        </select>
      </label>
    </div>

    <fieldset>
      <legend>Variables (none selected = all)</legend>
      <label>
        <input
          type="checkbox"
          :checked="selectedFields.has('temperature')"
          @change="toggleField('temperature')"
        />
        Temperature
      </label>
      <label>
        <input
          type="checkbox"
          :checked="selectedFields.has('pressure')"
          @change="toggleField('pressure')"
        />
        Pressure
      </label>
      <label>
        <input
          type="checkbox"
          :checked="selectedFields.has('speed')"
          @change="toggleField('speed')"
        />
        Speed
      </label>
    </fieldset>

    <button type="submit">Query</button>
  </form>
</template>