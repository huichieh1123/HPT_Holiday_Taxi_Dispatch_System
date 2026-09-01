export type ApiOperation =
  | 'booking-list'
  | 'booking-detail'
  | 'driver-update'
  | 'vehicle-delete'
  | 'location-update'
  | 'status-list'
  | 'export-start'
  | 'export-status'
  | 'export-download';

interface ApiErrorOptions {
  operation: ApiOperation;
  status?: number;
  fallback?: string;
}

type JsonObject = Record<string, unknown>;

const DEFAULT_MESSAGES: Record<ApiOperation, string> = {
  'booking-list': 'Bookings could not be loaded. Please try again.',
  'booking-detail': 'Booking details could not be loaded. Check the booking reference and try again.',
  'driver-update': 'Driver and vehicle details could not be updated. Please try again.',
  'vehicle-delete': 'The old vehicle could not be removed. Please try again.',
  'location-update': 'The vehicle location could not be updated. Please try again.',
  'status-list': 'Trip statuses could not be loaded. Refresh the page and try again.',
  'export-start': 'The export could not be started. Please try again.',
  'export-status': 'The export status could not be checked. Please try again.',
  'export-download': 'The export file could not be downloaded. Please try again.',
};

const REASON_MESSAGES: Record<string, string> = {
  NOT_FOUND: 'The booking or vehicle could not be found. Please check the details and try again.',
  CANCELLED: 'This booking has been cancelled, so it can no longer be updated.',
  BOOKING_TRAVELLED_TOO_LONG_AGO: 'This trip took place too long ago and can no longer be updated.',
  BOOKING_TRAVELS_TOO_LONG_IN_THE_FUTURE: 'It is too early to update this trip. Please try again closer to the pickup time.',
  INFORMATION_NOT_EXPECTED: 'This information is not supported for this booking type.',
  INFORMATION_NOT_EXPECTED_FOR_THIS_BOOKING_TYPE: 'This information is not supported for this booking type.',
  BOOKING_DATA_PROVIDED_TOO_EARLY: 'The information was received too early to be applied. Please try again closer to the pickup time.',
  TOO_MANY_DISTINCT_VEHICLE_IDENTIFIERS_FOR_THIS_BOOKING:
    'This booking already has the maximum number of vehicles. Remove the old vehicle and try again.',
  ATTEMPT_TO_DE_ALLOCATE_A_VEHICLE_IDENTIFIER_THAT_DOES_NOT_EXIST:
    'The vehicle could not be removed because it is no longer assigned to this booking.',
};

const FIELD_LABELS: Record<string, string> = {
  name: 'Driver name',
  licenseNumber: 'Driver license number',
  phoneNumber: 'Driver phone number',
  preferredContactMethod: 'Preferred contact method',
  contactMethods: 'Contact methods',
  brand: 'Vehicle brand',
  model: 'Vehicle model',
  color: 'Vehicle color',
  description: 'Vehicle description',
  registration: 'Vehicle registration',
  lat: 'Latitude',
  lng: 'Longitude',
  status: 'Trip status',
  dateFrom: 'Start date',
  dateTo: 'End date',
};

const isObject = (value: unknown): value is JsonObject =>
  typeof value === 'object' && value !== null && !Array.isArray(value);

const parseJsonString = (value: unknown): unknown => {
  if (typeof value !== 'string') return value;

  const trimmed = value.trim();
  if (!trimmed || (!trimmed.startsWith('{') && !trimmed.startsWith('['))) return value;

  try {
    return JSON.parse(trimmed);
  } catch {
    return value;
  }
};

const getNestedValue = (value: unknown, key: string, depth = 0): unknown => {
  if (depth > 4) return undefined;

  const parsed = parseJsonString(value);
  if (Array.isArray(parsed)) {
    for (const item of parsed) {
      const found = getNestedValue(item, key, depth + 1);
      if (found !== undefined) return found;
    }
    return undefined;
  }

  if (!isObject(parsed)) return undefined;
  if (parsed[key] !== undefined && parsed[key] !== null) return parsed[key];

  for (const child of Object.values(parsed)) {
    const found = getNestedValue(child, key, depth + 1);
    if (found !== undefined) return found;
  }
  return undefined;
};

const firstString = (value: unknown, depth = 0): string | null => {
  if (depth > 4) return null;

  const parsed = parseJsonString(value);
  if (typeof parsed === 'string') {
    const trimmed = parsed.trim();
    return trimmed || null;
  }

  if (Array.isArray(parsed)) {
    for (const item of parsed) {
      const found = firstString(item, depth + 1);
      if (found) return found;
    }
    return null;
  }

  if (isObject(parsed)) {
    for (const key of ['msg', 'message', 'detail', 'error_message', 'error']) {
      if (parsed[key] !== undefined) {
        const found = firstString(parsed[key], depth + 1);
        if (found) return found;
      }
    }
    for (const child of Object.values(parsed)) {
      const found = firstString(child, depth + 1);
      if (found) return found;
    }
  }

  return null;
};

const getPayloadText = (value: unknown): string => {
  if (value instanceof Error) return value.message;
  if (typeof value === 'string') return value;

  try {
    return JSON.stringify(value);
  } catch {
    return '';
  }
};

const getReasonMessage = (value: unknown): string | null => {
  const reason = firstString(getNestedValue(value, 'reason'));
  if (!reason) return null;
  return REASON_MESSAGES[reason.toUpperCase()] ?? null;
};

const getValidationMessage = (value: unknown): string | null => {
  const detail = getNestedValue(value, 'detail');
  if (!Array.isArray(detail)) return null;

  const issue = detail.find(isObject);
  if (!issue) return 'Some information is missing or invalid. Please check the form and try again.';

  const location = Array.isArray(issue.loc) ? issue.loc : [];
  const rawField = location.length > 0 ? location[location.length - 1] : undefined;
  const field = typeof rawField === 'string' ? (FIELD_LABELS[rawField] ?? rawField) : 'A field';
  const message = typeof issue.msg === 'string' ? issue.msg.toLowerCase() : '';

  if (message.includes('required')) return `${field} is required.`;
  if (message.includes('valid number')) return `${field} must be a valid number.`;
  return `${field} contains an invalid value. Please check it and try again.`;
};

const getKnownTextMessage = (value: unknown, operation: ApiOperation): string | null => {
  const text = getPayloadText(value).toLowerCase();

  if (text.includes('invalid status')) {
    return 'The selected trip status is invalid. Refresh the page and select a status again.';
  }
  if (text.includes('invalid lat/lng') || text.includes('latitude') && text.includes('longitude')) {
    return 'The location coordinates are invalid. Get the current location again and retry.';
  }
  if (text.includes('vehicle registration cannot be empty')) {
    return 'Vehicle registration is required.';
  }
  if (text.includes('cancelled')) return REASON_MESSAGES.CANCELLED;
  if (text.includes('travelled too long ago')) return REASON_MESSAGES.BOOKING_TRAVELLED_TOO_LONG_AGO;
  if (text.includes('travels too long in the future')) return REASON_MESSAGES.BOOKING_TRAVELS_TOO_LONG_IN_THE_FUTURE;
  if (text.includes('not expected for this booking type')) {
    return REASON_MESSAGES.INFORMATION_NOT_EXPECTED_FOR_THIS_BOOKING_TYPE;
  }
  if (text.includes('too many distinct vehicle')) {
    return REASON_MESSAGES.TOO_MANY_DISTINCT_VEHICLE_IDENTIFIERS_FOR_THIS_BOOKING;
  }
  if (text.includes('de-allocate a vehicle identifier that does not exist')) {
    return REASON_MESSAGES.ATTEMPT_TO_DE_ALLOCATE_A_VEHICLE_IDENTIFIER_THAT_DOES_NOT_EXIST;
  }
  if (text.includes('task not found')) {
    return 'This export session has expired or could not be found. Please start a new export.';
  }
  if (text.includes('export is not yet complete')) {
    return 'The export is still being prepared. Please wait and try again.';
  }
  if (text.includes('no data found to export')) {
    return 'There is no booking data to export for the selected date range.';
  }
  if (text.includes('not found') || /\b404\b/.test(text)) {
    if (operation === 'booking-detail') {
      return 'No booking was found for that reference. Check the reference and try again.';
    }
    return REASON_MESSAGES.NOT_FOUND;
  }

  return null;
};

const isNetworkError = (value: unknown): boolean => {
  if (!(value instanceof Error)) return false;
  const text = value.message.toLowerCase();
  return value instanceof TypeError || text.includes('failed to fetch') || text.includes('networkerror');
};

const getHttpMessage = (status: number | undefined, operation: ApiOperation): string | null => {
  if (!status) return null;

  if (status === 401 || status === 403) {
    return 'This request was not authorized. Please contact support if the problem continues.';
  }
  if (status === 404) {
    if (operation === 'booking-detail') {
      return 'No booking was found for that reference. Check the reference and try again.';
    }
    if (operation === 'export-status' || operation === 'export-download') {
      return 'This export session has expired or could not be found. Please start a new export.';
    }
    return REASON_MESSAGES.NOT_FOUND;
  }
  if (status === 409) {
    return 'The information changed while this request was being processed. Refresh the booking and try again.';
  }
  if (status === 422) {
    return 'Some required information is missing or invalid. Please check the form and try again.';
  }
  if (status === 429) {
    return 'Too many requests were sent. Please wait a moment and try again.';
  }
  if ([502, 503, 504].includes(status)) {
    return 'Holiday Taxis is temporarily unavailable. Please try again later.';
  }
  if (status >= 500) {
    return 'The server encountered a problem. Please try again later.';
  }

  return null;
};

const isSafeServerMessage = (message: string): boolean => {
  const lower = message.toLowerCase();
  const genericMessages = ['error', 'failed', 'update failed', 'an error occurred'];
  const technicalMarkers = [
    'external api error',
    'client error',
    'server error',
    'traceback',
    'exception',
    'httpconnectionpool',
    'httpsconnectionpool',
    'failed to parse',
    'unknown error',
  ];
  return message.length <= 240
    && !genericMessages.includes(lower)
    && !technicalMarkers.some(marker => lower.includes(marker));
};

export const parseApiError = (error: unknown, options: ApiErrorOptions): string => {
  const fallback = options.fallback ?? DEFAULT_MESSAGES[options.operation];

  if (isNetworkError(error)) {
    return 'Unable to connect to the server. Check your connection and try again.';
  }

  const reasonMessage = getReasonMessage(error);
  if (reasonMessage) return reasonMessage;

  const knownTextMessage = getKnownTextMessage(error, options.operation);
  if (knownTextMessage) return knownTextMessage;

  const validationMessage = getValidationMessage(error);
  if (validationMessage) return validationMessage;

  const httpMessage = getHttpMessage(options.status, options.operation);
  if (httpMessage) return httpMessage;

  const serverMessage = firstString(error instanceof Error ? error.message : error);
  if (serverMessage && isSafeServerMessage(serverMessage)) return serverMessage;

  return fallback;
};

export const parseApiErrorResponse = async (
  response: Response,
  options: Omit<ApiErrorOptions, 'status'>,
): Promise<string> => {
  let payload: unknown = null;

  try {
    const text = await response.text();
    payload = parseJsonString(text);
  } catch {
    // The HTTP status still provides a safe user-facing message.
  }

  return parseApiError(payload, { ...options, status: response.status });
};
