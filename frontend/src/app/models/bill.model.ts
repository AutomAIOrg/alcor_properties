export type BillState = 'Pendiente' | 'Creada' | 'Pagada' | 'Cancelada';

export interface Bill {
  bill_id: number | null;
  record_id: number | null;
  apartment_id: string;
  cleaning_date: string | null;
  clean_hours: number;
  cost: number | null;
  hourly_rate: number | null;
  cleaning_type_id: number | null;
  cleaning_type_name: string | null;
  state: BillState;
  paid_at: string | null;
  /** Fecha de pago confirmada por administración; null si aún no ha confirmado. */
  paid_confirmed_by_admin: string | null;
  /** Nombre completo de quien confirmó el pago desde administración. */
  paid_confirmed_by_admin_name: string | null;
  /** Fecha de pago confirmada por la limpiadora; null si aún no ha confirmado. */
  paid_confirmed_by_cleaner: string | null;
  /** Nombre completo de quien confirmó el pago desde limpieza. */
  paid_confirmed_by_cleaner_name: string | null;
  cancellation_note: string | null;
  previously_cancelled: boolean;
  address: string | null;
  apartment_description: string | null;
  created_at: string | null;
}

export interface BillCreateRequest {
  record_id: number;
  cleaning_date: string;
  start_time: string;
  end_time: string;
  cleaning_type_id: number;
}

export interface BillListFilters {
  apartment_id?: string;
  state?: BillState;
  date_from?: string;
  date_to?: string;
  cost_min?: number;
  cost_max?: number;
}

export interface BillUpdateStateRequest {
  state: BillState;
  paid_at?: string;
  cancellation_note?: string;
}

export interface BillRectifyRequest {
  cleaning_date: string;
  clean_hours: number;
  cleaning_type_id: number;
}
