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
  previously_cancelled: boolean;
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
}
