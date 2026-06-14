import { CurrencyPipe, DatePipe, DecimalPipe, KeyValuePipe } from '@angular/common';
import { Component, Input, inject, output, signal } from '@angular/core';
import { forkJoin } from 'rxjs';

import { Booking } from '../../../../models/booking.model';
import { ApartmentStatsResponse, BookingSearchFilters } from '../../../../models/search.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { ApartmentService } from '../../../../services/apartment.service';
import { BookingService } from '../../../../services/booking.service';
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
    KeyValuePipe,
    BookingColorPipe,
    DateRangePickerComponent,
  ],
  templateUrl: './apartment-search.component.html',
  styleUrl: './apartment-search.component.scss',
})
export class ApartmentSearchComponent {
  private apartmentService = inject(ApartmentService);
  private bookingService = inject(BookingService);
  private lastLoadRequestId = 0;

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

  readonly STATUS_OPTIONS = ['', 'Confirmed', 'Pending', 'Cancelled', 'ok'];

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
    this.apt.loading.set(true);
    this.apt.error.set('');
    this.apt.bookings.set([]);
    this.apt.stats.set(null);

    const bookingFilters: BookingSearchFilters = { apartment_id: id };
    if (this.apt.from()) bookingFilters.start_date = this.apt.from();
    if (this.apt.to()) bookingFilters.end_date = this.apt.to();
    if (this.apt.status()) bookingFilters.status = this.apt.status();

    forkJoin({
      bookings: this.bookingService.searchBookings(bookingFilters),
      stats: this.apartmentService.getApartmentStats(
        id,
        this.apt.from() || undefined,
        this.apt.to() || undefined
      ),
    }).subscribe({
      next: ({ bookings, stats }) => {
        this.apt.bookings.set(bookings);
        this.apt.stats.set(stats);
        this.apt.loading.set(false);
      },
      error: err => {
        const msg =
          err?.status === 404
            ? `El piso '${id}' no existe en la base de datos.`
            : 'Error al cargar datos del piso.';
        this.apt.error.set(msg);
        this.apt.loading.set(false);
      },
    });
  }

  clearApartmentDetail(): void {
    this.apt.id.set('');
    this.apt.from.set('');
    this.apt.to.set('');
    this.apt.status.set('');
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

  statusBreakdownEntries(breakdown: Record<string, number>): { key: string; value: number }[] {
    return Object.entries(breakdown).map(([key, value]) => ({ key, value }));
  }
}
