<template>
  <div>
    <!-- Bookings List -->
    <div v-if="bookings.length > 0" class="results">
      <div class="results-header">
        <h2>Results</h2>
        <button @click="startExport" class="export-button" :disabled="isExporting">
          {{ isExporting ? 'Exporting...' : 'Export to Excel' }}
        </button>
      </div>

      <!-- Export Progress Bar -->
      <div v-if="isExporting" class="progress-container">
        <p>{{ exportStatusMessage }} ({{ exportProgress }} / {{ exportTotal }})</p>
        <progress :value="exportProgress" :max="exportTotal"></progress>
        <p v-if="exportError" class="error-message">Error: {{ exportError }}</p>
      </div>

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
import { ref, computed } from 'vue';
import type { BookingNorm } from '../../types/booking';

// Define props including the new pagination object
const props = defineProps<{ 
  bookings: BookingNorm[];
  selectedBooking: BookingNorm | null;
  loading: boolean;
  hasSearched: boolean;
  pagination: {
    current_page: number;
    has_next_page: boolean;
  };
  searchDates: { from: string; to: string } | null;
}>();

// Define emits including the new page-change event
const emit = defineEmits<{ 
  (e: 'select-booking', booking: BookingNorm): void;
  (e: 'page-change', newPage: number): void;
}>();

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// --- Export State ---
const isExporting = ref(false);
const exportProgress = ref(0);
const exportTotal = ref(0);
const exportStatus = ref('');
const exportError = ref<string | null>(null);
let pollingInterval: number | null = null;

const exportStatusMessage = computed(() => {
  switch(exportStatus.value) {
    case 'fetching_summaries': return 'Step 1: Fetching booking list...';
    case 'fetching_details': return 'Step 2: Fetching booking details...';
    case 'generating_file': return 'Step 3: Generating Excel file...';
    case 'complete': return 'Export complete!';
    case 'error': return 'An error occurred';
    default: return 'Starting export...';
  }
});

const pollExportStatus = (taskId: string) => {
  pollingInterval = window.setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/export/status/${taskId}`);
      if (!res.ok) {
        throw new Error('Failed to get export status.');
      }
      const data = await res.json();
      
      exportStatus.value = data.status;
      exportProgress.value = data.progress;
      exportTotal.value = data.total;

      if (data.status === 'complete') {
        if (pollingInterval) clearInterval(pollingInterval);
        window.location.href = `${API_BASE_URL}/api/export/download/${taskId}`;
        setTimeout(() => { isExporting.value = false; }, 2000);
      } else if (data.status === 'error') {
        if (pollingInterval) clearInterval(pollingInterval);
        exportError.value = data.error_message || 'Unknown error during export.';
        isExporting.value = false;
      }
    } catch (err) {
      if (pollingInterval) clearInterval(pollingInterval);
      exportError.value = 'Failed to connect to the server for status updates.';
      isExporting.value = false;
    }
  }, 2000);
};

const startExport = async () => {
  if (!props.searchDates) {
    alert('Please perform a search first to select a date range.');
    return;
  }

  isExporting.value = true;
  exportError.value = null;
  exportProgress.value = 0;
  exportTotal.value = 0;
  exportStatus.value = 'pending';

  try {
    const params = new URLSearchParams({
      dateFrom: props.searchDates.from,
      dateTo: props.searchDates.to,
    });
    const res = await fetch(`${API_BASE_URL}/api/export/start?${params.toString()}`, { method: 'POST' });
    if (!res.ok) {
      throw new Error('Failed to start the export process.');
    }
    const { task_id } = await res.json();
    pollExportStatus(task_id);
  } catch (err: any) {
    exportError.value = err.message || 'Could not start export.';
    isExporting.value = false;
  }
};

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

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.export-button {
  padding: 8px 16px;
  border: none;
  background-color: #28a745; /* Green color */
  color: white;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
}

.export-button:hover:not(:disabled) {
  background-color: #218838;
}

.export-button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

.progress-container {
  margin: 15px 0;
  padding: 10px;
  border: 1px solid #ddd;
  border-radius: 4px;
}

.progress-container p {
  margin: 0 0 5px 0;
}

.progress-container progress {
  width: 100%;
}

.error-message {
  color: #721c24; /* Bootstrap's danger color */
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