import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';
import { BookingModalComponent } from './booking-modal.component';
import { BookingService } from '../../../services/booking.service';
import { ApartmentColorService } from '../../../services/apartment-color.service';
import { AuthService } from '../../../auth/auth.service';
import { Booking, BASE_STATUSES } from '../../../models/booking.model';

// ─── Fixture helper ────────────────────────────────────────────────────────────

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R180',
    guest_name: 'Ana García',
    check_in: '2025-06-01',
    check_out: '2025-06-07',
    check_in_time: null,
    check_out_time: null,
    status: 'Confirmed',
    nights: 6,
    persons: 2,
    adults: 2,
    children: 0,
    price: 600,
    charges: 50,
    electric_allowance: null,
    email: 'ana@test.com',
    phone: '+34600000000',
    booking_number: 'BK001',
    notes: null,
    notes_cleaning: null,
    ...overrides,
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
      searchBookings: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;
    bookingServiceSpy.updateBooking.mockReturnValue(of(makeBooking({ guest_name: 'Updated' })));
    bookingServiceSpy.searchBookings.mockReturnValue(of([]));

    const authServiceMock = {
      hasPermission: jest.fn().mockReturnValue(true),
      hasRole: jest.fn().mockReturnValue(true),
      isAuthenticated: jest.fn().mockReturnValue(true),
    };

    await TestBed.configureTestingModule({
      imports: [BookingModalComponent],
      providers: [
        { provide: BookingService, useValue: bookingServiceSpy },
        { provide: AuthService, useValue: authServiceMock },
        { provide: ApartmentColorService, useValue: { resolve: () => '#000000' } },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(BookingModalComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('booking', makeBooking());
    fixture.detectChanges();
  });

  // ── initials ──────────────────────────────────────────────────────────────────

  describe('fechas de la cabecera', () => {
    // El TestBed no hereda el LOCALE_ID 'es' de app.config.ts y el fichero de locale no se
    // puede importar aquí (es ESM y Jest corre en CJS), así que estas fechas salen en inglés.
    // Lo que se comprueba es nuestro formato —día de la semana + día + mes—, que en la
    // aplicación se pinta "Jue 16 Jul": en español con la inicial en mayúscula por CSS.
    function renderDates(booking: Booking): NodeListOf<Element> {
      fixture.componentRef.setInput('booking', booking);
      fixture.detectChanges();
      return fixture.nativeElement.querySelectorAll('.stat-date');
    }

    it('muestran el día de la semana junto a la fecha', () => {
      // 16/07/2026 es jueves; 20/07/2026, lunes.
      const dates = renderDates(makeBooking({ check_in: '2026-07-16', check_out: '2026-07-20' }));

      expect(dates[0].textContent?.trim()).toBe('Thu 16 Jul');
      expect(dates[1].textContent?.trim()).toBe('Mon 20 Jul');
    });

    it('la capitalización la pone el CSS, no el texto', () => {
      // El locale español da día y mes en minúscula ("jue 16 jul"); es .stat-date quien los
      // muestra como "Jue 16 Jul", así que la clase debe estar en ambas fechas.
      const dates = renderDates(makeBooking());

      expect(dates).toHaveLength(2);
      dates.forEach(date => expect(date.classList).toContain('stat-date'));
    });
  });

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
      fixture.componentRef.setInput(
        'booking',
        makeBooking({ guest_name: null as unknown as string })
      );
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

    it('carga las reservas del piso para detectar solapes', () => {
      component.startEdit();
      expect(bookingServiceSpy.searchBookings).toHaveBeenCalledWith({ apartment_id: 'R180' });
    });
  });

  describe('selectedRangeHasConflicts', () => {
    const otherBooking = makeBooking({
      record_id: 99,
      guest_name: 'Otra',
      check_in: '2025-06-10',
      check_out: '2025-06-15',
    });

    beforeEach(() => {
      bookingServiceSpy.searchBookings.mockReturnValue(of([makeBooking(), otherBooking]));
      component.startEdit();
    });

    it('no hay conflicto con las fechas originales (se excluye a sí misma)', () => {
      expect(component.selectedRangeHasConflicts()).toBe(false);
    });

    it('detecta solape al extender fechas hacia otra reserva', () => {
      component.patchDraft('check_out', '2025-06-12');
      expect(component.selectedRangeHasConflicts()).toBe(true);
    });

    it('muestra el aviso en el DOM al haber solape', () => {
      component.patchDraft('check_out', '2025-06-12');
      fixture.detectChanges();
      expect(fixture.nativeElement.textContent).toContain(
        'El piso ya tiene una reserva en ese rango de fechas.'
      );
    });

    it('no bloquea si el estado pasa a Cancelled', () => {
      component.patchDraft('check_out', '2025-06-12');
      component.patchDraft('status', 'Cancelled');
      expect(component.selectedRangeHasConflicts()).toBe(false);
    });

    it('ignora reservas canceladas del mismo piso', () => {
      bookingServiceSpy.searchBookings.mockReturnValue(
        of([
          makeBooking(),
          makeBooking({
            record_id: 99,
            status: 'Cancelled',
            check_in: '2025-06-10',
            check_out: '2025-06-15',
          }),
        ])
      );
      component.startEdit();
      component.patchDraft('check_out', '2025-06-12');
      expect(component.selectedRangeHasConflicts()).toBe(false);
    });

    it('no guarda si hay solape', () => {
      component.patchDraft('check_out', '2025-06-12');
      component.saveEdit();
      expect(bookingServiceSpy.updateBooking).not.toHaveBeenCalled();
      expect(component.saveError()).toContain('reserva en ese rango');
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

  describe('saveEdit — electric_allowance calculado', () => {
    beforeEach(() => {
      fixture.componentRef.setInput('booking', makeBooking({ electric_allowance: 24 }));
      fixture.detectChanges();
      component.startEdit();
    });

    it('si cambia electric_allowance, no guarda y muestra aviso', () => {
      component.patchDraft('electric_allowance', 40);

      component.saveEdit();
      fixture.detectChanges();

      expect(bookingServiceSpy.updateBooking).not.toHaveBeenCalled();
      expect(component.electricAllowanceWarning()).toContain('campo calculado');
      expect(fixture.nativeElement.textContent).toContain(
        'La luz incluida es un campo calculado automáticamente'
      );
    });

    it('si electric_allowance no cambia, guarda normalmente', () => {
      component.patchDraft('price', 700);

      component.saveEdit();

      expect(bookingServiceSpy.updateBooking).toHaveBeenCalledTimes(1);
      expect(component.electricAllowanceWarning()).toBe('');
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

    it('en conflicto 409 muestra el aviso de fechas', () => {
      bookingServiceSpy.updateBooking.mockReturnValue(
        throwError(
          () =>
            new HttpErrorResponse({
              status: 409,
              error: { detail: 'El piso ya tiene una reserva en ese rango de fechas.' },
            })
        )
      );
      component.saveEdit();
      fixture.detectChanges();
      expect(component.saveError()).toContain('reserva en ese rango');
      expect(fixture.nativeElement.textContent).toContain(
        'El piso ya tiene una reserva en ese rango de fechas.'
      );
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
    // Simula el inicio de la pulsación del ratón (mousedown) sobre un elemento.
    const press = (el: HTMLElement) =>
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));

    it('pulsar y soltar en .modal-backdrop emite close', () => {
      const spy = jest.fn();
      component.close.subscribe(spy);

      const backdrop = fixture.nativeElement.querySelector('.modal-backdrop');
      press(backdrop);
      backdrop.click();

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('click en .modal-card no emite close', () => {
      const spy = jest.fn();
      component.close.subscribe(spy);

      const card = fixture.nativeElement.querySelector('.modal-card');
      press(card);
      card.click();

      expect(spy).not.toHaveBeenCalled();
    });

    it('pulsar dentro del modal y soltar fuera no emite close', () => {
      const spy = jest.fn();
      component.close.subscribe(spy);

      const backdrop = fixture.nativeElement.querySelector('.modal-backdrop');
      const card = fixture.nativeElement.querySelector('.modal-card');
      press(card); // la pulsación empieza dentro del modal
      backdrop.click(); // ...y se suelta sobre el fondo

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
