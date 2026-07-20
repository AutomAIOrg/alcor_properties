import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, input, output, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Booking, BASE_STATUSES } from '../../../models/booking.model';
import { BookingColorPipe } from '../../../pipes/booking-color.pipe';
import { BookingService } from '../../../services/booking.service';
import { AuthService } from '../../../auth/auth.service';
import { DismissableBackdropDirective } from '../../directives/dismissable-backdrop.directive';

type DraftInputField =
  | 'guest_name'
  | 'check_in'
  | 'check_out'
  | 'email'
  | 'phone'
  | 'booking_number';
type DraftNumberField =
  | 'adults'
  | 'children'
  | 'persons'
  | 'price'
  | 'charges'
  | 'electric_allowance';
type DraftSelectField = 'status';

const DATE_CONFLICT_MESSAGE = 'El piso ya tiene una reserva en ese rango de fechas.';

@Component({
  selector: 'app-booking-modal',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, BookingColorPipe, FormsModule, DismissableBackdropDirective],
  templateUrl: './booking-modal.component.html',
  styleUrl: './booking-modal.component.scss',
})
export class BookingModalComponent {
  booking = input.required<Booking>();
  close = output<void>();
  saved = output<Booking>();

  private bookingService = inject(BookingService);
  private bookingsRequestId = 0;
  authService = inject(AuthService);

  statusOptions = computed(() => {
    const currentLower = this.booking().status?.toLowerCase();
    const inBase = (BASE_STATUSES as readonly string[]).some(s => s.toLowerCase() === currentLower);

    return inBase ? BASE_STATUSES : [this.booking().status, ...BASE_STATUSES];
  });

  editing = signal(false);
  saving = signal(false);
  draft = signal<Partial<Booking>>({});
  electricAllowanceWarning = signal('');
  saveError = signal('');
  apartmentBookings = signal<Booking[]>([]);

  /** Solape con otra reserva activa del mismo piso (excluye la que se está editando). */
  selectedRangeHasConflicts = computed(() => {
    const d = this.draft();
    const checkIn = d.check_in;
    const checkOut = d.check_out;

    if (!checkIn || !checkOut || checkOut <= checkIn) return false;
    if (this.isNonBlockingStatus(d.status)) return false;

    const apartment = (d.apartment_id ?? this.booking().apartment_id)?.trim();
    if (!apartment) return false;

    const currentId = this.booking().record_id;

    return this.apartmentBookings().some(
      other =>
        other.record_id !== currentId &&
        other.apartment_id?.trim() === apartment &&
        !this.isNonBlockingStatus(other.status) &&
        checkIn < other.check_out &&
        checkOut > other.check_in
    );
  });

  initials = computed(() => {
    const name = this.booking().guest_name ?? '';
    return (
      name
        .split(' ')
        .slice(0, 2)
        .map(w => w[0])
        .join('')
        .toUpperCase() || '?'
    );
  });

  startEdit(): void {
    this.draft.set({ ...this.booking() });
    this.electricAllowanceWarning.set('');
    this.saveError.set('');
    this.editing.set(true);
    this.loadBookingsForApartment(this.booking().apartment_id);
  }

  cancelEdit(): void {
    this.electricAllowanceWarning.set('');
    this.saveError.set('');
    this.apartmentBookings.set([]);
    this.editing.set(false);
  }

  saveEdit(): void {
    if (this.saving()) return;
    if (this.draft().electric_allowance !== this.booking().electric_allowance) {
      this.electricAllowanceWarning.set(
        'La luz incluida es un campo calculado automáticamente y no se puede modificar manualmente.'
      );
      return;
    }
    if (this.selectedRangeHasConflicts()) {
      this.saveError.set(DATE_CONFLICT_MESSAGE);
      return;
    }
    this.electricAllowanceWarning.set('');
    this.saveError.set('');
    this.saving.set(true);
    this.bookingService.updateBooking(this.booking().record_id, this.draft()).subscribe({
      next: updated => {
        this.saved.emit(updated);
        this.editing.set(false);
        this.saving.set(false);
        this.apartmentBookings.set([]);
      },
      error: (err: unknown) => {
        this.saving.set(false);
        if (err instanceof HttpErrorResponse && err.status === 409) {
          const detail = err.error?.detail;
          this.saveError.set(typeof detail === 'string' ? detail : DATE_CONFLICT_MESSAGE);
        }
      },
    });
  }

  patchDraft(field: keyof Booking, value: unknown): void {
    if (field === 'electric_allowance') {
      this.electricAllowanceWarning.set('');
    }
    if (field === 'check_in' || field === 'check_out' || field === 'status') {
      this.saveError.set('');
    }
    this.draft.update(d => ({ ...d, [field]: value === '' ? null : value }));
  }

  patchDraftInput(field: DraftInputField, event: Event): void {
    const input = event.target as HTMLInputElement;
    this.patchDraft(field, input.value);
  }

  patchDraftNumber(field: DraftNumberField, event: Event): void {
    const input = event.target as HTMLInputElement;
    this.patchDraft(field, input.value === '' ? null : Number(input.value));
  }

  patchDraftSelect(field: DraftSelectField, event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.patchDraft(field, select.value);
  }

  private loadBookingsForApartment(apartmentId: string | null | undefined): void {
    const apartment = apartmentId?.trim();

    if (!apartment) {
      this.apartmentBookings.set([]);
      return;
    }

    const requestId = ++this.bookingsRequestId;
    this.apartmentBookings.set([]);

    this.bookingService.searchBookings({ apartment_id: apartment }).subscribe({
      next: bookings => {
        if (requestId !== this.bookingsRequestId) return;
        this.apartmentBookings.set(bookings);
      },
      error: () => {
        if (requestId !== this.bookingsRequestId) return;
        this.apartmentBookings.set([]);
      },
    });
  }

  private isNonBlockingStatus(status: string | null | undefined): boolean {
    return status?.trim().toLowerCase() === 'cancelled';
  }
}
