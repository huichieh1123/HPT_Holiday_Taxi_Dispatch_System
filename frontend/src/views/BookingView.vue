<template>
  <div class="booking-view">
    <h1>Holiday Taxi Bookings</h1>

    <BookingSearch
      :loading="loading"
      :direct-fetch-loading="directFetchLoading"
      @search-by-ref="handleSearchByRef"
      @search-by-dates="startNewSearch"
    />

    <div v-if="loading && !bookings.length" class="message">Loading...</div>
    <div v-if="error" class="message error">{{ error }}</div>
    <div v-if="directFetchError" class="message error">{{ directFetchError }}</div>

    <BookingList
      :bookings="bookings"
      :selected-booking="selectedBooking"
      :loading="loading"
      :has-searched="hasSearched"
      :pagination="pagination"
      :search-dates="searchDates"
      @select-booking="handleSelectBooking"
      @page-change="handlePageChange"
    />

    <BookingDetail
      :selected-booking="selectedBooking"
      :detail-loading="detailLoading"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import BookingSearch from '../components/booking/BookingSearch.vue';
import BookingList from '../components/booking/BookingList.vue';
import BookingDetail from '../components/booking/BookingDetail.vue';
import type { BookingNorm } from '../types/booking';

// ---------- helpers ----------
const first = (...vals: any[]) => vals.find(v => v !== undefined && v !== null && v !== '');
const unwrap = (v: any) => (v?.booking ? v.booking : v) || v;

const getRef = (b: any) => {
  const x = unwrap(b);
  const ref = first(x?.ref, x?.general?.ref, (b as any)?.__ref);
  return typeof ref === 'string' ? ref.trim() : ref;
};

const getLegType = (b: any): 'arrival' | 'departure' | 'return' | 'unknown' => {
  const x = unwrap(b);
  if (x?.arrival) return 'arrival';
  if (x?.departure) return 'departure';
  if (x?.arrivaldate || x?.general?.arrivaldate) return 'arrival';
  if (x?.departuredate || x?.general?.departuredate) return 'departure';
  const toAirport = first(x?.toairport, x?.toairportcode, x?.departure?.toairport, x?.departure?.toairportcode);
  const fromAirport = first(x?.fromairport, x?.fromairportcode, x?.arrival?.fromairport, x?.arrival?.fromairportcode);
  if (toAirport) return 'departure';
  if (fromAirport) return 'arrival';
  const bt = x?.general?.bookingtype || x?.bookingtype || '';
  if (typeof bt === 'string' && bt.toLowerCase().includes('return')) return 'return';
  return 'unknown';
};

const getFlightNo = (b: any) => {
  const x = unwrap(b);
  return first(
    x?.transfers?.[0]?.flight?.flightNumber,
    x?.arrival?.flightno,
    x?.departure?.flightno,
    x?.flightno,
    x?.general?.flightno,
    (x as any)?.arrivalflightno,
    (x as any)?.departureflightno,
    (x as any)?.flight_number
  );
};

const getArrivalDate = (b: any) => {
  const x = unwrap(b);
  return first(x?.arrival?.arrivaldate, x?.general?.arrivaldate, x?.arrivaldate);
};

const getDepartureDate = (b: any) => {
  const x = unwrap(b);
  return first(x?.departure?.departuredate, x?.general?.departuredate, x?.departuredate);
};

const normalize = (v: any): BookingNorm => {
  const x = unwrap(v);
  return {
    ...x,
    __ref: getRef(x) ?? null,
    __leg: getLegType(x),
    __flightNo: getFlightNo(x) ?? null,
    __arrivalDate: getArrivalDate(x) ?? null,
    __departureDate: getDepartureDate(x) ?? null,
    __passenger: first(x?.passengername, x?.general?.passengername) ?? null,
  };
};

// ---------- state ----------
const bookings = ref<BookingNorm[]>([]);
const selectedBooking = ref<BookingNorm | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const hasSearched = ref(false);
const detailLoading = ref(false);
const directFetchLoading = ref(false);
const directFetchError = ref<string | null>(null);

// New state for pagination
const pagination = ref({ current_page: 1, has_next_page: false });
const searchDates = ref<{ from: string; to: string } | null>(null);

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;

// ---------- actions ----------

const fetchBookings = async (page: number) => {
  if (!searchDates.value) return;

  loading.value = true;
  error.value = null;
  hasSearched.value = true;
  if (page === 1) {
    bookings.value = [];
    selectedBooking.value = null;
  }

  try {
    const params = new URLSearchParams({
      dateFrom: searchDates.value.from,
      dateTo: searchDates.value.to,
      page: String(page),
    });

    const response = await fetch(`${API_BASE_URL}/api/bookings?${params.toString()}`);
    if (!response.ok) {
      const e = await response.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to fetch bookings (${response.status})`);
    }
    const data = await response.json();

    const bookingsData = data.bookings || {};
    bookings.value = Object.values(bookingsData).map(normalize);
    pagination.value = data.pagination;

    // The hydration logic can still run on the newly fetched page
    hydrateListWithDetails(5);

  } catch (err: any) {
    error.value = err?.message ?? String(err);
  } finally {
    loading.value = false;
  }
};

const startNewSearch = (dates: { from: string; to: string }) => {
  searchDates.value = dates;
  fetchBookings(1);
};

const handlePageChange = (newPage: number) => {
  if (newPage > 0) {
    fetchBookings(newPage);
  }
};

const handleSearchByRef = async (refId: string) => {
  directFetchLoading.value = true;
  directFetchError.value = null;
  selectedBooking.value = null;

  try {
    const res = await fetch(`${API_BASE_URL}/api/bookings/${encodeURIComponent(refId)}`);
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e.detail || `Failed to fetch booking (${res.status})`);
    }
    const raw = await res.json();
    selectedBooking.value = normalize(raw);
    bookings.value = [];
    hasSearched.value = false;
  } catch (e: any) {
    directFetchError.value = e?.message ?? String(e);
  } finally {
    directFetchLoading.value = false;
  }
};

const handleSelectBooking = async (booking: BookingNorm) => {
  detailLoading.value = true;
  selectedBooking.value = null; // Clear previous selection first

  const ref = booking.__ref;
  if (!ref) {
    error.value = 'Invalid booking: missing reference';
    detailLoading.value = false;
    return;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/bookings/${encodeURIComponent(ref)}`);
    if (!res.ok) {
      const e = await res.json().catch(() => ({}));
      throw new Error(e.detail || 'Failed to fetch booking details');
    }
    const raw = await res.json();
    const norm = normalize(raw);
    selectedBooking.value = norm;

    const idx = bookings.value.findIndex(b => b.__ref === norm.__ref);
    if (idx !== -1) bookings.value[idx] = { ...bookings.value[idx], ...norm };
  } catch (e: any) {
    error.value = e?.message ?? String(e);
  } finally {
    detailLoading.value = false;
  }
};

const hydrateListWithDetails = async (concurrency = 5) => {
  const targets = bookings.value.filter(b => !b.__flightNo && b.__ref);
  for (let i = 0; i < targets.length; i += concurrency) {
    const batch = targets.slice(i, i + concurrency);
    await Promise.all(
      batch.map(async (item) => {
        try {
          if (!item.__ref) return;
          const res = await fetch(`${API_BASE_URL}/api/bookings/${encodeURIComponent(item.__ref)}`);
          if (!res.ok) return;
          const raw = await res.json();
          const norm = normalize(raw);
          const idx = bookings.value.findIndex(b => b.__ref === norm.__ref);
          if (idx !== -1) bookings.value[idx] = { ...bookings.value[idx], ...norm };
        } catch {
          /* ignore single failure */
        }
      })
    );
  }
};

</script>

<style scoped>
.booking-view {
  font-family: sans-serif;
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

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

@media (max-width: 768px) {
  .booking-view {
    padding: 10px;
  }
}
</style>