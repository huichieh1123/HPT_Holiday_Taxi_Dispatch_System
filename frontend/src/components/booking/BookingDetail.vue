<template>
  <div>
    <div v-if="detailLoading" class="message">Loading details...</div>
    <div v-if="selectedBooking" class="details">
      <h2>Booking Details: {{ selectedBooking.__ref }}</h2>

      <div class="detail-grid">
        <div><strong>Leg:</strong> {{ selectedBooking.__leg }}</div>
        <div><strong>Flight No:</strong> {{ selectedBooking.__flightNo || 'N/A' }}</div>
        <div><strong>Arrival:</strong> {{ formatDT(selectedBooking.__arrivalDate) || 'N/A' }}</div>
        <div><strong>Departure:</strong> {{ formatDT(selectedBooking.__departureDate) || 'N/A' }}</div>
        <div><strong>Passenger:</strong> {{ selectedBooking.__passenger || 'N/A' }}</div>
      </div>

      <h3 class="mt-2">Raw JSON</h3>
      <pre>{{ JSON.stringify(selectedBooking, null, 2) }}</pre>

      <!-- Location Link Generator -->
      <div class="link-generator">
        <h4>Generate Location Update Link</h4>
        <button @click="generateLocationLink">Generate Link</button>
        <div v-if="locationUpdateLink" class="generated-link">
          <p>Share this link with the driver:</p>
          <input type="text" :value="locationUpdateLink" readonly />
          <button @click="copyLinkToClipboard">Copy</button>
        </div>
      </div>

      <!-- Update Driver Form -->
      <div class="update-form">
        <h3>Update Driver & Vehicle</h3>
        <div class="form-grid">
          <!-- Driver Fields -->
          <div class="form-group">
            <label>Driver Name:</label>
            <input v-model="driverForm.name" placeholder="e.g., John Doe" />
          </div>
          <div class="form-group">
            <label>Driver Phone:</label>
            <input v-model="driverForm.phoneNumber" placeholder="e.g., +441234567890" />
          </div>
          <!-- Vehicle Fields -->
          <div class="form-group">
            <label>Vehicle Brand:</label>
            <input v-model="vehicleForm.brand" placeholder="e.g., Toyota" />
          </div>
          <div class="form-group">
            <label>Vehicle Model:</label>
            <input v-model="vehicleForm.model" placeholder="e.g., Prius" />
          </div>
          <div class="form-group">
            <label>Vehicle Color:</label>
            <input v-model="vehicleForm.color" placeholder="e.g., Blue" />
          </div>
          <div class="form-group">
            <label>Vehicle Registration:</label>
            <input v-model="vehicleForm.registration" placeholder="e.g., AB-123-XYZ" />
          </div>
          <div class="form-group full-width">
            <label>Vehicle Description:</label>
            <input v-model="vehicleForm.description" placeholder="e.g., Branded with 'Acme Transfers'" />
          </div>
        </div>
        <button @click="updateDriver" :disabled="updating || !selectedBooking">
          {{ updating ? 'Updating...' : 'Update Driver' }}
        </button>
        <div v-if="updateMessage" class="message success">{{ updateMessage }}</div>
        <div v-if="updateError" class="message error">{{ updateError }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import type { BookingNorm, DriverForm, VehicleForm } from '../../types/booking';

const props = defineProps<{
  selectedBooking: BookingNorm | null;
  detailLoading: boolean;
}>();

// Rule mapping based on rule.txt
const ruleMessages = {
  OK: { type: 'success', text: 'Location updated successfully.' },
  BOOKING_DATA_PROVIDED_TOO_EARLY: { type: 'info', text: 'Location update accepted and is being processed.' },
  NOT_FOUND: { type: 'error', text: 'Error: Booking reference not found.' },
  CANCELLED: { type: 'error', text: 'Error: This booking has been cancelled.' },
  BOOKING_TRAVELLED_TOO_LONG_AGO: { type: 'error', text: 'Error: This booking is too old to be updated.' },
  BOOKING_TRAVELS_TOO_LONG_IN_THE_FUTURE: { type: 'error', text: 'Error: This booking is too far in the future to be updated.' },
  INFORMATION_NOT_EXPECTED_FOR_THIS_BOOKING_TYPE: { type: 'error', text: 'Error: Location information is not expected for this type of booking.' },
  TOO_MANY_DISTINCT_VEHICLE_IDENTIFIERS_FOR_THIS_BOOKING: { type: 'error', text: 'Error: Too many different vehicles have been assigned to this booking.' },
  ATTEMPT_TO_DE_ALLOCATE_A_VEHICLE_IDENTIFIER_THAT_DOES_NOT_EXIST: { type: 'error', text: 'Error: The vehicle you are trying to de-allocate does not exist.' },
  UNKNOWN_ERROR: { type: 'error', text: 'An unknown error occurred.' }
};

const driverForm = ref<DriverForm>({
  name: 'Driver 1',
  phoneNumber: '+441234567891',
  preferredContactMethod: 'VOICE',
  contactMethods: ['VOICE', 'SMS'],
});

const vehicleForm = ref<VehicleForm>({
  brand: 'Toyota',
  model: 'Prius',
  color: 'blue',
  description: "Branded with 'Acme Transfers'",
  registration: 'AB-123-XYZ1',
});

const updating = ref(false);
const updateMessage = ref<string | null>(null);
const updateError = ref<string | null>(null);
const locationUpdateLink = ref('');

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

watch(() => props.selectedBooking, (newBooking) => {
  locationUpdateLink.value = '';
  updateMessage.value = null;
  updateError.value = null;
});

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

// This function now triggers a location update for demonstration
const updateDriver = async () => {
  if (!props.selectedBooking) return;
  updating.value = true;
  updateMessage.value = null;
  updateError.value = null;

  const ref = props.selectedBooking.__ref;
  if (!ref) {
    updateError.value = 'Missing booking reference';
    updating.value = false;
    return;
  }

  try {
    const vehicleId = vehicleForm.value.registration;
    if (!vehicleId) {
      throw new Error('Vehicle registration is required to test the location update.');
    }

    // Dummy location data for demonstration
    const locationPayload = {
      lat: 34.0522,
      lng: -118.2437,
      status: 'AFTER_PICKUP'
    };

    const locRes = await fetch(`${API_BASE_URL}/api/bookings/${encodeURIComponent(ref)}/vehicles/${encodeURIComponent(vehicleId)}/location`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(locationPayload),
    });

    const locData = await locRes.json();
    const rule = ruleMessages[locData.reason as keyof typeof ruleMessages] || ruleMessages.UNKNOWN_ERROR;

    if (!locRes.ok || rule.type === 'error') {
      throw new Error(rule.text);
    }
    
    updateMessage.value = rule.text;

  } catch (e: any) {
    updateError.value = e?.message ?? String(e);
  } finally {
    updating.value = false;
  }
};

const generateLocationLink = () => {
  if (props.selectedBooking?.__ref) {
    const vehicleId = vehicleForm.value.registration;
    if (!vehicleId) {
      alert('Please enter a vehicle registration number in the form below before generating a link.');
      return;
    }
    const path = `/update-location/${props.selectedBooking.__ref}/${vehicleId}`;
    locationUpdateLink.value = window.location.origin + path;
  }
};

const copyLinkToClipboard = () => {
  if (locationUpdateLink.value) {
    navigator.clipboard.writeText(locationUpdateLink.value).then(() => {
      alert('Link copied to clipboard!');
    }, () => {
      alert('Failed to copy link.');
    });
  }
};
</script>

<style scoped>
.message {
  padding: 15px;
  border-radius: 4px;
  margin: 20px 0;
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

.details {
  margin-top: 30px;
  padding: 20px;
  border: 1px solid #ccc;
  border-radius: 8px;
  background-color: #fafafa;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 8px 20px;
  margin-bottom: 14px;
}

pre {
  background-color: #eee;
  padding: 15px;
  border-radius: 4px;
  white-space: pre-wrap;
  word-wrap: break-word;
  max-height: 400px;
  overflow-y: auto;
}

.update-form {
  margin-top: 20px;
}

.update-form h3 {
  margin-bottom: 15px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
  margin-bottom: 20px;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  margin-bottom: 5px;
  font-weight: bold;
  color: #333;
}

.form-group input {
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.form-group.full-width {
  grid-column: 1 / -1;
}

.mt-2 { margin-top: 0.5rem; }

.link-generator {
  margin-top: 20px;
  padding: 15px;
  border: 1px solid #eee;
  border-radius: 4px;
}

.generated-link {
  margin-top: 15px;
}

.generated-link p {
  margin-bottom: 5px;
}

.generated-link input {
  width: calc(100% - 80px);
  padding: 8px;
  border: 1px solid #ccc;
  border-radius: 4px;
  margin-right: 10px;
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
  .generated-link {
    display: flex;
    flex-direction: column;
  }

  .generated-link input {
    width: 100%;
    margin-right: 0;
    margin-bottom: 10px;
  }

  .generated-link button {
    width: 100%;
  }
}
</style>
