<template>
  <div class="location-update-view">
    <h1>Update Vehicle Location</h1>
    <div v-if="bookingRef">
      <p><strong>Booking Reference:</strong> {{ bookingRef }}</p>
      <p><strong>Vehicle ID:</strong> {{ vehicleId }}</p>

      <div v-if="error" class="message error">{{ error }}</div>

      <!-- Geolocation -->
      <div class="geo-section">
        <button @click="getGeolocation" :disabled="geo.loading">
          {{ geo.loading ? 'Getting Location...' : 'Get Current Location' }}
        </button>
        <div v-if="geo.lat && geo.lng" class="geo-coords">
          <p><strong>Latitude:</strong> {{ geo.lat }}</p>
          <p><strong>Longitude:</strong> {{ geo.lng }}</p>
        </div>
      </div>

      <!-- Status Selection -->
      <div class="status-section">
        <label for="status-select"><strong>Trip Status:</strong></label>
        <select id="status-select" v-model="selectedStatus">
          <option disabled value="">Please select a status</option>
          <option v-for="status in availableStatuses" :key="status" :value="status">
            {{ status }}
          </option>
        </select>
      </div>

      <!-- Update Button -->
      <div class="update-section">
        <button @click="submitUpdate" :disabled="submitting || !canSubmit">
          {{ submitting ? 'Updating...' : 'Submit Update' }}
        </button>
      </div>

      <div v-if="successMessage" class="message success">{{ successMessage }}</div>
    </div>
    <div v-else>
      <p>Loading booking information...</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';

const route = useRoute();

// Route params
const bookingRef = ref<string | null>(null);
const vehicleId = ref<string | null>(null);

// Geolocation state
const geo = ref({
  loading: false,
  lat: null as number | null,
  lng: null as number | null,
});

// Statuses
const availableStatuses = ref<string[]>([]);
const selectedStatus = ref('');

// Component state
const error = ref<string | null>(null);
const submitting = ref(false);
const successMessage = ref<string | null>(null);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// Fetch available statuses from the backend
const fetchStatuses = async () => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/statuses`);
    if (!response.ok) {
      throw new Error('Failed to fetch statuses.');
    }
    availableStatuses.value = await response.json();
  } catch (err: any) {
    error.value = err.message || 'Could not load statuses from backend.';
  }
};

// Get user's geolocation
const getGeolocation = () => {
  if (!navigator.geolocation) {
    error.value = 'Geolocation is not supported by your browser.';
    return;
  }
  geo.value.loading = true;
  navigator.geolocation.getCurrentPosition(
    (position) => {
      geo.value.lat = position.coords.latitude;
      geo.value.lng = position.coords.longitude;
      geo.value.loading = false;
      error.value = null; // Clear previous errors
    },
    (err) => {
      error.value = `Failed to get location: ${err.message}`;
      geo.value.loading = false;
    }
  );
};

// Check if form can be submitted
const canSubmit = computed(() => {
  return geo.value.lat !== null && geo.value.lng !== null && selectedStatus.value !== '';
});

// Submit the location update
const submitUpdate = async () => {
  if (!canSubmit.value) {
    error.value = 'Please get location and select a status first.';
    return;
  }

  submitting.value = true;
  error.value = null;
  successMessage.value = null;

  try {
    const payload = {
      lat: geo.value.lat,
      lng: geo.value.lng,
      status: selectedStatus.value,
    };

    const response = await fetch(
      `${API_BASE_URL}/api/bookings/${bookingRef.value}/vehicles/${vehicleId.value}/location`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    );

    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.detail || 'Failed to update location.');
    }

    await response.json();
    successMessage.value = 'Location updated successfully!';
  } catch (err: any) {
    error.value = err.message || 'An unknown error occurred.';
  } finally {
    submitting.value = false;
  }
};

// On component mount
onMounted(() => {
  bookingRef.value = route.params.bookingRef as string;
  vehicleId.value = route.params.vehicleId as string;
  fetchStatuses();
});
</script>

<style scoped>
.location-update-view {
  font-family: sans-serif;
  max-width: 600px;
  margin: 40px auto;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

h1 {
  text-align: center;
  margin-bottom: 25px;
}

.message {
  padding: 15px;
  border-radius: 4px;
  margin: 20px 0;
  text-align: center;
}

.error {
  background-color: #f8d7da;
  color: #721c24;
  border: 1px solid #f5c6cb;
}

.success {
  background-color: #d4edda;
  color: #155724;
  border: 1px solid #c3e6cb;
}

.geo-section, .status-section, .update-section {
  margin-bottom: 20px;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 4px;
}

.geo-coords {
  margin-top: 15px;
  background-color: #f9f9f9;
  padding: 10px;
  border-radius: 4px;
}

label {
  font-weight: bold;
  margin-right: 10px;
}

select {
  padding: 8px;
  border-radius: 4px;
  border: 1px solid #ccc;
  min-width: 200px;
}

button {
  padding: 10px 20px;
  border: none;
  background-color: #007bff;
  color: white;
  border-radius: 4px;
  cursor: pointer;
  transition: background-color 0.3s;
  display: block;
  margin: 0 auto;
}

button:disabled {
  background-color: #ccc;
  cursor: not-allowed;
}

button:hover:not(:disabled) {
  background-color: #0056b3;
}
</style>
