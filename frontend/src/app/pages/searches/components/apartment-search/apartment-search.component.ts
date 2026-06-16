import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { Component, Input, inject, output, signal } from '@angular/core';

import { BASE_STATUSES, Booking } from '../../../../models/booking.model';
import { ApartmentStatsResponse, BookingSearchFilters } from '../../../../models/search.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { ApartmentService } from '../../../../services/apartment.service';
import { BookingService } from '../../../../services/booking.service';
import { SearchStatsGridComponent } from '../search-stats-grid/search-stats-grid.component';
import {
  DateRangePickerComponent,
  type DateRangeValue,
} from '../../../../shared/components/date-range-picker/date-range-picker.component';

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

  @Input() allApartmentIds: string[] = [];

  @Input() set apartmentToLoad(request: ApartmentLoadRequest | null | undefined) {
    const id = request?.apartmentId.trim() ?? '';
    if (!id || !request || request.requestId === this.lastLoadRequestId) return;

    this.lastLoadRequestId = request.requestId;
    this.apt.id.set(id);
    this.apt.from.set('');
    this.apt.to.set('');
    this.apt.status.set('');
    this.searchApartmentDetail();
  }

  bookingSelected = output<Booking>();

  readonly STATUS_OPTIONS = ['', ...BASE_STATUSES] as const;

  apt = {
    id: signal(''),
    from: signal(''),
    to: signal(''),
    status: signal(''),
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
    if (this.apt.to()) bookingFilters.end_date = this.apt.to();
    if (this.apt.status()) bookingFilters.status = this.apt.status();

    this.bookingService.searchBookings(bookingFilters).subscribe({
      next: bookings => {
        if (requestId !== this.apartmentSearchRequestId) return;

        this.apt.bookings.set(bookings);
        finishRequest();
      },
      error: () => {
        if (requestId !== this.apartmentSearchRequestId) return;

        this.apt.error.set('No se pudieron cargar las reservas del piso.');
        finishRequest();
      },
    });

    this.apartmentService
      .getApartmentStats(id, this.apt.from() || undefined, this.apt.to() || undefined)
      .subscribe({
        next: stats => {
          if (requestId !== this.apartmentSearchRequestId) return;

          this.apt.stats.set(stats);
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
    this.apt.id.set('');
    this.apt.from.set('');
    this.apt.to.set('');
    this.apt.status.set('');
    this.apt.loading.set(false);
    this.apt.bookings.set([]);
    this.apt.stats.set(null);
    this.apt.error.set('');
  }

  setApartmentRange(range: DateRangeValue): void {
    this.apt.from.set(range.from);
    this.apt.to.set(range.to);
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
    const hasActiveSearch = !!this.apt.stats() || this.apt.bookings().length > 0;
    if (hasActiveSearch) {
      this.searchApartmentDetail();
      return;
    }

    this.applyBookingUpdate(updated);
  }

  inputValue(event: Event): string {
    return (event.target as HTMLInputElement).value;
  }

  selectValue(event: Event): string {
    return (event.target as HTMLSelectElement).value;
  }
}
