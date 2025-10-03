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
      <!-- Pagination Controls -->
      <div class="pagination-controls">
        <button 
          @click="emit('page-change', pagination.current_page - 1)" 
          :disabled="pagination.current_page <= 1 || loading">
          &laquo; Previous
        </button>
        <span>Page {{ pagination.current_page }}</span>
        <button 
          @click="emit('page-change', pagination.current_page + 1)" 
          :disabled="!pagination.has_next_page || loading">
          Next &raquo;
        </button>
      </div>
    </div>
    <div v-else-if="!loading && hasSearched" class="message">
      No bookings found for the selected date range.
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BookingNorm } from '../../types/booking';

// Define props including the new pagination object
defineProps<{ 
  bookings: BookingNorm[];
  selectedBooking: BookingNorm | null;
  loading: boolean;
  hasSearched: boolean;
  pagination: {
    current_page: number;
    has_next_page: boolean;
  };
}>();

// Define emits including the new page-change event
const emit = defineEmits<{ 
  (e: 'select-booking', booking: BookingNorm): void;
  (e: 'page-change', newPage: number): void;
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

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 20px;
  margin-top: 20px;
}

.pagination-controls button {
  padding: 8px 16px;
  border: none;
  background-color: #007bff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.pagination-controls button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.pagination-controls button:hover:not(:disabled) {
  background-color: #0056b3;
}

.pagination-controls span {
  font-weight: bold;
}
</style>