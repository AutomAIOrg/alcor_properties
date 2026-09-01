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

/**
 * Estados de reserva que ofrece la aplicación. Alimenta el desplegable de crear y editar
 * reserva y los filtros de estado del calendario y del buscador.
 */
export const BASE_STATUSES = ['Confirmed', 'Cancelled'] as const;
export type BookingStatus = (typeof BASE_STATUSES)[number];

/** Limpieza que prepara el check-in de una reserva: solo se limpia cuando hay entrada. */
export interface CleaningOpportunity {
  /** La reserva que llega: identifica la limpieza (factura, comentarios, hora de entrada). */
  source_booking_record_id: number;
  apartment_id: string;
  /** La ventana la cierra el check-in y la abre la salida anterior (o el lunes de esa semana). */
  available_from: string;
  available_until: string;
  /** Horas ya resueltas por el backend ("HH:MM:SS"): la pactada o la estándar. */
  available_from_time: string;
  available_until_time: string;
  comments: string;
  can_bill: boolean;
  has_bill: boolean;
  bill_state: string | null;
  address: string | null;
  apartment_description: string | null;
  /** Reserva que se va. null si no hay anterior: entonces available_from es el lunes. */
  previous_booking_record_id: number | null;
  /** Ocupación que la limpieza prepara: la de la reserva que llega. */
  persons: number;
  nights: number;
}
