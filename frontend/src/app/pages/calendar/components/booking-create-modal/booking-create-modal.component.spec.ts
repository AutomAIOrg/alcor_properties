import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { BookingCreateModalComponent } from './booking-create-modal.component';
import { BookingService } from '../../../../services/booking.service';
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

  beforeEach(async () => {
    bookingServiceSpy = {
      createBooking: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;
    bookingServiceSpy.createBooking.mockReturnValue(of(makeCreatedBooking()));

    await TestBed.configureTestingModule({
      imports: [BookingCreateModalComponent],
      providers: [{ provide: BookingService, useValue: bookingServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(BookingCreateModalComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('apartments', ['R180', 'R101', 'R202']);
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
});
