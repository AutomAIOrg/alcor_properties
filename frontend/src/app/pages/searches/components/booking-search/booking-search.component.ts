import { CurrencyPipe, DatePipe, DecimalPipe } from '@angular/common';
import { Component, Input, inject, output, signal } from '@angular/core';
import { forkJoin } from 'rxjs';

import { Booking } from '../../../../models/booking.model';
import { BookingSearchFilters, BookingStatsResponse } from '../../../../models/search.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { BookingService } from '../../../../services/booking.service';
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
    DecimalPipe,
    BookingColorPipe,
    DateRangePickerComponent,
  ],
  templateUrl: './booking-search.component.html',
  styleUrl: './booking-search.component.scss',
})
export class BookingSearchComponent {
  private bookingService = inject(BookingService);

  @Input() allApartmentIds: string[] = [];

  bookingSelected = output<Booking>();

  readonly STATUS_OPTIONS = ['', 'Confirmed', 'Pending', 'Cancelled', 'ok'];

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

    forkJoin({
      bookings: this.bookingService.searchBookings(filters),
      stats: this.bookingService.getBookingStats(filters),
    }).subscribe({
      next: ({ bookings, stats }) => {
        this.bkg.results.set(bookings);
        this.bkg.stats.set(stats);
        this.bkg.loading.set(false);
      },
      error: () => {
        this.bkg.error.set('Error al buscar reservas.');
        this.bkg.loading.set(false);
      },
    });
  }

  clearBookings(): void {
    this.bkg.from.set('');
    this.bkg.to.set('');
    this.bkg.apartmentId.set('');
    this.bkg.status.set('');
    this.bkg.guestName.set('');
    this.bkg.bookingNumber.set('');
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

  statusBreakdownEntries(breakdown: Record<string, number>): { key: string; value: number }[] {
    return Object.entries(breakdown).map(([key, value]) => ({ key, value }));
  }
}
