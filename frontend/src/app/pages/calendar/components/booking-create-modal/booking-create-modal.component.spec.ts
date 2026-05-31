import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { BookingCreateModalComponent } from './booking-create-modal.component';
import { BookingService } from '../../../../services/booking.service';
import { ApartmentService } from '../../../../services/apartment.service';
import { Booking } from '../../../../models/booking.model';

// ─── Fixture helper ────────────────────────────────────────────────────────────

function makeCreatedBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 99,
    booking_id: 'R180',
    guest_name: 'Juan Pérez',
    check_in: '2025-07-01',
    check_out: '2025-07-05',
    status: 'Confirmed',
    nights: 4,
    persons: 2,
    adults: 2,
    children: 0,
    price: null,
    charges: null,
    electric_allowance: null,
    email: null,
    phone: null,
    booking_number: null,
    notes: null,
    ...overrides,
  };
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('BookingCreateModalComponent', () => {
  let fixture: ComponentFixture<BookingCreateModalComponent>;
  let component: BookingCreateModalComponent;
  let bookingServiceSpy: jest.Mocked<BookingService>;
  let apartmentServiceSpy: jest.Mocked<ApartmentService>;

  beforeEach(async () => {
    bookingServiceSpy = {
      createBooking: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;
    apartmentServiceSpy = {
      getAvailableApartmentIds: jest.fn(),
    } as unknown as jest.Mocked<ApartmentService>;

    bookingServiceSpy.createBooking.mockReturnValue(of(makeCreatedBooking()));
    apartmentServiceSpy.getAvailableApartmentIds.mockReturnValue(of(['R101', 'R202']));

    await TestBed.configureTestingModule({
      imports: [BookingCreateModalComponent],
      providers: [
        { provide: BookingService, useValue: bookingServiceSpy },
        { provide: ApartmentService, useValue: apartmentServiceSpy },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(BookingCreateModalComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('apartments', ['R180', 'R101', 'R202']);
    fixture.componentRef.setInput('bookings', [
      makeCreatedBooking({
        record_id: 1,
        booking_id: 'R180',
        check_in: '2025-07-10',
        check_out: '2025-07-15',
        status: 'Confirmed',
      }),
      makeCreatedBooking({
        record_id: 2,
        booking_id: 'R101',
        check_in: '2025-07-20',
        check_out: '2025-07-25',
        status: 'Cancelled',
      }),
    ]);
    fixture.detectChanges();
  });

  // ── nights ────────────────────────────────────────────────────────────────────

  describe('nights', () => {
    it('check_in y check_out válidos calculan las noches correctamente', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
      expect(component.nights()).toBe(4);
    });

    it('sin check_out devuelve 0', () => {
      component.patch('check_in', '2025-07-01');
      expect(component.nights()).toBe(0);
    });

    it('fechas iguales devuelve 0', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-01');
      expect(component.nights()).toBe(0);
    });

    it('check_out anterior a check_in devuelve 0 (Math.max)', () => {
      component.patch('check_in', '2025-07-10');
      component.patch('check_out', '2025-07-01');
      expect(component.nights()).toBe(0);
    });
  });

  // ── patch ─────────────────────────────────────────────────────────────────────

  describe('patch', () => {
    it('actualiza el campo especificado en el draft', () => {
      component.patch('guest_name', 'María López');
      expect(component.draft().guest_name).toBe('María López');
    });

    it('valor vacío "" guarda null en el draft', () => {
      component.patch('email', '');
      expect(component.draft().email).toBeNull();
    });
  });

  // ── range calendar ────────────────────────────────────────────────────────────

  describe('range calendar', () => {
    it('openRangeCalendar abre el calendario', () => {
      component.openRangeCalendar();

      expect(component.rangeCalendarOpen()).toBe(true);
    });

    it('clearRangeDates limpia check_in, check_out y disponibilidad', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
      component.availableApartmentIds.set(['R180']);
      component.availableApartmentsError.set('Error');

      component.clearRangeDates();

      expect(component.draft().check_in).toBeNull();
      expect(component.draft().check_out).toBeNull();
      expect(component.availableApartmentIds()).toEqual([]);
      expect(component.availableApartmentsError()).toBeNull();
    });

    it('primer click en una fecha establece check_in y deja check_out en null', () => {
      component.selectRangeDate('2025-07-01');

      expect(component.draft().check_in).toBe('2025-07-01');
      expect(component.draft().check_out).toBeNull();
    });

    it('segundo click posterior establece check_out y carga apartamentos disponibles', () => {
      component.selectRangeDate('2025-07-01');
      component.selectRangeDate('2025-07-05');

      expect(component.draft().check_in).toBe('2025-07-01');
      expect(component.draft().check_out).toBe('2025-07-05');
      expect(apartmentServiceSpy.getAvailableApartmentIds).toHaveBeenCalledWith(
        '2025-07-01',
        '2025-07-05'
      );
    });

    it('si selecciona una fecha anterior al check_in, reinicia el check_in', () => {
      component.selectRangeDate('2025-07-10');
      component.selectRangeDate('2025-07-05');

      expect(component.draft().check_in).toBe('2025-07-05');
      expect(component.draft().check_out).toBeNull();
    });
  });

  // ── booked days ──────────────────────────────────────────────────────────────

  describe('booked days', () => {
    it('marca como booked los días ocupados del piso seleccionado', () => {
      component.patch('booking_id', 'R180');
      component.rangeCalendarMonth.set(new Date(2025, 6, 1)); // julio 2025

      const days = component.rangeCalendarDays();

      const bookedDay = days.find(day => day.iso === '2025-07-10');

      expect(bookedDay).toBeTruthy();
      expect(bookedDay?.isBooked).toBe(true);
      expect(bookedDay?.canSelect).toBe(false);
    });

    it('no marca como booked el día de check_out porque es fecha de salida', () => {
      component.patch('booking_id', 'R180');
      component.rangeCalendarMonth.set(new Date(2025, 6, 1));

      const days = component.rangeCalendarDays();

      const checkoutDay = days.find(day => day.iso === '2025-07-15');

      expect(checkoutDay).toBeTruthy();
      expect(checkoutDay?.isBooked).toBe(false);
    });

    it('no bloquea reservas canceladas', () => {
      component.patch('booking_id', 'R101');
      component.rangeCalendarMonth.set(new Date(2025, 6, 1));

      const days = component.rangeCalendarDays();

      const cancelledBookingDay = days.find(day => day.iso === '2025-07-20');

      expect(cancelledBookingDay).toBeTruthy();
      expect(cancelledBookingDay?.isBooked).toBe(false);
      expect(cancelledBookingDay?.canSelect).toBe(true);
    });

    it('no permite seleccionar un rango que atraviesa una reserva existente', () => {
      component.patch('booking_id', 'R180');
      component.rangeCalendarMonth.set(new Date(2025, 6, 1));
      component.selectRangeDate('2025-07-08');

      const days = component.rangeCalendarDays();

      const dayAfterBookedRangeStarts = days.find(day => day.iso === '2025-07-12');

      expect(dayAfterBookedRangeStarts).toBeTruthy();
      expect(dayAfterBookedRangeStarts?.canSelect).toBe(false);
    });
  });

  // ── available apartments ─────────────────────────────────────────────────────

  describe('available apartments', () => {
    it('sin rango completo usa todos los apartamentos recibidos por input', () => {
      expect(component.apartmentOptions()).toEqual(['R180', 'R101', 'R202']);
    });

    it('con rango completo usa availableApartmentIds', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
      component.availableApartmentIds.set(['R101']);

      expect(component.apartmentOptions()).toEqual(['R101']);
    });

    it('loadAvailableApartmentsForSelectedDates llama al servicio con check_in y check_out', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');

      component.loadAvailableApartmentsForSelectedDates();

      expect(apartmentServiceSpy.getAvailableApartmentIds).toHaveBeenCalledWith(
        '2025-07-01',
        '2025-07-05'
      );
    });

    it('loadAvailableApartmentsForSelectedDates guarda los apartamentos disponibles', () => {
      apartmentServiceSpy.getAvailableApartmentIds.mockReturnValue(of(['R101', 'R202']));

      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');

      component.loadAvailableApartmentsForSelectedDates();

      expect(component.availableApartmentIds()).toEqual(['R101', 'R202']);
      expect(component.loadingAvailableApartments()).toBe(false);
    });

    it('si el piso seleccionado deja de estar disponible, limpia booking_id', () => {
      apartmentServiceSpy.getAvailableApartmentIds.mockReturnValue(of(['R101']));

      component.patch('booking_id', 'R180');
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');

      component.loadAvailableApartmentsForSelectedDates();

      expect(component.draft().booking_id).toBeNull();
    });

    it('si falla la carga de apartamentos, guarda mensaje de error', () => {
      apartmentServiceSpy.getAvailableApartmentIds.mockReturnValue(
        throwError(() => new Error('network'))
      );

      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');

      component.loadAvailableApartmentsForSelectedDates();

      expect(component.availableApartmentIds()).toEqual([]);
      expect(component.availableApartmentsError()).toBe(
        'No se pudieron cargar los pisos disponibles.'
      );
      expect(component.loadingAvailableApartments()).toBe(false);
    });
  });

  // ── isValid ───────────────────────────────────────────────────────────────────

  describe('isValid', () => {
    function fillValid(): void {
      component.patch('booking_id', 'R180');
      component.patch('guest_name', 'Juan Pérez');
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
    }

    it('todos los campos requeridos rellenos y nights>0 → true', () => {
      fillValid();
      expect(component.isValid()).toBe(true);
    });

    it('sin booking_id → false', () => {
      fillValid();
      component.patch('booking_id', '');
      expect(component.isValid()).toBe(false);
    });

    it('sin guest_name → false', () => {
      fillValid();
      component.patch('guest_name', '');
      expect(component.isValid()).toBe(false);
    });

    it('guest_name solo espacios → false', () => {
      fillValid();
      component.patch('guest_name', '   ');
      expect(component.isValid()).toBe(false);
    });

    it('nights=0 → false', () => {
      fillValid();
      component.patch('check_out', '2025-07-01'); // misma fecha → 0 noches
      expect(component.isValid()).toBe(false);
    });
  });

  // ── save — happy path ─────────────────────────────────────────────────────────

  describe('save — happy path', () => {
    beforeEach(() => {
      component.patch('booking_id', 'R180');
      component.patch('guest_name', 'Juan Pérez');
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
    });

    it('llama a createBooking con el payload correcto', () => {
      component.save();
      expect(bookingServiceSpy.createBooking).toHaveBeenCalledTimes(1);
      const payload = bookingServiceSpy.createBooking.mock.calls[0][0];
      expect(payload.booking_id).toBe('R180');
      expect(payload.guest_name).toBe('Juan Pérez');
      expect(payload.nights).toBe(4);
      expect(payload.persons).toBe(component.draft().adults! + component.draft().children!);
    });

    it('emite created con la reserva devuelta por el servicio', () => {
      const emitted: Booking[] = [];
      component.created.subscribe(b => emitted.push(b));

      component.save();

      expect(emitted.length).toBe(1);
      expect(emitted[0].record_id).toBe(99);
    });

    it('tras guardar, saving vuelve a false', () => {
      component.save();
      expect(component.saving()).toBe(false);
    });
  });

  // ── save — errores y guards ───────────────────────────────────────────────────

  describe('save — error de red', () => {
    beforeEach(() => {
      bookingServiceSpy.createBooking.mockReturnValue(throwError(() => new Error('net')));
      component.patch('booking_id', 'R180');
      component.patch('guest_name', 'Juan Pérez');
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
    });

    it('saving vuelve a false', () => {
      component.save();
      expect(component.saving()).toBe(false);
    });

    it('no emite created', () => {
      const emitted: Booking[] = [];
      component.created.subscribe(b => emitted.push(b));
      component.save();
      expect(emitted.length).toBe(0);
    });
  });

  describe('save — guard de validación', () => {
    it('isValid()=false no llama al servicio', () => {
      // draft vacío → isValid = false
      component.save();
      expect(bookingServiceSpy.createBooking).not.toHaveBeenCalled();
    });

    it('no guarda si el rango seleccionado tiene conflictos', () => {
      component.patch('booking_id', 'R180');
      component.patch('guest_name', 'Juan Pérez');
      component.patch('check_in', '2025-07-08');
      component.patch('check_out', '2025-07-12');

      expect(component.selectedRangeHasConflicts()).toBe(true);

      component.save();

      expect(bookingServiceSpy.createBooking).not.toHaveBeenCalled();
    });
  });

  describe('save — guard de doble envío', () => {
    it('saving=true previene una segunda llamada', () => {
      component.patch('booking_id', 'R180');
      component.patch('guest_name', 'Juan Pérez');
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');

      component.saving.set(true);
      component.save();

      expect(bookingServiceSpy.createBooking).not.toHaveBeenCalled();
    });
  });

  // ── DOM ───────────────────────────────────────────────────────────────────────

  describe('DOM', () => {
    it('.nights-info no se renderiza cuando nights=0', () => {
      expect(fixture.nativeElement.querySelector('.nights-info')).toBeNull();
    });

    it('.nights-info muestra "4 noches" cuando hay 4 noches', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement.querySelector('.nights-info');
      expect(el).toBeTruthy();
      expect(el.textContent).toContain('4 noches');
    });

    it('.nights-info muestra "1 noche" (singular) cuando hay 1 noche', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-02');
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement.querySelector('.nights-info');
      expect(el.textContent).toContain('1 noche');
      expect(el.textContent).not.toContain('noches');
    });

    it('renderiza una <option> por cada piso en apartments', () => {
      const selects: HTMLSelectElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('select')
      );
      const aptOpts = selects[0].querySelectorAll('option:not([disabled])');
      expect(aptOpts.length).toBe(3);
    });

    it('click en .modal-backdrop emite close', () => {
      const spy = jest.fn();
      component.close.subscribe(spy);

      fixture.nativeElement.querySelector('.modal-backdrop').click();

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('click en .modal-card no emite close (stopPropagation)', () => {
      const spy = jest.fn();
      component.close.subscribe(spy);

      fixture.nativeElement.querySelector('.modal-card').click();

      expect(spy).not.toHaveBeenCalled();
    });

    it('botón "Crear reserva" está deshabilitado cuando el formulario es inválido', () => {
      const btn: HTMLButtonElement = fixture.nativeElement.querySelector('.btn-save');
      expect(btn.disabled).toBe(true);
    });

    it('botón "Crear reserva" se habilita cuando el formulario es válido', () => {
      component.patch('booking_id', 'R180');
      component.patch('guest_name', 'Juan Pérez');
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
      fixture.detectChanges();

      const btn: HTMLButtonElement = fixture.nativeElement.querySelector('.btn-save');
      expect(btn.disabled).toBe(false);
    });
  });

  // ── DOM — range calendar ─────────────────────────────────────────────────────

  describe('DOM — range calendar', () => {
    it('renderiza el calendario al hacer click en Entrada', () => {
      const dateBtn: HTMLButtonElement = fixture.nativeElement.querySelector('.date-range-input');

      dateBtn.click();
      fixture.detectChanges();

      expect(fixture.nativeElement.querySelector('.range-calendar')).toBeTruthy();
    });

    it('muestra mensaje informativo si no hay piso seleccionado', () => {
      component.openRangeCalendar();
      fixture.detectChanges();

      const message: HTMLElement = fixture.nativeElement.querySelector('.range-message');

      expect(message).toBeTruthy();
      expect(message.textContent).toContain('Puedes seleccionar fechas primero');
    });

    it('renderiza días disabled cuando hay reserva del piso seleccionado', () => {
      component.patch('booking_id', 'R180');
      component.openRangeCalendar();
      component.rangeCalendarMonth.set(new Date(2025, 6, 1));

      fixture.detectChanges();

      const disabledDays: NodeListOf<HTMLButtonElement> =
        fixture.nativeElement.querySelectorAll('.range-day.disabled');

      expect(disabledDays.length).toBeGreaterThan(0);
    });

    it('el select de pisos muestra solo apartamentos disponibles cuando hay rango completo', () => {
      component.patch('check_in', '2025-07-01');
      component.patch('check_out', '2025-07-05');
      component.availableApartmentIds.set(['R101']);

      fixture.detectChanges();

      const selects: HTMLSelectElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('select')
      );

      const apartmentOptions = selects[0].querySelectorAll('option:not([disabled])');

      expect(apartmentOptions.length).toBe(1);
      expect(apartmentOptions[0].textContent?.trim()).toBe('R101');
    });
  });
});
