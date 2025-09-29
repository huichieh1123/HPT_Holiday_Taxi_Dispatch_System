export type BookingNorm = {
  __ref: string | null;
  __leg: 'arrival' | 'departure' | 'return' | 'unknown';
  __flightNo: string | null;
  __arrivalDate: string | null;
  __departureDate: string | null;
  __passenger: string | null;
  [k: string]: any;
};

export interface DriverForm {
  name: string;
  phoneNumber: string;
  preferredContactMethod: 'VOICE' | 'SMS';
  contactMethods: ('VOICE' | 'SMS')[];
}

export interface VehicleForm {
  brand: string;
  model: string;
  color: string;
  description: string;
  registration: string;
}
