import { CurrencyPipe, DecimalPipe } from '@angular/common';
import { Component, Input } from '@angular/core';

export type SearchStatsGridData = {
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
  no_booking_days_pct?: number | null;
  status_breakdown: Record<string, number>;
};

@Component({
  selector: 'app-search-stats-grid',
  standalone: true,
  imports: [CurrencyPipe, DecimalPipe],
  templateUrl: './search-stats-grid.component.html',
  styleUrl: './search-stats-grid.component.scss',
})
export class SearchStatsGridComponent {
  @Input({ required: true }) stats!: SearchStatsGridData;
  @Input() nightsLabel = 'Noches reserva';

  pendingBookings(): number {
    return Object.entries(this.stats.status_breakdown).reduce((total, [status, count]) => {
      const normalizedStatus = status.trim().toLowerCase();
      return normalizedStatus === 'pending' || normalizedStatus === 'pendiente'
        ? total + count
        : total;
    }, 0);
  }

  statusBreakdownEntries(): { key: string; value: number }[] {
    return Object.entries(this.stats.status_breakdown).map(([key, value]) => ({ key, value }));
  }
}
