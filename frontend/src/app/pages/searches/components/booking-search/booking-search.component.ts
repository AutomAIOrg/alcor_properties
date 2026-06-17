import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, Input, inject, output, signal } from '@angular/core';

import { BASE_STATUSES, Booking } from '../../../../models/booking.model';
import { BookingSearchFilters, BookingStatsResponse } from '../../../../models/search.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { BookingService } from '../../../../services/booking.service';
import { SearchStatsGridComponent } from '../search-stats-grid/search-stats-grid.component';
import {
  DateRangePickerComponent,
  type DateRangeValue,
} from '../../../../shared/components/date-range-picker/date-range-picker.component';

@Component({
  selector: 'app-booking-search',
  standalone: true,
  imports: [
    CurrencyPipe,
    DatePipe,
    BookingColorPipe,
    DateRangePickerComponent,
    SearchStatsGridComponent,
  ],
  templateUrl: './booking-search.component.html',
  styleUrl: './booking-search.component.scss',
})
export class BookingSearchComponent {
  private bookingService = inject(BookingService);
  private bookingSearchRequestId = 0;

  @Input() allApartmentIds: string[] = [];

  bookingSelected = output<Booking>();

  readonly STATUS_OPTIONS = ['', ...BASE_STATUSES] as const;

  bkg = {
    from: signal(''),
    to: signal(''),
    apartmentId: signal(''),
    status: signal(''),
    guestName: signal(''),
    bookingNumber: signal(''),
    loading: signal(false),
    error: signal(''),
    results: signal<Booking[]>([]),
    stats: signal<BookingStatsResponse | null>(null),
  };

  searchBookings(): void {
    const requestId = ++this.bookingSearchRequestId;
    let pendingRequests = 2;
    const finishRequest = () => {
      pendingRequests -= 1;
      if (pendingRequests === 0 && requestId === this.bookingSearchRequestId) {
        this.bkg.loading.set(false);
      }
    };

    this.bkg.loading.set(true);
    this.bkg.error.set('');
    this.bkg.results.set([]);
    this.bkg.stats.set(null);

    const filters: BookingSearchFilters = {};
    if (this.bkg.from()) filters.start_date = this.bkg.from();
    if (this.bkg.to()) filters.end_date = this.bkg.to();
    if (this.bkg.apartmentId()) filters.apartment_id = this.bkg.apartmentId();
    if (this.bkg.status()) filters.status = this.bkg.status();
    if (this.bkg.guestName()) filters.guest_name = this.bkg.guestName();
    if (this.bkg.bookingNumber()) filters.booking_number = this.bkg.bookingNumber();

    this.bookingService.searchBookings(filters).subscribe({
      next: bookings => {
        if (requestId !== this.bookingSearchRequestId) return;

        this.bkg.results.set(this.filterBookingsByCheckIn(bookings));
        finishRequest();
      },
      error: () => {
        if (requestId !== this.bookingSearchRequestId) return;

        this.bkg.error.set('No se pudieron cargar las reservas.');
        finishRequest();
      },
    });

    this.bookingService.getBookingStats(filters).subscribe({
      next: stats => {
        if (requestId !== this.bookingSearchRequestId) return;

        this.bkg.stats.set(stats);
        finishRequest();
      },
      error: () => {
        if (requestId !== this.bookingSearchRequestId) return;

        this.bkg.error.set('No se pudieron cargar las estadísticas de reservas.');
        finishRequest();
      },
    });
  }

  clearBookings(): void {
    this.bookingSearchRequestId += 1;
    this.bkg.from.set('');
    this.bkg.to.set('');
    this.bkg.apartmentId.set('');
    this.bkg.status.set('');
    this.bkg.guestName.set('');
    this.bkg.bookingNumber.set('');
    this.bkg.loading.set(false);
    this.bkg.results.set([]);
    this.bkg.stats.set(null);
    this.bkg.error.set('');
  }

  setBookingRange(range: DateRangeValue): void {
    this.bkg.from.set(range.from);
    this.bkg.to.set(range.to);
  }

  completeBookingRange(range: DateRangeValue): void {
    this.setBookingRange(range);
    this.searchBookings();
  }

  searchCurrentYearBookings(): void {
    const year = new Date().getFullYear();
    this.bkg.from.set(`${year}-01-01`);
    this.bkg.to.set(`${year}-12-31`);
    this.searchBookings();
  }

  openModal(booking: Booking): void {
    this.bookingSelected.emit(booking);
  }

  applyBookingUpdate(updated: Booking): void {
    this.bkg.results.update(list =>
      list.map(booking => (booking.record_id === updated.record_id ? updated : booking))
    );
  }

  refreshAfterBookingSaved(updated: Booking): void {
    const hasActiveSearch = !!this.bkg.stats() || this.bkg.results().length > 0;
    if (hasActiveSearch) {
      this.searchBookings();
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

  private filterBookingsByCheckIn(bookings: Booking[]): Booking[] {
    const from = this.bkg.from();
    const to = this.bkg.to();

    return bookings.filter(booking => {
      if (from && booking.check_in < from) return false;
      if (to && booking.check_in > to) return false;
      return true;
    });
  }
}
