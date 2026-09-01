import { describe, expect, it } from 'vitest';
import { parseApiError, parseApiErrorResponse } from '../apiError';

describe('API error messages', () => {
  it('maps Holiday Taxis reason codes to user-facing messages', () => {
    expect(parseApiError(
      { reason: 'CANCELLED' },
      { operation: 'location-update', status: 400 },
    )).toBe('This booking has been cancelled, so it can no longer be updated.');
  });

  it('extracts FastAPI validation errors without exposing the raw object', () => {
    expect(parseApiError(
      { detail: [{ loc: ['body', 'vehicle', 'registration'], msg: 'Field required' }] },
      { operation: 'driver-update', status: 422 },
    )).toBe('Vehicle registration is required.');
  });

  it('turns an upstream booking 404 wrapped as a gateway error into a useful message', () => {
    expect(parseApiError(
      { detail: 'External API error: 404 Client Error' },
      { operation: 'booking-detail', status: 502 },
    )).toBe('No booking was found for that reference. Check the reference and try again.');
  });

  it('does not expose technical gateway details', () => {
    expect(parseApiError(
      { detail: 'External API error: HTTPSConnectionPool timed out' },
      { operation: 'booking-list', status: 502 },
    )).toBe('Holiday Taxis is temporarily unavailable. Please try again later.');
  });

  it('uses a consistent message for browser network failures', () => {
    expect(parseApiError(
      new TypeError('Failed to fetch'),
      { operation: 'driver-update' },
    )).toBe('Unable to connect to the server. Check your connection and try again.');
  });

  it('explains an empty export download', async () => {
    const response = new Response(
      JSON.stringify({ detail: 'No data found to export, the source was likely empty.' }),
      { status: 404 },
    );

    await expect(parseApiErrorResponse(response, { operation: 'export-download' }))
      .resolves.toBe('There is no booking data to export for the selected date range.');
  });
});
