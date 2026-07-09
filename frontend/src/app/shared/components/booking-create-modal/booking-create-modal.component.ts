import {
  Component,
  HostListener,
  OnInit,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Booking, BASE_STATUSES } from '../../../models/booking.model';
import { BookingService } from '../../../services/booking.service';
import { ApartmentService } from '../../../services/apartment.service';
import { DismissableBackdropDirective } from '../../directives/dismissable-backdrop.directive';

type BookingCreate = Omit<Booking, 'record_id' | 'electric_allowance'>;

export type BookingCreateInitialValues = Partial<
  Pick<Booking, 'apartment_id' | 'check_in' | 'check_out'>
>;

type BookingCreateDraft = Partial<{
  [K in keyof BookingCreate]: BookingCreate[K] | null;
}>;

type InputField = 'guest_name' | 'check_in' | 'check_out' | 'email' | 'phone' | 'booking_number';
type NumberField = 'adults' | 'children' | 'price' | 'charges';
type SelectField = 'apartment_id' | 'status';
type TextareaField = 'notes';

type CalendarDay = {
  iso: string;
  label: number;
  inCurrentMonth: boolean;
  isStart: boolean;
  isEnd: boolean;
  inRange: boolean;
  isBooked: boolean;
  canSelect: boolean;
};

type AvailabilityLoadOptions = {
  preserveSelectedApartment?: boolean;
};

@Component({
  selector: 'app-booking-create-modal',
  standalone: true,
  imports: [FormsModule, DismissableBackdropDirective],
  templateUrl: './booking-create-modal.component.html',
  styleUrl: './booking-create-modal.component.scss',
})
export class BookingCreateModalComponent implements OnInit {
  close = output<void>();
  created = output<Booking>();

  apartments = input<string[]>([]);
  bookings = input<Booking[]>([]);
  initialValues = input<BookingCreateInitialValues | null>(null);

  private bookingService = inject(BookingService);
  private apartmentService = inject(ApartmentService);
  private bookingsRequestId = 0;
  readonly BASE_STATUSES = BASE_STATUSES;
  readonly WEEKDAYS = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];

  saving = signal(false);

  draft = signal<BookingCreateDraft>({
    status: 'Confirmed',
    adults: 1,
    children: 0,
  });

  rangeCalendarOpen = signal(false);
  rangeCalendarMonth = signal(new Date());
  rangeHoverIso = signal<string | null>(null);

  selectedRangeHasConflicts = computed(() => {
    const d = this.draft();

    if (!d.apartment_id || !d.check_in || !d.check_out) {
      return false;
    }

    return this.rangeHasBookedNights(d.check_in, d.check_out);
  });

  rangeCalendarTitle = computed(() => {
    const d = this.rangeCalendarMonth();

    return new Intl.DateTimeFormat('es-ES', {
      month: 'long',
      year: 'numeric',
    }).format(d);
  });

  rangeCalendarDays = computed<CalendarDay[]>(() => {
    const monthDate = this.rangeCalendarMonth();
    const year = monthDate.getFullYear();
    const month = monthDate.getMonth();

    const firstDay = new Date(year, month, 1);
    const firstWeekDay = (firstDay.getDay() + 6) % 7;
    const gridStart = new Date(year, month, 1 - firstWeekDay);

    const d = this.draft();
    const start = d.check_in ?? null;
    const selectedEnd = d.check_out ?? null;
    const hover = this.rangeHoverIso();

    const previewEnd =
      start && !selectedEnd && hover && hover > start && this.canSelectDate(hover)
        ? hover
        : selectedEnd;

    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(gridStart);
      date.setDate(gridStart.getDate() + index);

      const iso = this.toIso(date);
      const isBooked = this.isBookedNight(iso);
      const canSelect = this.canSelectDate(iso);

      return {
        iso,
        label: date.getDate(),
        inCurrentMonth: date.getMonth() === month,
        isStart: iso === start,
        isEnd: iso === previewEnd,
        inRange: !!start && !!previewEnd && iso > start && iso < previewEnd,
        isBooked,
        canSelect,
      };
    });
  });

  nights = computed(() => {
    const { check_in, check_out } = this.draft();

    if (!check_in || !check_out) return 0;

    const start = this.fromIso(check_in);
    const end = this.fromIso(check_out);

    return Math.max(0, Math.round((end.getTime() - start.getTime()) / 86_400_000));
  });

  availableApartmentIds = signal<string[]>([]);
  apartmentBookings = signal<Booking[]>([]);
  apartmentBookingsLoadedFor = signal<string | null>(null);
  loadingAvailableApartments = signal(false);
  availableApartmentsError = signal<string | null>(null);

  hasCompleteDateRange = computed(() => {
    const d = this.draft();

    return !!d.check_in && !!d.check_out && this.nights() > 0;
  });

  apartmentOptions = computed(() => {
    if (this.hasCompleteDateRange()) {
      return this.availableApartmentIds();
    }

    return this.apartments();
  });

  apartmentPlaceholder = computed(() => {
    if (this.loadingAvailableApartments()) {
      return 'Cargando pisos disponibles...';
    }

    if (this.hasCompleteDateRange()) {
      return 'Selecciona un piso disponible';
    }

    return 'Selecciona un piso';
  });

  ngOnInit(): void {
    this.applyInitialValues();
  }

  loadAvailableApartmentsForSelectedDates(options: AvailabilityLoadOptions = {}): void {
    const d = this.draft();

    if (!d.check_in || !d.check_out || this.nights() <= 0) {
      this.availableApartmentIds.set([]);
      this.availableApartmentsError.set(null);
      return;
    }

    this.loadingAvailableApartments.set(true);
    this.availableApartmentsError.set(null);

    this.apartmentService.getAvailableApartmentIds(d.check_in, d.check_out).subscribe({
      next: apartmentIds => {
        const selectedApartment = this.draft().apartment_id?.trim() || null;
        const nextApartmentIds =
          options.preserveSelectedApartment &&
          selectedApartment &&
          !apartmentIds.includes(selectedApartment)
            ? [selectedApartment, ...apartmentIds]
            : apartmentIds;

        this.availableApartmentIds.set(nextApartmentIds);

        if (selectedApartment && !nextApartmentIds.includes(selectedApartment)) {
          this.draft.update(current => ({
            ...current,
            apartment_id: null,
          }));
        }

        this.loadingAvailableApartments.set(false);
      },
      error: () => {
        this.availableApartmentIds.set([]);
        this.availableApartmentsError.set('No se pudieron cargar los pisos disponibles.');
        this.loadingAvailableApartments.set(false);
      },
    });
  }

  openRangeCalendar(event?: MouseEvent): void {
    event?.stopPropagation();

    if (this.rangeCalendarOpen() && this.hasIncompleteRange()) {
      this.clearRangeDates();
      this.closeRangeCalendar();
      return;
    }

    const d = this.draft();

    if (d.check_in) {
      this.rangeCalendarMonth.set(this.fromIso(d.check_in));
    } else {
      this.rangeCalendarMonth.set(new Date());
    }

    this.rangeCalendarOpen.set(true);
  }

  onBackdropClick(): void {
    if (this.rangeCalendarOpen() && this.hasIncompleteRange()) {
      this.clearRangeDates();
    }

    this.closeRangeCalendar();
    this.close.emit();
  }

  @HostListener('document:click', ['$event.target'])
  onDocumentClick(target: EventTarget | null): void {
    if (!(target instanceof Element)) return;
    if (
      !this.rangeCalendarOpen() ||
      target.closest('.range-calendar') ||
      target.closest('.date-range-input')
    ) {
      return;
    }

    if (this.hasIncompleteRange()) {
      this.clearRangeDates();
    }

    this.closeRangeCalendar();
  }

  onModalCardClick(event: Event): void {
    event.stopPropagation();
    if (!this.rangeCalendarOpen()) return;

    const target = event.target as Element;
    if (target.closest('.range-calendar') || target.closest('.date-range-input')) return;

    if (this.hasIncompleteRange()) {
      this.clearRangeDates();
    }

    this.closeRangeCalendar();
  }

  closeRangeCalendar(): void {
    this.rangeCalendarOpen.set(false);
    this.rangeHoverIso.set(null);
  }

  prevRangeMonth(): void {
    const d = this.rangeCalendarMonth();
    this.rangeCalendarMonth.set(new Date(d.getFullYear(), d.getMonth() - 1, 1));
  }

  nextRangeMonth(): void {
    const d = this.rangeCalendarMonth();
    this.rangeCalendarMonth.set(new Date(d.getFullYear(), d.getMonth() + 1, 1));
  }

  onRangeDayHover(day: CalendarDay): void {
    if (!day.canSelect) return;
    this.rangeHoverIso.set(day.iso);
  }

  selectRangeDate(iso: string): void {
    if (!this.canSelectDate(iso)) return;

    const d = this.draft();
    const start = d.check_in;
    const end = d.check_out;

    if (!start || end) {
      this.draft.update(current => ({
        ...current,
        check_in: iso,
        check_out: null,
      }));
      return;
    }

    if (iso <= start) {
      this.draft.update(current => ({
        ...current,
        check_in: iso,
        check_out: null,
      }));
      return;
    }

    this.draft.update(current => ({
      ...current,
      check_out: iso,
    }));

    this.loadAvailableApartmentsForSelectedDates();
    this.closeRangeCalendar();
  }

  clearRangeDates(): void {
    this.draft.update(current => ({
      ...current,
      check_in: null,
      check_out: null,
    }));

    this.availableApartmentIds.set([]);
    this.availableApartmentsError.set(null);
    this.rangeCalendarMonth.set(this.currentMonthDate());
    this.rangeHoverIso.set(null);
  }

  formatDisplayDate(iso: string | null | undefined): string {
    if (!iso) return '';

    const [year, month, day] = iso.split('-');

    return `${day}/${month}/${year}`;
  }

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
    const value = select.value;

    if (field === 'apartment_id') {
      this.draft.update(d => ({
        ...d,
        apartment_id: value,
      }));

      this.loadBookingsForApartment(value);
      this.rangeHoverIso.set(null);
      return;
    }

    this.patch(field, value);
  }

  patchTextarea(field: TextareaField, event: Event): void {
    const textarea = event.target as HTMLTextAreaElement;
    this.patch(field, textarea.value);
  }

  isValid(): boolean {
    const d = this.draft();

    return !!(
      d.apartment_id?.trim() &&
      d.guest_name?.trim() &&
      d.check_in &&
      d.check_out &&
      this.nights() > 0 &&
      !this.selectedRangeHasConflicts()
    );
  }

  save(): void {
    if (this.saving() || !this.isValid()) return;

    this.saving.set(true);

    const d = this.draft();

    const payload: BookingCreate = {
      apartment_id: d.apartment_id!,
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
      email: d.email ?? null,
      phone: d.phone ?? null,
      booking_number: d.booking_number ?? null,
      notes: d.notes ?? null,
      notes_cleaning: null,
    };

    this.bookingService.createBooking(payload).subscribe({
      next: created => {
        this.created.emit(created);
        this.saving.set(false);
      },
      error: () => this.saving.set(false),
    });
  }

  private canSelectDate(iso: string): boolean {
    const d = this.draft();

    const start = d.check_in;
    const end = d.check_out;

    // Si todavía no hay piso, dejamos seleccionar fechas libremente.
    // Después usaremos esas fechas para filtrar pisos disponibles desde backend.
    if (!d.apartment_id) {
      if (!start || end) {
        return true;
      }

      if (iso <= start) {
        return true;
      }

      return true;
    }

    if (this.isBookedNight(iso)) {
      return false;
    }

    if (!start || end) {
      return true;
    }

    if (iso <= start) {
      return true;
    }

    return !this.rangeHasBookedNights(start, iso);
  }

  private isBookedNight(iso: string): boolean {
    return this.blockingBookingsForSelectedApartment().some(
      booking => booking.check_in <= iso && iso < booking.check_out
    );
  }

  private rangeHasBookedNights(startIso: string, endIso: string): boolean {
    if (endIso <= startIso) return false;

    return this.blockingBookingsForSelectedApartment().some(
      booking => startIso < booking.check_out && endIso > booking.check_in
    );
  }

  private blockingBookingsForSelectedApartment(): Booking[] {
    const apartment = this.draft().apartment_id?.trim();

    if (!apartment) return [];

    const bookings =
      this.apartmentBookingsLoadedFor() === apartment ? this.apartmentBookings() : this.bookings();

    return bookings.filter(
      booking =>
        booking.apartment_id?.trim() === apartment && !this.isNonBlockingStatus(booking.status)
    );
  }

  private loadBookingsForApartment(apartmentId: string | null | undefined): void {
    const apartment = apartmentId?.trim();

    if (!apartment) {
      this.apartmentBookings.set([]);
      this.apartmentBookingsLoadedFor.set(null);
      return;
    }

    const requestId = ++this.bookingsRequestId;
    this.apartmentBookings.set([]);
    this.apartmentBookingsLoadedFor.set(null);

    this.bookingService.searchBookings({ apartment_id: apartment }).subscribe({
      next: bookings => {
        if (requestId !== this.bookingsRequestId) return;
        if (this.draft().apartment_id?.trim() !== apartment) return;

        this.apartmentBookings.set(bookings);
        this.apartmentBookingsLoadedFor.set(apartment);
      },
      error: () => {
        if (requestId !== this.bookingsRequestId) return;

        this.apartmentBookings.set([]);
        this.apartmentBookingsLoadedFor.set(null);
      },
    });
  }

  private isNonBlockingStatus(status: string | null | undefined): boolean {
    return status?.trim().toLowerCase() === 'cancelled';
  }

  private hasIncompleteRange(): boolean {
    const d = this.draft();
    return (!!d.check_in && !d.check_out) || (!d.check_in && !!d.check_out);
  }

  private toIso(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
  }

  private fromIso(iso: string): Date {
    const [year, month, day] = iso.split('-').map(Number);

    return new Date(year, month - 1, day);
  }

  private currentMonthDate(): Date {
    const today = new Date();

    return new Date(today.getFullYear(), today.getMonth(), 1);
  }

  private applyInitialValues(): void {
    const values = this.initialValues();
    if (!values) return;

    const apartmentId = values.apartment_id?.trim() || null;
    const checkIn = values.check_in || null;
    const checkOut = values.check_out || null;

    this.draft.update(current => ({
      ...current,
      apartment_id: apartmentId,
      check_in: checkIn,
      check_out: checkOut,
    }));

    this.loadBookingsForApartment(apartmentId);

    if (checkIn) {
      this.rangeCalendarMonth.set(this.fromIso(checkIn));
    }

    if (checkIn && checkOut && this.nights() > 0) {
      if (apartmentId) {
        this.availableApartmentIds.set([apartmentId]);
      }

      this.loadAvailableApartmentsForSelectedDates({ preserveSelectedApartment: true });
    }
  }
}
