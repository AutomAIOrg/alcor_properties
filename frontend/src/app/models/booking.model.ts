export interface Booking {
  record_id: number; // ID único por reserva en DB
  apartment_id: string; // Identificador del apartamento (ej: R180) — NO único entre reservas
  guest_name: string;
  check_in: string; // "YYYY-MM-DD"
  check_out: string; // "YYYY-MM-DD"
  /** "HH:MM:SS" pactada para esta reserva; null = hora estándar (entrada 16:00 / salida 11:00). */
  check_in_time: string | null;
  check_out_time: string | null;
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
  /** Horas ya resueltas por el backend ("HH:MM:SS"): la pactada o la estándar. */
  available_from_time: string;
  available_until_time: string | null;
  comments: string;
  can_bill: boolean;
  has_bill: boolean;
  bill_state: string | null;
  address: string | null;
  apartment_description: string | null;
  /** Reserva de entrada. null si aún no hay reserva siguiente. */
  next_booking_record_id: number | null;
  /** Ocupación de la reserva de entrada. null si aún no hay reserva siguiente. */
  next_persons: number | null;
  next_nights: number | null;
}
