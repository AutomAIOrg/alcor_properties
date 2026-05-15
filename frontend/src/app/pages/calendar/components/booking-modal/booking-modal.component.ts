import { Component, computed, inject, input, output, signal } from '@angular/core';
import { CurrencyPipe, DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Booking, BASE_STATUSES } from '../../../../models/booking.model';
import { BookingColorPipe } from '../../../../pipes/booking-color.pipe';
import { BookingService } from '../../../../services/booking.service';
import { AuthService } from '../../../../auth/auth.service';


@Component({
  selector: 'app-booking-modal',
  standalone: true,
  imports: [CurrencyPipe, DatePipe, BookingColorPipe, FormsModule],
  templateUrl: './booking-modal.component.html',
  styleUrl: './booking-modal.component.scss'
})
export class BookingModalComponent {
  booking = input.required<Booking>();
  close   = output<void>();
  saved   = output<Booking>();

  private bookingService = inject(BookingService);
  authService            = inject(AuthService);

  statusOptions = computed(() => {
    const currentLower = this.booking().status?.toLowerCase();
    const inBase = (BASE_STATUSES as readonly string[]).some(s => s.toLowerCase() === currentLower);

    return inBase ? BASE_STATUSES : [this.booking().status, ...BASE_STATUSES];
  });

  editing = signal(false);
  saving  = signal(false);
  draft   = signal<Partial<Booking>>({});

  initials = computed(() => {
    const name = this.booking().guest_name ?? '';
    return name.split(' ').slice(0, 2).map(w => w[0]).join('').toUpperCase() || '?';
  });

  startEdit(): void {
    this.draft.set({ ...this.booking() });
    this.editing.set(true);
  }

  cancelEdit(): void {
    this.editing.set(false);
  }

  saveEdit(): void {
    if (this.saving()) return;
    this.saving.set(true);
    this.bookingService.updateBooking(this.booking().record_id, this.draft())
      .subscribe({
        next: updated => {
          this.saved.emit(updated);
          this.editing.set(false);
          this.saving.set(false);
        },
        error: () => this.saving.set(false)
      });
  }

  patchDraft(field: keyof Booking, value: unknown): void {
    this.draft.update(d => ({ ...d, [field]: value === '' ? null : value }));
  }
}
