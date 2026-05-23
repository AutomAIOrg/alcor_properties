import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { WeekRowComponent } from './week-row.component';
import { CalendarLayoutService } from '../../../../services/calendar-layout.service';
import { CalendarWeek, WeekBar } from '../../../../models/calendar.model';
import { Booking } from '../../../../models/booking.model';
import { BookingBarComponent } from '../booking-bar/booking-bar.component';

// ─── Stub de BookingBarComponent ───────────────────────────────────────────────

@Component({
  selector: 'app-booking-bar',
  standalone: true,
  template: '<div class="stub-bar" (click)="barClick.emit(bar.booking)"></div>',
})
class StubBookingBarComponent {
  @Input() bar!: WeekBar;
  @Output() barClick = new EventEmitter<Booking>();
}

// ─── Fixture helpers ───────────────────────────────────────────────────────────

function makeBooking(overrides: Partial<Booking> = {}): Booking {
  return {
    record_id: 1,
    booking_id: 'R180',
    guest_name: 'Ana García',
    check_in: '2025-06-02',
    check_out: '2025-06-06',
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

function makeWeek(overrides: Partial<CalendarWeek> = {}): CalendarWeek {
  const base = new Date(2025, 5, 2); // Lun 2-jun-2025
  return {
    days: Array.from({ length: 7 }, (_, i) => ({
      date: new Date(base.getFullYear(), base.getMonth(), base.getDate() + i),
      currentMonth: i < 6, // último día es de otro mes para probar other-month
      isToday: i === 0, // el lunes es "hoy" en el fixture
    })),
    bars: [],
    totalLanes: 0,
    ...overrides,
  };
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('WeekRowComponent', () => {
  let fixture: ComponentFixture<WeekRowComponent>;
  let component: WeekRowComponent;
  let layout: CalendarLayoutService;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [WeekRowComponent, StubBookingBarComponent],
    })
      .overrideComponent(WeekRowComponent, {
        remove: { imports: [BookingBarComponent] },
        add: { imports: [StubBookingBarComponent] },
      })
      .compileComponents();

    layout = TestBed.inject(CalendarLayoutService);
    fixture = TestBed.createComponent(WeekRowComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('week', makeWeek());
    fixture.detectChanges();
  });

  // ── weekHeight ────────────────────────────────────────────────────────────────

  describe('weekHeight', () => {
    it('delega en layout.weekHeight con totalLanes=0', () => {
      fixture.componentRef.setInput('week', makeWeek({ totalLanes: 0 }));
      fixture.detectChanges();
      expect(component.weekHeight).toBe(layout.weekHeight(0));
    });

    it('delega en layout.weekHeight con totalLanes=3', () => {
      fixture.componentRef.setInput('week', makeWeek({ totalLanes: 3 }));
      fixture.detectChanges();
      expect(component.weekHeight).toBe(layout.weekHeight(3));
    });
  });

  // ── DOM: grid de días ─────────────────────────────────────────────────────────

  describe('DOM — grid de días', () => {
    it('renderiza exactamente 7 celdas .day-cell', () => {
      const cells = fixture.nativeElement.querySelectorAll('.day-cell');
      expect(cells.length).toBe(7);
    });

    it('el día con isToday=true lleva clase .today', () => {
      const cells: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll('.day-cell'));
      const todayCells = cells.filter(c => c.classList.contains('today'));
      expect(todayCells.length).toBe(1);
    });

    it('el día con currentMonth=false lleva clase .other-month', () => {
      const cells: HTMLElement[] = Array.from(fixture.nativeElement.querySelectorAll('.day-cell'));
      const otherMonth = cells.filter(c => c.classList.contains('other-month'));
      expect(otherMonth.length).toBe(1); // solo el último en el fixture
    });

    it('.day-number muestra el número del día correcto', () => {
      const numbers: HTMLElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('.day-number')
      );
      expect(numbers[0].textContent?.trim()).toBe('2'); // lunes 2 de junio
    });
  });

  // ── DOM: barras ───────────────────────────────────────────────────────────────

  describe('DOM — barras', () => {
    it('sin barras el overlay está vacío', () => {
      const bars = fixture.nativeElement.querySelectorAll('app-booking-bar');
      expect(bars.length).toBe(0);
    });

    it('con 2 barras renderiza 2 app-booking-bar', () => {
      const week = makeWeek({
        bars: [
          makeBar({ booking: makeBooking({ record_id: 1 }) }),
          makeBar({ booking: makeBooking({ record_id: 2 }), laneIndex: 1 }),
        ],
        totalLanes: 2,
      });
      fixture.componentRef.setInput('week', week);
      fixture.detectChanges();

      const bars = fixture.nativeElement.querySelectorAll('app-booking-bar');
      expect(bars.length).toBe(2);
    });
  });

  // ── Output: propagación de barClick ──────────────────────────────────────────

  describe('output barClick', () => {
    it('barClick del stub se propaga como output de WeekRowComponent', () => {
      const booking = makeBooking({ record_id: 42 });
      const week = makeWeek({ bars: [makeBar({ booking })], totalLanes: 1 });
      fixture.componentRef.setInput('week', week);
      fixture.detectChanges();

      const emitted: Booking[] = [];
      component.barClick.subscribe(b => emitted.push(b));

      // Disparar click en el stub
      fixture.nativeElement.querySelector('.stub-bar').click();

      expect(emitted.length).toBe(1);
      expect(emitted[0].record_id).toBe(42);
    });
  });
});
