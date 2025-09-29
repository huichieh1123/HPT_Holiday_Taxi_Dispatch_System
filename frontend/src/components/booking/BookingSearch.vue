<template>
  <div>
    <!-- Get by Booking Reference -->
    <div class="controls ref-search">
      <div class="ref-input">
        <label for="bookingRef">Get by Booking Reference:</label>
        <input
          type="text"
          id="bookingRef"
          v-model="bookingRefInput"
          placeholder="Enter booking reference"
          @keyup.enter="emitSearchByRef"
        />
      </div>
      <button @click="emitSearchByRef" :disabled="directFetchLoading">
        {{ directFetchLoading ? 'Loading...' : 'Get Details' }}
      </button>
    </div>

    <!-- Date Range Selection -->
    <div class="controls">
      <div class="date-picker">
        <label for="dateFrom">From:</label>
        <input type="datetime-local" id="dateFrom" v-model="dateFrom" />
      </div>
      <button @click="emitSearchByDates" :disabled="loading || !dateFrom">
        {{ loading ? 'Loading...' : 'Get Bookings' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';

defineProps<{ 
  loading: boolean;
  directFetchLoading: boolean;
}>();

const emit = defineEmits<{ 
  (e: 'search-by-ref', ref: string): void;
  (e: 'search-by-dates', dates: { from: string; to: string }): void;
}>();

const bookingRefInput = ref('');
const dateFrom = ref('');

function toSupplierDT(d: Date): string {
  const y = d.getUTCFullYear();
  const m = String(d.getUTCMonth() + 1).padStart(2, '0');
  const day = String(d.getUTCDate()).padStart(2, '0');
  const hh = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  const ss = String(d.getUTCSeconds()).padStart(2, '0');
  return `${y}-${m}-${day}T${hh}:${mm}:${ss}`; // ← 無 Z
}

const emitSearchByRef = () => {
  if (bookingRefInput.value.trim()) {
    emit('search-by-ref', bookingRefInput.value.trim());
  }
};

const emitSearchByDates = () => {
  if (dateFrom.value) {
    const from = new Date(dateFrom.value);
    const to = new Date(); // Use current time for 'to'
    emit('search-by-dates', {
      from: toSupplierDT(from),
      to: toSupplierDT(to),
    });
  }
};
</script>

<style scoped>
.controls {
  display: flex;
  gap: 20px;
  align-items: center;
  margin-bottom: 20px;
  background-color: #f9f9f9;
  padding: 15px;
  border-radius: 8px;
}

.ref-search {
  margin-bottom: 10px;
}

.ref-input {
  display: flex;
  flex-direction: column;
  flex-grow: 1;
}

.ref-input label {
  font-size: 0.9em;
  margin-bottom: 5px;
  color: #555;
}

.ref-input input {
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.date-picker {
  display: flex;
  flex-direction: column;
}

.date-picker label {
  font-size: 0.9em;
  margin-bottom: 5px;
  color: #555;
}

input[type="datetime-local"] {
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

button {
  padding: 10px 20px;
  border: none;
  background-color: #007bff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}

@media (max-width: 768px) {
  .controls {
    flex-direction: column;
    align-items: stretch;
  }

  .ref-input {
    width: 100%;
  }

  .controls button {
    width: 100%;
  }
}
</style>