import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BookingBarComponent } from './booking-bar.component';
import { CalendarLayoutService } from '../../../../services/calendar-layout.service';
import { WeekBar } from '../../../../models/calendar.model';
import { Booking } from '../../../../models/booking.model';

// ─── Fixture helpers ───────────────────────────────────────────────────────────

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    apartment_id: 'R180',
    guest_name: 'Ana García',
    check_in: '2025-06-01',
    check_out: '2025-06-07',
    status: 'Confirmed',
    nights: 6,
    persons: 2,
    adults: 2,
    children: 0,
    price: 600,
    charges: null,
    electric_allowance: null,
    email: null,
    phone: null,
    booking_number: null,
    notes: null,
    ...overrides,
  };
}

function makeBar(overrides: Partial<WeekBar> = {}): WeekBar {
  return {
    booking: makeBooking(),
    laneIndex: 0,
    leftPct: 10,
    widthPct: 50,
    isCheckin: true,
    isCheckout: false,
    background: 'hsl(200, 65%, 42%)',
    ...overrides,
  };
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('BookingBarComponent', () => {
  let fixture: ComponentFixture<BookingBarComponent>;
  let component: BookingBarComponent;
  let layout: CalendarLayoutService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [BookingBarComponent],
      providers: [CalendarLayoutService],
    }).compileComponents();

    layout = TestBed.inject(CalendarLayoutService);
    fixture = TestBed.createComponent(BookingBarComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('bar', makeBar());
    fixture.detectChanges();
  });

  // ── Getters de layout ────────────────────────────────────────────────────────

  describe('getters de layout', () => {
    it('height devuelve BAR_HEIGHT del servicio (22)', () => {
      expect(component.height).toBe(layout.BAR_HEIGHT);
    });

    it('top con laneIndex=0 devuelve barTop(0)', () => {
      fixture.componentRef.setInput('bar', makeBar({ laneIndex: 0 }));
      fixture.detectChanges();
      expect(component.top).toBe(layout.barTop(0));
    });

    it('top con laneIndex=2 devuelve barTop(2)', () => {
      fixture.componentRef.setInput('bar', makeBar({ laneIndex: 2 }));
      fixture.detectChanges();
      expect(component.top).toBe(layout.barTop(2));
    });
  });

  // ── Clases CSS condicionales ─────────────────────────────────────────────────

  describe('clases CSS', () => {
    it('aplica las clases de borde según isCheckin/isCheckout', () => {
      fixture.componentRef.setInput('bar', makeBar({ isCheckin: true, isCheckout: true }));
      fixture.detectChanges();
      let el: HTMLElement = fixture.nativeElement.querySelector('.booking-bar');

      expect(el.classList).toContain('bar-round-left');
      expect(el.classList).toContain('bar-round-right');

      fixture.componentRef.setInput('bar', makeBar({ isCheckin: false, isCheckout: false }));
      fixture.detectChanges();
      el = fixture.nativeElement.querySelector('.booking-bar');
      expect(el.classList).not.toContain('bar-round-left');
      expect(el.classList).not.toContain('bar-round-right');
    });

    it('aplica .bar-cancelled solo cuando status="Cancelled"', () => {
      fixture.componentRef.setInput(
        'bar',
        makeBar({ booking: makeBooking({ status: 'Cancelled' }) })
      );
      fixture.detectChanges();
      let el: HTMLElement = fixture.nativeElement.querySelector('.booking-bar');
      expect(el.classList).toContain('bar-cancelled');

      fixture.componentRef.setInput(
        'bar',
        makeBar({ booking: makeBooking({ status: 'Confirmed' }) })
      );
      fixture.detectChanges();
      el = fixture.nativeElement.querySelector('.booking-bar');
      expect(el.classList).not.toContain('bar-cancelled');
    });
  });

  // ── Background ───────────────────────────────────────────────────────────────

  describe('background', () => {
    it('status="Cancelled" deja background en null (se gestiona por CSS)', () => {
      const bar = makeBar({
        booking: makeBooking({ status: 'Cancelled' }),
        background: 'hsl(200, 65%, 42%)',
      });
      fixture.componentRef.setInput('bar', bar);
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement.querySelector('.booking-bar');
      // La directiva [style.background]="null" elimina el estilo inline
      expect(el.style.background).toBeFalsy();
    });

    it('status confirmado aplica bar.background como estilo inline', () => {
      const bg = 'hsl(120, 65%, 42%)';
      fixture.componentRef.setInput('bar', makeBar({ background: bg }));
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement.querySelector('.booking-bar');
      expect(el.style.background).toBeTruthy();
    });
  });

  // ── Posicionamiento ──────────────────────────────────────────────────────────

  describe('posicionamiento inline', () => {
    it('aplica left% desde bar.leftPct', () => {
      fixture.componentRef.setInput('bar', makeBar({ leftPct: 14.28 }));
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement.querySelector('.booking-bar');
      expect(el.style.left).toContain('%');
    });

    it('aplica width% desde bar.widthPct', () => {
      fixture.componentRef.setInput('bar', makeBar({ widthPct: 42.85 }));
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement.querySelector('.booking-bar');
      expect(el.style.width).toContain('%');
    });
  });

  // ── Atributo title ───────────────────────────────────────────────────────────

  describe('title', () => {
    it('muestra "apartment_id — guest_name"', () => {
      const booking = makeBooking({ apartment_id: 'R180', guest_name: 'Juan García' });
      fixture.componentRef.setInput('bar', makeBar({ booking }));
      fixture.detectChanges();
      const el: HTMLElement = fixture.nativeElement.querySelector('.booking-bar');
      expect(el.getAttribute('title')).toBe('R180 — Juan García');
    });
  });

  // ── Output barClick ──────────────────────────────────────────────────────────

  describe('output barClick', () => {
    it('click en la barra emite bar.booking', () => {
      const booking = makeBooking({ record_id: 99 });
      fixture.componentRef.setInput('bar', makeBar({ booking }));
      fixture.detectChanges();

      const emitted: Booking[] = [];
      component.barClick.subscribe(b => emitted.push(b));

      fixture.nativeElement.querySelector('.booking-bar').click();

      expect(emitted.length).toBe(1);
      expect(emitted[0].record_id).toBe(99);
    });
  });
});
