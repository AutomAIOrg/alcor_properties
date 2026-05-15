import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { BookingModalComponent } from './booking-modal.component';
import { BookingService } from '../../../../services/booking.service';
import { Booking, BASE_STATUSES } from '../../../../models/booking.model';

// ─── Fixture helper ────────────────────────────────────────────────────────────

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1, booking_id: 'R180', guest_name: 'Ana García',
    check_in: '2025-06-01', check_out: '2025-06-07',
    status: 'Confirmed', nights: 6, persons: 2,
    adults: 2, children: 0, price: 600, charges: 50,
    electric_allowance: null, email: 'ana@test.com', phone: '+34600000000',
    booking_number: 'BK001', notes: null,
    ...overrides
  };
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('BookingModalComponent', () => {
  let fixture: ComponentFixture<BookingModalComponent>;
  let component: BookingModalComponent;
  let bookingServiceSpy: jest.Mocked<BookingService>;

  beforeEach(async () => {
    bookingServiceSpy = {
      updateBooking: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;
    bookingServiceSpy.updateBooking.mockReturnValue(of(makeBooking({ guest_name: 'Updated' })));

    await TestBed.configureTestingModule({
      imports: [BookingModalComponent],
      providers: [{ provide: BookingService, useValue: bookingServiceSpy }],
    }).compileComponents();

    fixture = TestBed.createComponent(BookingModalComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('booking', makeBooking());
    fixture.detectChanges();
  });

  // ── initials ──────────────────────────────────────────────────────────────────

  describe('initials', () => {
    it('"Ana García" → "AG"', () => {
      fixture.componentRef.setInput('booking', makeBooking({ guest_name: 'Ana García' }));
      fixture.detectChanges();
      expect(component.initials()).toBe('AG');
    });

    it('nombre de una sola palabra → primera letra en mayúscula', () => {
      fixture.componentRef.setInput('booking', makeBooking({ guest_name: 'Ana' }));
      fixture.detectChanges();
      expect(component.initials()).toBe('A');
    });

    it('nombre vacío → "?"', () => {
      fixture.componentRef.setInput('booking', makeBooking({ guest_name: '' }));
      fixture.detectChanges();
      expect(component.initials()).toBe('?');
    });

    it('guest_name null → "?"', () => {
      fixture.componentRef.setInput('booking', makeBooking({ guest_name: null as unknown as string }));
      fixture.detectChanges();
      expect(component.initials()).toBe('?');
    });
  });

  // ── statusOptions ─────────────────────────────────────────────────────────────

  describe('statusOptions', () => {
    it('status en BASE_STATUSES devuelve exactamente BASE_STATUSES', () => {
      fixture.componentRef.setInput('booking', makeBooking({ status: 'Confirmed' }));
      fixture.detectChanges();
      expect(component.statusOptions()).toEqual(BASE_STATUSES as unknown as string[]);
    });

    it('status fuera de BASE_STATUSES lo antepone a la lista', () => {
      fixture.componentRef.setInput('booking', makeBooking({ status: 'Custom' }));
      fixture.detectChanges();
      const opts = component.statusOptions();
      expect(opts[0]).toBe('Custom');
      expect(opts.length).toBe(BASE_STATUSES.length + 1);
    });

    it('la comparación es case-insensitive ("confirmed" = "Confirmed")', () => {
      fixture.componentRef.setInput('booking', makeBooking({ status: 'confirmed' }));
      fixture.detectChanges();
      // "confirmed" está en BASE_STATUSES (case-insensitive) → no se antepone
      expect(component.statusOptions().length).toBe(BASE_STATUSES.length);
    });
  });

  // ── startEdit / cancelEdit ────────────────────────────────────────────────────

  describe('startEdit', () => {
    it('copia booking al draft y pone editing=true', () => {
      component.startEdit();
    expect(component.editing()).toBe(true);
      expect(component.draft().guest_name).toBe('Ana García');
    });
  });

  describe('cancelEdit', () => {
    it('pone editing=false sin llamar al servicio', () => {
      component.startEdit();
      component.cancelEdit();
      expect(component.editing()).toBe(false);
      expect(bookingServiceSpy.updateBooking).not.toHaveBeenCalled();
    });
  });

  // ── patchDraft ────────────────────────────────────────────────────────────────

  describe('patchDraft', () => {
    beforeEach(() => component.startEdit());

    it('actualiza el campo especificado en el draft', () => {
      component.patchDraft('guest_name', 'Nuevo Nombre');
      expect(component.draft().guest_name).toBe('Nuevo Nombre');
    });

    it('valor vacío "" guarda null en el draft', () => {
      component.patchDraft('email', '');
      expect(component.draft().email).toBeNull();
    });
  });

  // ── saveEdit ──────────────────────────────────────────────────────────────────

  describe('saveEdit — happy path', () => {
    beforeEach(() => component.startEdit());

    it('llama a updateBooking con record_id y el draft actual', () => {
      component.saveEdit();
      expect(bookingServiceSpy.updateBooking).toHaveBeenCalledWith(1, component.draft());
    });

    it('emite saved con la reserva actualizada', () => {
      const emitted: Booking[] = [];
      component.saved.subscribe(b => emitted.push(b));

      component.saveEdit();

      expect(emitted.length).toBe(1);
      expect(emitted[0].guest_name).toBe('Updated');
    });

    it('tras guardar, editing y saving quedan en false', () => {
      component.saveEdit();
      expect(component.editing()).toBe(false);
      expect(component.saving()).toBe(false);
    });
  });

  describe('saveEdit — error', () => {
    beforeEach(() => {
      component.startEdit();
      bookingServiceSpy.updateBooking.mockReturnValue(throwError(() => new Error('network')));
    });

    it('en caso de error, saving vuelve a false', () => {
      component.saveEdit();
      expect(component.saving()).toBe(false);
    });

    it('en caso de error, editing permanece true', () => {
      component.saveEdit();
      expect(component.editing()).toBe(true);
    });

    it('en caso de error, no emite saved', () => {
      const emitted: Booking[] = [];
      component.saved.subscribe(b => emitted.push(b));
      component.saveEdit();
      expect(emitted.length).toBe(0);
    });
  });

  describe('saveEdit — guard de doble envío', () => {
    it('si saving=true no llama al servicio de nuevo', () => {
      component.startEdit();
      component.saving.set(true);
      component.saveEdit();
      expect(bookingServiceSpy.updateBooking).not.toHaveBeenCalled();
    });
  });

  // ── DOM — vista de detalle ────────────────────────────────────────────────────

  describe('DOM — vista de detalle', () => {
    it('muestra .modal-body y botón "Editar reserva" cuando no está en modo edición', () => {
      expect(component.editing()).toBe(false);
      const editBtn = fixture.nativeElement.querySelector('.edit-btn');
      expect(editBtn).toBeTruthy();
      expect(editBtn.textContent).toContain('Editar reserva');
    });

    it('con children=0 no renderiza el chip de niños', () => {
      fixture.componentRef.setInput('booking', makeBooking({ children: 0 }));
      fixture.detectChanges();
      const text = fixture.nativeElement.textContent as string;
      expect(text).not.toContain('niño');
    });

    it('con children=2 renderiza "2 niños"', () => {
      fixture.componentRef.setInput('booking', makeBooking({ children: 2 }));
      fixture.detectChanges();
      expect(fixture.nativeElement.textContent).toContain('2 niños');
    });

    it('email presente → renderiza enlace mailto', () => {
      const link: HTMLAnchorElement = fixture.nativeElement.querySelector('[href^="mailto:"]');
      expect(link).toBeTruthy();
      expect(link.href).toContain('ana@test.com');
    });

    it('sin email ni teléfono → muestra "Sin datos de contacto"', () => {
      fixture.componentRef.setInput('booking', makeBooking({ email: null, phone: null }));
      fixture.detectChanges();
      expect(fixture.nativeElement.textContent).toContain('Sin datos de contacto');
    });
  });

  // ── DOM — backdrop ────────────────────────────────────────────────────────────

  describe('DOM — backdrop', () => {
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

    it('click en el botón × emite close', () => {
      const spy = jest.fn();
      component.close.subscribe(spy);

      fixture.nativeElement.querySelector('.close-btn').click();

      expect(spy).toHaveBeenCalledTimes(1);
    });
  });
});
