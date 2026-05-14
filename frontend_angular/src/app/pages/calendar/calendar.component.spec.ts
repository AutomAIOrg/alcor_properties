import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { of } from 'rxjs';

import { CalendarComponent } from './calendar.component';
import { BookingService } from '../../services/booking.service';
import { CalendarLayoutService } from '../../services/calendar-layout.service';
import { Booking } from '../../models/booking.model';
import { CalendarWeek } from '../../models/calendar.model';
import { CalendarHeaderComponent } from './components/calendar-header/calendar-header.component';
import { WeekRowComponent } from './components/week-row/week-row.component';
import { BookingModalComponent } from './components/booking-modal/booking-modal.component';
import { BookingCreateModalComponent } from './components/booking-create-modal/booking-create-modal.component';
import { BookingColorPipe } from '../../pipes/booking-color.pipe';

// ─── Stubs de componentes hijo ─────────────────────────────────────────────────
// Se usan stubs para aislar el componente padre sin montar la lógica interna
// de cada hijo. Los outputs se disparan manualmente desde los tests.

@Component({
  selector: 'app-calendar-header',
  standalone: true,
  template: '',
})
class StubCalendarHeaderComponent {
  @Input() month!: number;
  @Input() year!: number;
  @Input() viewMode!: string;
  @Output() prev           = new EventEmitter<void>();
  @Output() next           = new EventEmitter<void>();
  @Output() today          = new EventEmitter<void>();
  @Output() dateChange     = new EventEmitter<{ month: number; year: number }>();
  @Output() viewModeChange = new EventEmitter<string>();
}

@Component({
  selector: 'app-week-row',
  standalone: true,
  template: '',
})
class StubWeekRowComponent {
  @Input() week!: CalendarWeek;
  @Output() barClick = new EventEmitter<Booking>();
}

@Component({
  selector: 'app-booking-modal',
  standalone: true,
  template: '',
})
class StubBookingModalComponent {
  @Input() booking!: Booking;
  @Output() close = new EventEmitter<void>();
  @Output() saved = new EventEmitter<Booking>();
}

@Component({
  selector: 'app-booking-create-modal',
  standalone: true,
  template: '',
})
class StubBookingCreateModalComponent {
  @Input() apartments!: string[];
  @Output() close   = new EventEmitter<void>();
  @Output() created = new EventEmitter<Booking>();
}

// ─── Fixture helper ────────────────────────────────────────────────────────────

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1, booking_id: 'R180', guest_name: 'Ana García',
    check_in: '2025-06-01', check_out: '2025-06-07',
    status: 'Confirmed', nights: 6, persons: 2,
    adults: 2, children: 0, price: 600, charges: null,
    electric_allowance: null, email: null, phone: null,
    booking_number: null, notes: null,
    ...overrides
  };
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('CalendarComponent', () => {
  let fixture: ComponentFixture<CalendarComponent>;
  let component: CalendarComponent;
  let bookingServiceSpy: jest.Mocked<BookingService>;
  let layout: CalendarLayoutService;

  beforeEach(async () => {
    bookingServiceSpy = {
      getBookings: jest.fn().mockReturnValue(of([])),
      updateBooking: jest.fn(),
      createBooking: jest.fn(),
    } as unknown as jest.Mocked<BookingService>;

    await TestBed.configureTestingModule({
      imports: [CalendarComponent],
      providers: [
        { provide: BookingService, useValue: bookingServiceSpy },
        CalendarLayoutService,
      ],
    })
      .overrideComponent(CalendarComponent, {
        remove: {
          imports: [
            CalendarHeaderComponent,
            WeekRowComponent,
            BookingModalComponent,
            BookingCreateModalComponent,
            BookingColorPipe,
          ],
        },
        add: {
          imports: [
            StubCalendarHeaderComponent,
            StubWeekRowComponent,
            StubBookingModalComponent,
            StubBookingCreateModalComponent,
          ],
        },
      })
      .compileComponents();

    layout = TestBed.inject(CalendarLayoutService);
    fixture = TestBed.createComponent(CalendarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges(); // dispara ngOnInit
  });

  // ── A: Inicialización ────────────────────────────────────────────────────────

  describe('A — ngOnInit', () => {
    it('carga las reservas desde el servicio al iniciar', () => {
      expect(bookingServiceSpy.getBookings).toHaveBeenCalledTimes(1);
    });

    it('almacena las reservas recibidas en el signal bookings', () => {
      const bookings = [makeBooking({ record_id: 1 }), makeBooking({ record_id: 2 })];
      bookingServiceSpy.getBookings.mockReturnValue(of(bookings));

      fixture = TestBed.createComponent(CalendarComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();

      expect(component.bookings().length).toBe(2);
    });

    it('con lista vacía, weeks() tiene filas sin barras', () => {
      const hasBarras = component.weeks().some(w => w.bars.length > 0);
      expect(hasBarras).toBe(false);
    });
  });

  // ── B: Navegación ────────────────────────────────────────────────────────────

  describe('B — navegación', () => {
    beforeEach(() => {
      // Fijar la fecha para reproducibilidad
      component.currentDate.set(new Date(2025, 5, 15)); // 15 jun 2025
    });

    it('prevPeriod en modo month retrocede un mes', () => {
      component.viewMode.set('month');
      component.prevPeriod();
      const d = component.currentDate();
      expect(d.getFullYear()).toBe(2025);
      expect(d.getMonth()).toBe(4); // mayo
    });

    it('nextPeriod en modo month avanza un mes', () => {
      component.viewMode.set('month');
      component.nextPeriod();
      const d = component.currentDate();
      expect(d.getMonth()).toBe(6); // julio
    });

    it('prevPeriod en modo week resta 7 días', () => {
      component.viewMode.set('week');
      component.prevPeriod();
      const d = component.currentDate();
      expect(d.getDate()).toBe(8); // 15 - 7
    });

    it('nextPeriod en modo week suma 7 días', () => {
      component.viewMode.set('week');
      component.nextPeriod();
      const d = component.currentDate();
      expect(d.getDate()).toBe(22); // 15 + 7
    });

    it('goToToday establece la fecha de hoy', () => {
      component.currentDate.set(new Date(2020, 0, 1));
      component.goToToday();
      const iso = layout.toIso(component.currentDate());
      const todayIso = layout.toIso(new Date());
      expect(iso).toBe(todayIso);
    });

    it('goToDate posiciona en el mes y año indicados', () => {
      component.goToDate({ month: 3, year: 2024 });
      const d = component.currentDate();
      expect(d.getMonth()).toBe(3);
      expect(d.getFullYear()).toBe(2024);
    });

    it('prevPeriod en enero retrocede a diciembre del año anterior', () => {
      component.viewMode.set('month');
      component.currentDate.set(new Date(2025, 0, 1));
      component.prevPeriod();
      const d = component.currentDate();
      expect(d.getMonth()).toBe(11); // diciembre
      expect(d.getFullYear()).toBe(2024);
    });

    it('nextPeriod en diciembre avanza a enero del año siguiente', () => {
      component.viewMode.set('month');
      component.currentDate.set(new Date(2025, 11, 1));
      component.nextPeriod();
      const d = component.currentDate();
      expect(d.getMonth()).toBe(0); // enero
      expect(d.getFullYear()).toBe(2026);
    });
  });

  // ── C: Modo de vista ─────────────────────────────────────────────────────────

  describe('C — modo de vista', () => {
    it('estado inicial es "month"', () => {
      expect(component.viewMode()).toBe('month');
    });

    it('se puede cambiar a "week"', () => {
      component.viewMode.set('week');
      expect(component.viewMode()).toBe('week');
    });
  });

  // ── D: Filtros ───────────────────────────────────────────────────────────────

  describe('D — filtros', () => {
    const b1 = makeBooking({ record_id: 1, booking_id: 'R180', status: 'Confirmed' });
    const b2 = makeBooking({ record_id: 2, booking_id: 'R101', status: 'Pending' });
    const b3 = makeBooking({ record_id: 3, booking_id: 'R180', status: 'Cancelled' });

    beforeEach(() => {
      component.bookings.set([b1, b2, b3]);
      component.currentDate.set(new Date(2025, 5, 1)); // junio 2025, donde caen las reservas
    });

    it('bookingIdOptions devuelve IDs únicos y ordenados', () => {
      expect(component.bookingIdOptions()).toEqual(['R101', 'R180']);
    });

    it('hasActiveFilters es false sin filtros', () => {
      expect(component.hasActiveFilters()).toBe(false);
    });

    it('hasActiveFilters es true al activar un filtro de ID', () => {
      component.toggleBookingId('R180');
      expect(component.hasActiveFilters()).toBe(true);
    });

    it('hasActiveFilters es true al activar un filtro de estado', () => {
      component.toggleBookingState('Confirmed');
      expect(component.hasActiveFilters()).toBe(true);
    });

    it('toggleBookingId añade el ID a filterBookingIds', () => {
      component.toggleBookingId('R180');
      expect(component.filterBookingIds()).toContain('R180');
    });

    it('toggleBookingId elimina el ID si ya estaba seleccionado', () => {
      component.toggleBookingId('R180');
      component.toggleBookingId('R180');
      expect(component.filterBookingIds()).not.toContain('R180');
    });

    it('toggleBookingState añade el estado', () => {
      component.toggleBookingState('Pending');
      expect(component.filterBookingStates()).toContain('Pending');
    });

    it('toggleBookingState elimina el estado si ya estaba seleccionado', () => {
      component.toggleBookingState('Pending');
      component.toggleBookingState('Pending');
      expect(component.filterBookingStates()).not.toContain('Pending');
    });

    it('clearAllFilters limpia ambos arrays', () => {
      component.toggleBookingId('R180');
      component.toggleBookingState('Confirmed');
      component.clearAllFilters();
      expect(component.filterBookingIds()).toEqual([]);
      expect(component.filterBookingStates()).toEqual([]);
    });

    it('filtrado por ID: solo pasan las reservas con ese booking_id', () => {
      component.toggleBookingId('R101');
      const allBars = component.weeks().flatMap(w => w.bars);
      expect(allBars.length).toBeGreaterThan(0);
      allBars.forEach(bar => expect(bar.booking.booking_id).toBe('R101'));
    });

    it('filtrado por estado es case-insensitive', () => {
      component.filterBookingStates.set(['confirmed']); // minúsculas
      const allBars = component.weeks().flatMap(w => w.bars);
      expect(allBars.length).toBeGreaterThan(0);
      allBars.forEach(bar =>
        expect(bar.booking.status.toUpperCase()).toBe('CONFIRMED')
      );
    });

    it('filtrado combinado (AND): ID y estado deben cumplirse a la vez', () => {
      component.toggleBookingId('R180');
      component.toggleBookingState('Cancelled');
      const allBars = component.weeks().flatMap(w => w.bars);
      expect(allBars.length).toBeGreaterThan(0);
      allBars.forEach(bar => {
        expect(bar.booking.booking_id).toBe('R180');
        expect(bar.booking.status).toBe('Cancelled');
      });
    });

    it('sin filtros activos, todas las reservas son visibles en el calendario', () => {
      expect(component.hasActiveFilters()).toBe(false);
      expect(component.currentDayBookings().length).toBe(3);
    });
  });

  // ── E: Control de desplegables ────────────────────────────────────────────────

  describe('E — desplegables', () => {
    it('showIdDropdown inicia en false', () => {
      expect(component.showIdDropdown()).toBe(false);
    });

    it('openBooking cierra ambos desplegables', () => {
      component.showIdDropdown.set(true);
      component.showStateDropdown.set(true);
      component.openBooking(makeBooking());
      expect(component.showIdDropdown()).toBe(false);
      expect(component.showStateDropdown()).toBe(false);
    });
  });

  // ── F: Modales ────────────────────────────────────────────────────────────────

  describe('F — modales', () => {
    const booking = makeBooking({ record_id: 5 });

    it('openBooking asigna la reserva a selectedBooking', () => {
      component.openBooking(booking);
      expect(component.selectedBooking()?.record_id).toBe(5);
    });

    it('closeBooking pone selectedBooking a null', () => {
      component.openBooking(booking);
      component.closeBooking();
      expect(component.selectedBooking()).toBeNull();
    });

    it('onBookingSaved reemplaza la reserva correcta por record_id', () => {
      const b1 = makeBooking({ record_id: 1, guest_name: 'Original' });
      const b2 = makeBooking({ record_id: 2, guest_name: 'Otro' });
      component.bookings.set([b1, b2]);
      component.selectedBooking.set(b1);

      const updated = makeBooking({ record_id: 1, guest_name: 'Actualizado' });
      component.onBookingSaved(updated);

      expect(component.bookings().find(b => b.record_id === 1)?.guest_name).toBe('Actualizado');
      expect(component.bookings().find(b => b.record_id === 2)?.guest_name).toBe('Otro');
      expect(component.selectedBooking()?.guest_name).toBe('Actualizado');
    });

    it('onBookingSaved con record_id inexistente no muta la lista', () => {
      component.bookings.set([makeBooking({ record_id: 1 })]);
      component.onBookingSaved(makeBooking({ record_id: 999 }));
      expect(component.bookings().length).toBe(1);
    });

    it('onBookingCreated añade la reserva y cierra el modal de creación', () => {
      component.showCreateModal.set(true);
      component.bookings.set([makeBooking({ record_id: 1 })]);
      component.onBookingCreated(makeBooking({ record_id: 2 }));
      expect(component.bookings().length).toBe(2);
      expect(component.showCreateModal()).toBe(false);
    });

    it('el output close del stub booking-modal cierra selectedBooking', () => {
      component.openBooking(makeBooking());
      fixture.detectChanges();

      const modalEl = fixture.debugElement.query(
        el => el.nativeElement.tagName === 'APP-BOOKING-MODAL'
      );
      (modalEl?.componentInstance as StubBookingModalComponent).close.emit();

      expect(component.selectedBooking()).toBeNull();
    });

    it('el output saved del stub booking-modal llama a onBookingSaved', () => {
      const b = makeBooking({ record_id: 1, guest_name: 'Original' });
      component.bookings.set([b]);
      component.openBooking(b);
      fixture.detectChanges();

      const modalEl = fixture.debugElement.query(
        el => el.nativeElement.tagName === 'APP-BOOKING-MODAL'
      );
      (modalEl?.componentInstance as StubBookingModalComponent).saved.emit(
        makeBooking({ record_id: 1, guest_name: 'Actualizado por output' })
      );

      expect(component.bookings().find(x => x.record_id === 1)?.guest_name).toBe('Actualizado por output');
    });

    it('el output close del stub create-modal pone showCreateModal a false', () => {
      component.showCreateModal.set(true);
      fixture.detectChanges();

      const createEl = fixture.debugElement.query(
        el => el.nativeElement.tagName === 'APP-BOOKING-CREATE-MODAL'
      );
      (createEl?.componentInstance as StubBookingCreateModalComponent).close.emit();

      expect(component.showCreateModal()).toBe(false);
    });
  });

  // ── G: Utilidades ─────────────────────────────────────────────────────────────

  describe('G — formatHour / isToday', () => {
    it('formatHour(0) → "00:00"', () => {
      expect(component.formatHour(0)).toBe('00:00');
    });

    it('formatHour(9) → "09:00"', () => {
      expect(component.formatHour(9)).toBe('09:00');
    });

    it('formatHour(23) → "23:00"', () => {
      expect(component.formatHour(23)).toBe('23:00');
    });

    it('isToday devuelve true para la fecha de hoy', () => {
      expect(component.isToday(new Date())).toBe(true);
    });

    it('isToday devuelve false para una fecha pasada', () => {
      expect(component.isToday(new Date(2000, 0, 1))).toBe(false);
    });
  });

  // ── H: DOM ───────────────────────────────────────────────────────────────────

  describe('H — integración con el DOM', () => {
    it('renderiza 7 celdas .weekday-header en vista month', () => {
      component.viewMode.set('month');
      fixture.detectChanges();
      const headers = fixture.nativeElement.querySelectorAll('.weekday-header');
      expect(headers.length).toBe(7);
    });

    it('el botón "Mes" tiene clase .active en viewMode="month"', () => {
      component.viewMode.set('month');
      fixture.detectChanges();
      const btns: HTMLButtonElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('.view-toggle button')
      );
      const mesBtn = btns.find(b => b.textContent?.trim() === 'Mes');
      expect(mesBtn?.classList).toContain('active');
    });

    it('el botón "Semana" tiene clase .active en viewMode="week"', () => {
      component.viewMode.set('week');
      fixture.detectChanges();
      const btns: HTMLButtonElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('.view-toggle button')
      );
      const semanaBtn = btns.find(b => b.textContent?.trim() === 'Semana');
      expect(semanaBtn?.classList).toContain('active');
    });

    it('.clear-filter no se renderiza cuando no hay filtros activos', () => {
      expect(fixture.nativeElement.querySelector('.clear-filter')).toBeNull();
    });

    it('.clear-filter aparece cuando hay un filtro activo', () => {
      component.bookings.set([makeBooking()]);
      component.toggleBookingId('R180');
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('.clear-filter')).toBeTruthy();
    });

    it('app-booking-modal no se renderiza sin selectedBooking', () => {
      expect(fixture.nativeElement.querySelector('app-booking-modal')).toBeNull();
    });

    it('app-booking-modal se renderiza cuando hay selectedBooking', () => {
      component.openBooking(makeBooking());
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('app-booking-modal')).toBeTruthy();
    });

    it('app-booking-create-modal no se renderiza con showCreateModal=false', () => {
      expect(fixture.nativeElement.querySelector('app-booking-create-modal')).toBeNull();
    });

    it('app-booking-create-modal se renderiza con showCreateModal=true', () => {
      component.showCreateModal.set(true);
      fixture.detectChanges();
      expect(fixture.nativeElement.querySelector('app-booking-create-modal')).toBeTruthy();
    });

    it('click en "Nueva reserva" pone showCreateModal a true', () => {
      fixture.nativeElement.querySelector('.btn-new-booking').click();
      expect(component.showCreateModal()).toBe(true);
    });

    it('barClick de app-week-row llama a openBooking', () => {
      const rows = fixture.debugElement.queryAll(
        el => el.nativeElement.tagName === 'APP-WEEK-ROW'
      );
      const booking = makeBooking({ record_id: 77 });
      (rows[0].componentInstance as StubWeekRowComponent).barClick.emit(booking);

      expect(component.selectedBooking()?.record_id).toBe(77);
    });

    it('el header recibe month y year correctos según currentDate', () => {
      component.currentDate.set(new Date(2025, 5, 1)); // Junio 2025
      fixture.detectChanges();
      const header = fixture.debugElement.query(
        el => el.nativeElement.tagName === 'APP-CALENDAR-HEADER'
      );
      const headerComp = header?.componentInstance as StubCalendarHeaderComponent;
      expect(headerComp?.month).toBe(5);
      expect(headerComp?.year).toBe(2025);
    });
  });

  // ── EC: Edge cases ────────────────────────────────────────────────────────────

  describe('EC — edge cases', () => {
    it('currentWeek cae en la semana correcta de currentDate', () => {
      component.bookings.set([]);
      component.currentDate.set(new Date(2025, 5, 11)); // miércoles 11 jun
      const week = component.currentWeek();
      const isos = week.days.map(d => layout.toIso(d.date));
      expect(isos).toContain('2025-06-11');
    });

    it('onDocumentClick fuera de .filter-dropdown cierra ambos desplegables', () => {
      component.showIdDropdown.set(true);
      component.showStateDropdown.set(true);

      // click() en un nodo del DOM real: event.target es el elemento,
      // burbujea hasta document donde está el @HostListener.
      // .calendar-actions está fuera de cualquier .filter-dropdown.
      fixture.nativeElement.querySelector('.calendar-actions').click();

      expect(component.showIdDropdown()).toBe(false);
      expect(component.showStateDropdown()).toBe(false);
    });
  });

  // ── I: currentDayBookings ─────────────────────────────────────────────────────

  describe('I — currentDayBookings', () => {
    it('devuelve reservas activas en la fecha actual', () => {
      const booking = makeBooking({ check_in: '2025-06-01', check_out: '2025-06-07' });
      component.bookings.set([booking]);
      component.currentDate.set(new Date(2025, 5, 3));
      expect(component.currentDayBookings().length).toBe(1);
    });

    it('excluye reservas fuera del rango de currentDate', () => {
      const booking = makeBooking({ check_in: '2025-06-10', check_out: '2025-06-15' });
      component.bookings.set([booking]);
      component.currentDate.set(new Date(2025, 5, 3));
      expect(component.currentDayBookings().length).toBe(0);
    });

    it('respeta los filtros activos', () => {
      const b1 = makeBooking({ record_id: 1, booking_id: 'R180', check_in: '2025-06-01', check_out: '2025-06-07' });
      const b2 = makeBooking({ record_id: 2, booking_id: 'R101', check_in: '2025-06-01', check_out: '2025-06-07' });
      component.bookings.set([b1, b2]);
      component.currentDate.set(new Date(2025, 5, 3));
      component.toggleBookingId('R180');
      expect(component.currentDayBookings().length).toBe(1);
      expect(component.currentDayBookings()[0].booking_id).toBe('R180');
    });
  });
});
