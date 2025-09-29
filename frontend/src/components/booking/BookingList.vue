<template>
  <div>
    <!-- Bookings List -->
    <div v-if="bookings.length > 0" class="results">
      <h2>Results</h2>
      <ul class="booking-list">
        <li
          v-for="(booking, index) in bookings"
          :key="booking.__ref || index"
          @click="emitSelectBooking(booking)"
          :class="{ selected: selectedBooking && selectedBooking.__ref === booking.__ref }"
        >
          <p><strong>Leg:</strong> {{ booking.__leg }}</p>
          <p><strong>Flight No:</strong> {{ booking.__flightNo || 'N/A' }}</p>
          <p><strong>Arrival:</strong> {{ formatDT(booking.__arrivalDate) || 'N/A' }}</p>
          <p><strong>Departure:</strong> {{ formatDT(booking.__departureDate) || 'N/A' }}</p>
          <p><strong>Passenger:</strong> {{ booking.__passenger || 'N/A' }}</p>
        </li>
      </ul>
    </div>
    <div v-else-if="!loading && hasSearched" class="message">
      No bookings found for the selected date range.
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BookingNorm } from '../../types/booking';

defineProps<{ 
  bookings: BookingNorm[];
  selectedBooking: BookingNorm | null;
  loading: boolean;
  hasSearched: boolean;
}>();

const emit = defineEmits<{ 
  (e: 'select-booking', booking: BookingNorm): void;
}>();

const formatDT = (s?: string | null) => {
  if (!s) return '';
  try {
    const d = new Date(s);
    if (Number.isNaN(d.getTime())) return s;
    return d.toLocaleString();
  } catch {
    return s;
  }
};

const emitSelectBooking = (booking: BookingNorm) => {
  emit('select-booking', booking);
};
</script>

<style scoped>
.message {
  padding: 15px;
  border-radius: 4px;
  margin: 20px 0;
}

.results {
  margin-top: 20px;
}

.booking-list {
  list-style: none;
  padding: 0;
  max-height: 400px;
  overflow-y: auto;
}

.booking-list li {
  padding: 15px;
  border: 1px solid #ddd;
  border-radius: 4px;
  margin-bottom: 10px;
  cursor: pointer;
  transition: background-color 0.2s;
}

.booking-list li:hover {
  background-color: #f0f0f0;
}

.booking-list li.selected {
  background-color: #e0efff;
  border-color: #007bff;
}
</style>