export interface BookingSearchFilters {
  start_date?: string;
  end_date?: string;
  apartment_id?: string;
  status?: string;
  guest_name?: string;
  booking_number?: string;
  days?: number;
  limit?: number;
}

export interface BookingStatsResponse {
  total_bookings: number;
  active_bookings: number;
  cancelled_bookings: number;
  cancellation_rate: number | null;
  total_nights: number;
  avg_nights_per_booking: number | null;
  total_persons: number;
  avg_persons_per_booking: number | null;
  total_revenue: number | null;
  avg_revenue_per_booking: number | null;
  avg_revenue_per_night: number | null;
  total_charges: number | null;
  total_electric_allowance: number | null;
  status_breakdown: Record<string, number>;
  start_date: string | null;
  end_date: string | null;
  occupancy_pct: number | null;
  no_booking_days_pct: number | null;
}

export interface ApartmentStatsRange {
  start_date: string | null;
  end_date: string | null;
  total_bookings: number;
  active_bookings: number;
  cancelled_bookings: number;
  cancellation_rate: number | null;
  total_nights: number;
  avg_nights_per_booking: number | null;
  total_persons: number;
  avg_persons_per_booking: number | null;
  total_revenue: number | null;
  avg_revenue_per_booking: number | null;
  avg_revenue_per_night: number | null;
  total_charges: number | null;
  total_electric_allowance: number | null;
  occupancy_pct: number | null;
  status_breakdown: Record<string, number>;
}

export interface ApartmentStatsYear {
  year: number;
  total_bookings: number;
  active_bookings: number;
  cancelled_bookings: number;
  cancellation_rate: number | null;
  total_nights: number;
  avg_nights_per_booking: number | null;
  total_days_in_year: number;
  occupancy_pct: number;
  total_revenue: number | null;
  avg_revenue_per_booking: number | null;
  total_charges: number | null;
  total_electric_allowance: number | null;
}

export interface ApartmentInfo {
  apartment_id: string;
  community: string | null;
  apartment_description: string | null;
  address: string | null;
  rooms: number;
  bathrooms: number;
  parking: string;
  total_occupants: number;
  owner_name: string | null;
  email: string | null;
  phone: string | null;
}

export interface ApartmentStatsResponse {
  apartment_id: string;
  apartment: ApartmentInfo;
  filtered_range: ApartmentStatsRange;
  by_year: ApartmentStatsYear[];
}
