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
const location = ref('')
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
    location: location.value || undefined,
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

    <div>
      <label>
        Location (optional)
        <input v-model="location" type="text" placeholder="e.g. Europe/Berlin or +02:00" />
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

<style scoped>
form {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  font-size: 0.85rem;
  font-weight: 500;
  color: var(--color-text-muted);
}

input,
select {
  padding: 0.55rem 0.7rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  font-size: 0.95rem;
  color: var(--color-text);
}

input:focus,
select:focus {
  outline: 2px solid var(--color-primary);
  outline-offset: 1px;
}

fieldset {
  grid-column: 1 / -1;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 0.9rem 1.1rem;
}

legend {
  font-size: 0.85rem;
  color: var(--color-text-muted);
  padding: 0 0.4rem;
}

fieldset label {
  flex-direction: row;
  align-items: center;
  display: inline-flex;
  gap: 0.4rem;
  margin-right: 1.75rem;
  font-weight: 400;
  color: var(--color-text);
}

button {
  grid-column: 1 / -1;
  justify-self: start;
  padding: 0.65rem 1.75rem;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

button:hover {
  background: var(--color-primary-hover);
}
</style>