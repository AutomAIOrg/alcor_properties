import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { Component, Input, inject, output, signal } from '@angular/core';

import { Booking } from '../../../../models/booking.model';
import { ApartmentStatsResponse, BookingSearchFilters } from '../../../../models/search.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { ApartmentService } from '../../../../services/apartment.service';
import { BookingService } from '../../../../services/booking.service';
import { SearchStatsGridComponent } from '../search-stats-grid/search-stats-grid.component';
import {
  DateRangePickerComponent,
  type DateRangeValue,
} from '../../../../shared/components/date-range-picker/date-range-picker.component';
import { exportApartmentStatsToExcel } from '../../../../shared/utils/stats-excel-export';

export type ApartmentLoadRequest = {
  apartmentId: string;
  requestId: number;
};

@Component({
  selector: 'app-apartment-search',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    DecimalPipe,
    BookingColorPipe,
    DateRangePickerComponent,
    SearchStatsGridComponent,
  ],
  templateUrl: './apartment-search.component.html',
  styleUrl: './apartment-search.component.scss',
})
export class ApartmentSearchComponent {
  private apartmentService = inject(ApartmentService);
  private bookingService = inject(BookingService);
  private lastLoadRequestId = 0;
  private apartmentSearchRequestId = 0;
  private autoSearchTimeout: ReturnType<typeof setTimeout> | null = null;
  private searchWithoutDatesOnCalendarClose = false;

  @Input() allApartmentIds: string[] = [];

  @Input() set apartmentToLoad(request: ApartmentLoadRequest | null | undefined) {
    const id = request?.apartmentId.trim() ?? '';
    if (!id || !request || request.requestId === this.lastLoadRequestId) return;

    this.lastLoadRequestId = request.requestId;
    this.apt.id.set(id);
    this.apt.from.set('');
    this.apt.to.set('');
    this.searchWithoutDatesOnCalendarClose = false;
    this.cancelAutoSearch();
    this.searchApartmentDetail();
  }

  bookingSelected = output<Booking>();

  apt = {
    id: signal(''),
    from: signal(''),
    to: signal(''),
    loading: signal(false),
    error: signal(''),
    bookings: signal<Booking[]>([]),
    stats: signal<ApartmentStatsResponse | null>(null),
  };

  searchApartmentDetail(): void {
    const id = this.apt.id().trim();
    if (!id) return;

    const requestId = ++this.apartmentSearchRequestId;
    let pendingRequests = 2;
    const finishRequest = () => {
      pendingRequests -= 1;
      if (pendingRequests === 0 && requestId === this.apartmentSearchRequestId) {
        this.apt.loading.set(false);
      }
    };

    this.apt.loading.set(true);
    this.apt.error.set('');
    this.apt.bookings.set([]);
    this.apt.stats.set(null);

    const bookingFilters: BookingSearchFilters = { apartment_id: id };
    if (this.apt.from()) bookingFilters.start_date = this.apt.from();
    if (this.apt.to()) bookingFilters.end_date = this.addOneDay(this.apt.to());

    this.bookingService.searchBookings(bookingFilters).subscribe({
      next: bookings => {
        if (requestId !== this.apartmentSearchRequestId) return;

        this.apt.bookings.set(this.sortBookingsByNewestCheckIn(bookings));
        finishRequest();
      },
      error: () => {
        if (requestId !== this.apartmentSearchRequestId) return;

        this.apt.error.set('No se pudieron cargar las reservas del piso.');
        finishRequest();
      },
    });

    const statsEnd = this.apt.to() ? this.addOneDay(this.apt.to()) : undefined;
    this.apartmentService.getApartmentStats(id, this.apt.from() || undefined, statsEnd).subscribe({
      next: stats => {
        if (requestId !== this.apartmentSearchRequestId) return;

        this.apt.stats.set(
          this.sortStatsByNewestYear({
            ...stats,
            filtered_range: {
              ...stats.filtered_range,
              start_date: this.apt.from() || null,
              end_date: this.apt.to() || null,
            },
          })
        );
        finishRequest();
      },
      error: err => {
        if (requestId !== this.apartmentSearchRequestId) return;

        const msg =
          err?.status === 404
            ? `El piso '${id}' no existe en la base de datos.`
            : 'No se pudieron cargar las estadísticas del piso.';
        this.apt.error.set(msg);
        finishRequest();
      },
    });
  }

  clearApartmentDetail(): void {
    this.apartmentSearchRequestId += 1;
    this.cancelAutoSearch();
    this.apt.id.set('');
    this.apt.from.set('');
    this.apt.to.set('');
    this.searchWithoutDatesOnCalendarClose = false;
    this.apt.loading.set(false);
    this.apt.bookings.set([]);
    this.apt.stats.set(null);
    this.apt.error.set('');
  }

  setApartmentRange(range: DateRangeValue): void {
    const hadDateFilter = !!this.apt.from() || !!this.apt.to();
    const rangeIsEmpty = !range.from && !range.to;

    this.apt.from.set(range.from);
    this.apt.to.set(range.to);

    this.searchWithoutDatesOnCalendarClose =
      rangeIsEmpty && hadDateFilter && this.hasActiveSearch() && !!this.apt.id().trim();
  }

  completeApartmentRange(range: DateRangeValue): void {
    this.setApartmentRange(range);
    this.searchWithoutDatesOnCalendarClose = false;
    this.searchApartmentDetail();
  }

  handleApartmentCalendarClosed(): void {
    if (!this.searchWithoutDatesOnCalendarClose) return;

    this.searchWithoutDatesOnCalendarClose = false;
    this.searchApartmentDetail();
  }

  setApartmentId(value: string): void {
    this.apt.id.set(value);
    this.scheduleAutoSearch();
  }

  downloadStatsExcel(): void {
    const stats = this.apt.stats();
    if (!stats) return;

    exportApartmentStatsToExcel(stats);
  }

  openModal(booking: Booking): void {
    this.bookingSelected.emit(booking);
  }

  applyBookingUpdate(updated: Booking): void {
    this.apt.bookings.update(list =>
      list.map(booking => (booking.record_id === updated.record_id ? updated : booking))
    );
  }

  refreshAfterBookingSaved(updated: Booking): void {
    if (this.hasActiveSearch()) {
      this.searchApartmentDetail();
      return;
    }

    this.applyBookingUpdate(updated);
  }

  inputValue(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }

  private scheduleAutoSearch(): void {
    this.cancelAutoSearch();
    if (!this.apt.id().trim()) return;

    this.autoSearchTimeout = setTimeout(() => {
      this.autoSearchTimeout = null;
      this.searchApartmentDetail();
    }, 300);
  }

  private cancelAutoSearch(): void {
    if (this.autoSearchTimeout === null) return;

    clearTimeout(this.autoSearchTimeout);
    this.autoSearchTimeout = null;
  }

  private hasActiveSearch(): boolean {
    return !!this.apt.stats() || this.apt.bookings().length > 0;
  }

  private addOneDay(isoDate: string): string {
    const [year, month, day] = isoDate.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    date.setUTCDate(date.getUTCDate() + 1);
    return date.toISOString().slice(0, 10);
  }

  private sortBookingsByNewestCheckIn(bookings: Booking[]): Booking[] {
    return [...bookings].sort((a, b) => {
      const dateComparison = b.check_in.localeCompare(a.check_in);
      return dateComparison !== 0 ? dateComparison : b.record_id - a.record_id;
    });
  }

  private sortStatsByNewestYear(stats: ApartmentStatsResponse): ApartmentStatsResponse {
    return {
      ...stats,
      by_year: [...stats.by_year].sort((a, b) => b.year - a.year),
    };
  }
}
