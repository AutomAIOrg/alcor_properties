export interface Bill {
  bill_id: number | null;
  record_id: number | null;
  apartment_id: string;
  cleaning_date: string | null; // "YYYY-MM-DD"
  clean_hours: number;
  cost: number | null;
  hourly_rate: number | null;
  state: string;
  paid_at: string | null; // "YYYY-MM-DD"
  previously_cancelled?: boolean; // true en una pendiente cuya limpieza tuvo una factura cancelada
}

export interface BillStateUpdatePayload {
  state: string;
  paid_at?: string; // "YYYY-MM-DD"
}

export interface BillCreatePayload {
  record_id: number;
  cleaning_date: string;
  start_time: string;
  end_time: string;
  hourly_rate?: number;
}

export interface BillSearchFilters {
  apartment_id?: string;
  state?: string;
  date_from?: string;
  date_to?: string;
  cost_min?: number;
  cost_max?: number;
}
