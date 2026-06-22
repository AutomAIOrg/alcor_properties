export interface Booking {
  record_id: number; // ID único por reserva en DB
  apartment_id: string; // Identificador del apartamento (ej: R180) — NO único entre reservas
  guest_name: string;
  check_in: string; // "YYYY-MM-DD"
  check_out: string; // "YYYY-MM-DD"
  status: string;
  nights: number;
  persons: number;
  adults: number;
  children: number;
  price: number | null;
  charges: number | null;
  electric_allowance: number | null;
  email: string | null;
  phone: string | null;
  booking_number: string | null;
  notes: string | null;
  notes_cleaning: string | null;
}

export const BASE_STATUSES = ['Confirmed', 'Pending', 'Cancelled', 'ok'] as const;
export type BookingStatus = (typeof BASE_STATUSES)[number];

export interface CleaningOpportunity {
  source_booking_record_id: number;
  apartment_id: string;
  available_from: string;
  available_until: string | null;
  comments: string;
}
