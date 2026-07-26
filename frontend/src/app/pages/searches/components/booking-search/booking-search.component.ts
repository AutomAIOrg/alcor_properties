import { CurrencyPipe, DatePipe } from '@angular/common';
import { Component, ElementRef, Input, inject, output, signal, viewChild } from '@angular/core';

import { BASE_STATUSES, Booking } from '../../../../models/booking.model';
import { BookingSearchFilters, BookingStatsResponse } from '../../../../models/search.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { BookingService } from '../../../../services/booking.service';
import { SearchStatsGridComponent } from '../search-stats-grid/search-stats-grid.component';
import {
  DateRangePickerComponent,
  type DateRangeValue,
} from '../../../../shared/components/date-range-picker/date-range-picker.component';
import { exportBookingStatsToExcel } from '../../../../shared/utils/stats-excel-export';
import { exportModelo210ToExcel } from '../../../../shared/utils/modelo-210-excel-export';

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
  host: {
    '(document:click)': 'onDocumentClick($event)',
  },
})
export class BookingSearchComponent {
  private bookingService = inject(BookingService);
  private bookingSearchRequestId = 0;

  @Input() allApartmentIds: string[] = [];

  bookingSelected = output<Booking>();

  readonly STATUS_OPTIONS = [...BASE_STATUSES] as const;

  statusDropdownOpen = signal(false);
  private statusDropdownRef = viewChild<ElementRef>('statusDropdown');

  bkg = {
    from: signal(''),
    to: signal(''),
    apartmentId: signal(''),
    statuses: signal<string[]>([]),
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
    if (this.bkg.to()) filters.end_date = this.addOneDay(this.bkg.to());
    if (this.bkg.apartmentId()) filters.apartment_id = this.bkg.apartmentId();
    const statuses = this.bkg.statuses();
    if (statuses.length > 0) filters.status = statuses.join(',');
    if (this.bkg.guestName()) filters.guest_name = this.bkg.guestName();
    if (this.bkg.bookingNumber()) filters.booking_number = this.bkg.bookingNumber();

    this.bookingService.searchBookings(filters).subscribe({
      next: bookings => {
        if (requestId !== this.bookingSearchRequestId) return;

        this.bkg.results.set(bookings);
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

        this.bkg.stats.set({
          ...stats,
          start_date: this.bkg.from() || null,
          end_date: this.bkg.to() || null,
        });
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
    this.bkg.statuses.set([]);
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

  onFilterChange(field: 'apartmentId' | 'guestName' | 'bookingNumber', event: Event): void {
    const value = this.inputValue(event);

    switch (field) {
      case 'apartmentId':
        this.bkg.apartmentId.set(value);
        break;
      case 'guestName':
        this.bkg.guestName.set(value);
        break;
      case 'bookingNumber':
        this.bkg.bookingNumber.set(value);
        break;
    }

    this.searchBookingsIfActive();
  }

  toggleStatusDropdown(): void {
    this.statusDropdownOpen.update(open => !open);
  }

  isStatusSelected(status: string): boolean {
    const selected = this.bkg.statuses();
    return selected.length === 0 || selected.includes(status);
  }

  toggleStatus(status: string): void {
    const current = this.bkg.statuses();

    if (current.length === 0) {
      this.bkg.statuses.set(this.STATUS_OPTIONS.filter(s => s !== status));
    } else if (current.includes(status)) {
      const next = current.filter(s => s !== status);
      this.bkg.statuses.set(next.length === 0 ? [] : next);
    } else {
      const next = [...current, status];
      this.bkg.statuses.set(next.length === this.STATUS_OPTIONS.length ? [] : next);
    }

    this.searchBookingsIfActive();
  }

  statusLabel(): string {
    const selected = this.bkg.statuses();
    if (selected.length === 0) return 'Todos';
    if (selected.length === 1) return selected[0];
    return `${selected.length} estados`;
  }

  onDocumentClick(event: Event): void {
    const ref = this.statusDropdownRef();
    if (this.statusDropdownOpen() && ref && !ref.nativeElement.contains(event.target)) {
      this.statusDropdownOpen.set(false);
    }
  }

  private searchBookingsIfActive(): void {
    if (this.isSearchActive()) {
      this.searchBookings();
    }
  }

  private isSearchActive(): boolean {
    return this.bkg.stats() !== null || this.bkg.results().length > 0;
  }

  searchCurrentYearBookings(): void {
    const year = new Date().getFullYear();
    this.bkg.from.set(`${year}-01-01`);
    this.bkg.to.set(`${year}-12-31`);
    this.searchBookings();
  }

  downloadStatsExcel(): void {
    const stats = this.bkg.stats();
    if (!stats) return;

    exportBookingStatsToExcel(stats);
  }

  async downloadModelo210(): Promise<void> {
    const apartmentId = this.bkg.apartmentId().trim();
    if (!apartmentId) {
      this.bkg.error.set('Selecciona un ID de piso para descargar el Modelo 210.');
      return;
    }

    const bookings = this.bkg
      .results()
      .filter(booking => booking.apartment_id.trim() === apartmentId);

    if (bookings.length === 0) {
      this.bkg.error.set('No hay reservas del piso seleccionado para exportar.');
      return;
    }

    this.bkg.error.set('');

    try {
      await exportModelo210ToExcel(bookings, apartmentId);
    } catch {
      this.bkg.error.set('No se pudo generar el Modelo 210.');
    }
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

  private addOneDay(isoDate: string): string {
    const [year, month, day] = isoDate.split('-').map(Number);
    const date = new Date(Date.UTC(year, month - 1, day));
    date.setUTCDate(date.getUTCDate() + 1);
    return date.toISOString().slice(0, 10);
  }
}
