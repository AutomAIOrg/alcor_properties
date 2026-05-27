import { Component, computed, inject, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Booking, BASE_STATUSES } from '../../../../models/booking.model';
import { BookingService } from '../../../../services/booking.service';

type BookingCreate = Omit<Booking, 'record_id'>;
type InputField = 'guest_name' | 'check_in' | 'check_out' | 'email' | 'phone' | 'booking_number';
type NumberField = 'adults' | 'children' | 'price' | 'charges' | 'electric_allowance';
type SelectField = 'booking_id' | 'status';
type TextareaField = 'notes';

@Component({
  selector: 'app-booking-create-modal',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './booking-create-modal.component.html',
  styleUrl: './booking-create-modal.component.scss',
})
export class BookingCreateModalComponent {
  close = output<void>();
  created = output<Booking>();

  // Lista de pisos disponibles, pasada desde el componente padre.
  apartments = input<string[]>([]);

  private bookingService = inject(BookingService);
  readonly BASE_STATUSES = BASE_STATUSES;
  saving = signal(false);

  draft = signal<Partial<BookingCreate>>({
    status: 'Confirmed',
    adults: 1,
    children: 0,
  });

  nights = computed(() => {
    const { check_in, check_out } = this.draft();
    if (!check_in || !check_out) return 0;
    return Math.max(
      0,
      Math.round((new Date(check_out).getTime() - new Date(check_in).getTime()) / 86_400_000)
    );
  });

  patch(field: keyof BookingCreate, value: unknown): void {
    this.draft.update(d => ({ ...d, [field]: value === '' ? null : value }));
  }

  patchInput(field: InputField, event: Event): void {
    const input = event.target as HTMLInputElement;
    this.patch(field, input.value);
  }

  patchNumber(field: NumberField, event: Event): void {
    const input = event.target as HTMLInputElement;
    this.patch(field, input.value === '' ? null : Number(input.value));
  }

  patchSelect(field: SelectField, event: Event): void {
    const select = event.target as HTMLSelectElement;
    this.patch(field, select.value);
  }

  patchTextarea(field: TextareaField, event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    this.patch(field, textarea.value);
  }

  isValid(): boolean {
    const d = this.draft();
    return !!(
      d.booking_id?.trim() &&
      d.guest_name?.trim() &&
      d.check_in &&
      d.check_out &&
      this.nights() > 0
    );
  }

  save(): void {
    if (this.saving() || !this.isValid()) return;
    this.saving.set(true);
    const d = this.draft();
    const payload: BookingCreate = {
      booking_id: d.booking_id!,
      guest_name: d.guest_name!,
      check_in: d.check_in!,
      check_out: d.check_out!,
      status: d.status ?? 'Confirmed',
      nights: this.nights(),
      persons: (d.adults ?? 1) + (d.children ?? 0),
      adults: d.adults ?? 1,
      children: d.children ?? 0,
      price: d.price ?? null,
      charges: d.charges ?? null,
      electric_allowance: d.electric_allowance ?? null,
      email: d.email ?? null,
      phone: d.phone ?? null,
      booking_number: d.booking_number ?? null,
      notes: d.notes ?? null,
    };
    this.bookingService.createBooking(payload).subscribe({
      next: created => {
        this.created.emit(created);
        this.saving.set(false);
      },
      error: () => this.saving.set(false),
    });
  }
}
