import { CalendarLayoutService } from './calendar-layout.service';
import { Booking } from '../models/booking.model';

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

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('CalendarLayoutService', () => {
  let svc: CalendarLayoutService;

  beforeEach(() => {
    svc = new CalendarLayoutService();
  });

  // ── toIso ────────────────────────────────────────────────────────────────────

  describe('toIso', () => {
    it('formatea una fecha normal como YYYY-MM-DD', () => {
      expect(svc.toIso(new Date(2025, 5, 15))).toBe('2025-06-15');
    });

    it('añade padding de cero en mes y día de un dígito', () => {
      expect(svc.toIso(new Date(2025, 0, 5))).toBe('2025-01-05');
    });

    it('maneja el 31 de diciembre correctamente', () => {
      expect(svc.toIso(new Date(2024, 11, 31))).toBe('2024-12-31');
    });
  });

  // ── weekHeight ───────────────────────────────────────────────────────────────

  describe('weekHeight', () => {
    it('con 0 carriles devuelve la altura base', () => {
      const expected = svc.DAY_HEADER_H + svc.BAR_TOP_PAD + 0 + 8;
      expect(svc.weekHeight(0)).toBe(expected);
    });

    it('con 1 carril incluye el espacio de una barra', () => {
      const expected = svc.DAY_HEADER_H + svc.BAR_TOP_PAD + 1 * (svc.BAR_HEIGHT + svc.BAR_GAP) + 8;
      expect(svc.weekHeight(1)).toBe(expected);
    });

    it('con N carriles escala linealmente', () => {
      const n = 4;
      const expected = svc.DAY_HEADER_H + svc.BAR_TOP_PAD + n * (svc.BAR_HEIGHT + svc.BAR_GAP) + 8;
      expect(svc.weekHeight(n)).toBe(expected);
    });
  });

  // ── barTop ───────────────────────────────────────────────────────────────────

  describe('barTop', () => {
    it('lane 0 devuelve DAY_HEADER_H + BAR_TOP_PAD', () => {
      expect(svc.barTop(0)).toBe(svc.DAY_HEADER_H + svc.BAR_TOP_PAD);
    });

    it('lane 2 desplaza el valor dos veces (BAR_HEIGHT + BAR_GAP)', () => {
      const expected = svc.DAY_HEADER_H + svc.BAR_TOP_PAD + 2 * (svc.BAR_HEIGHT + svc.BAR_GAP);
      expect(svc.barTop(2)).toBe(expected);
    });
  });

  // ── buildLaneAssignment ──────────────────────────────────────────────────────

  describe('buildLaneAssignment', () => {
    it('lista vacía devuelve un Map vacío', () => {
      expect(svc.buildLaneAssignment([]).size).toBe(0);
    });

    it('dos reservas sin solapamiento comparten el carril 0', () => {
      const b1 = makeBooking({ record_id: 1, check_in: '2025-06-01', check_out: '2025-06-07' });
      const b2 = makeBooking({ record_id: 2, check_in: '2025-06-10', check_out: '2025-06-15' });
      const map = svc.buildLaneAssignment([b1, b2]);
      expect(map.get(1)).toBe(0);
      expect(map.get(2)).toBe(0);
    });

    it('dos reservas solapadas reciben carriles distintos', () => {
      const b1 = makeBooking({ record_id: 1, check_in: '2025-06-01', check_out: '2025-06-10' });
      const b2 = makeBooking({ record_id: 2, check_in: '2025-06-05', check_out: '2025-06-15' });
      const map = svc.buildLaneAssignment([b1, b2]);
      expect(map.get(1)).toBe(0);
      expect(map.get(2)).toBe(1);
    });

    it('tres reservas con solapamiento parcial aplica greedy correctamente', () => {
      const b1 = makeBooking({ record_id: 1, check_in: '2025-06-01', check_out: '2025-06-05' });
      const b2 = makeBooking({ record_id: 2, check_in: '2025-06-03', check_out: '2025-06-10' });
      const b3 = makeBooking({ record_id: 3, check_in: '2025-06-06', check_out: '2025-06-12' });
      const map = svc.buildLaneAssignment([b1, b2, b3]);
      // b1 → lane 0, b2 → lane 1 (solapa b1), b3 → lane 0 (b1 ya terminó)
      expect(map.get(1)).toBe(0);
      expect(map.get(2)).toBe(1);
      expect(map.get(3)).toBe(0);
    });

    it('checkout y checkin el mismo día comparten carril (≤ en la comparación)', () => {
      const b1 = makeBooking({ record_id: 1, check_in: '2025-06-01', check_out: '2025-06-07' });
      const b2 = makeBooking({ record_id: 2, check_in: '2025-06-07', check_out: '2025-06-14' });
      const map = svc.buildLaneAssignment([b1, b2]);
      // check_out de b1 === check_in de b2 → end '2025-06-07' <= '2025-06-07' → mismo carril
      expect(map.get(1)).toBe(0);
      expect(map.get(2)).toBe(0);
    });
  });

  // ── buildWeeks ───────────────────────────────────────────────────────────────

  describe('buildWeeks', () => {
    const TODAY = '2025-06-15';

    it('enero 2025 produce 5 semanas con 35 días', () => {
      const weeks = svc.buildWeeks(2025, 0, [], TODAY, new Map());
      expect(weeks.length).toBe(5);
      const totalDays = weeks.reduce((acc, w) => acc + w.days.length, 0);
      expect(totalDays).toBe(35);
    });

    it('los días del mes correcto tienen currentMonth=true', () => {
      const weeks = svc.buildWeeks(2025, 5, [], TODAY, new Map()); // Junio
      const all = weeks.flatMap(w => w.days);
      const junioDays = all.filter(d => d.currentMonth);
      expect(junioDays.length).toBe(30);
    });

    it('el día de hoy tiene isToday=true', () => {
      const weeks = svc.buildWeeks(2025, 5, [], '2025-06-15', new Map());
      const all = weeks.flatMap(w => w.days);
      const today = all.find(d => d.isToday);
      expect(today).toBeTruthy();
      expect(svc.toIso(today!.date)).toBe('2025-06-15');
    });

    it('una reserva multi-semana aparece en barras de dos semanas distintas', () => {
      const booking = makeBooking({
        record_id: 1,
        check_in: '2025-06-07',
        check_out: '2025-06-14',
      });
      const assignment = svc.buildLaneAssignment([booking]);
      const weeks = svc.buildWeeks(2025, 5, [booking], TODAY, assignment);
      const weeksWithBars = weeks.filter(w => w.bars.length > 0);
      expect(weeksWithBars.length).toBeGreaterThanOrEqual(2);
    });

    it('una reserva fuera del mes no genera barras', () => {
      const booking = makeBooking({
        record_id: 1,
        check_in: '2025-08-01',
        check_out: '2025-08-10',
      });
      const assignment = svc.buildLaneAssignment([booking]);
      const weeks = svc.buildWeeks(2025, 5, [booking], TODAY, assignment); // Junio
      const weeksWithBars = weeks.filter(w => w.bars.length > 0);
      expect(weeksWithBars.length).toBe(0);
    });

    it('febrero en año bisiesto (2024) produce 5 semanas', () => {
      const weeks = svc.buildWeeks(2024, 1, [], TODAY, new Map());
      const allDays = weeks.flatMap(w => w.days);
      const febDays = allDays.filter(d => d.currentMonth);
      expect(febDays.length).toBe(29);
    });

    it('totalLanes refleja el número de carriles activos en la semana', () => {
      const b1 = makeBooking({ record_id: 1, check_in: '2025-06-02', check_out: '2025-06-06' });
      const b2 = makeBooking({
        record_id: 2,
        apartment_id: 'R101',
        check_in: '2025-06-03',
        check_out: '2025-06-05',
      });
      const assignment = svc.buildLaneAssignment([b1, b2]);
      const weeks = svc.buildWeeks(2025, 5, [b1, b2], TODAY, assignment);
      // Primera semana de junio (lun 02 - dom 08): ambas reservas solapan → 2 carriles
      const firstWeek = weeks.find(w =>
        w.bars.some(bar => bar.booking.record_id === 1 || bar.booking.record_id === 2)
      );
      expect(firstWeek?.totalLanes).toBe(2);
    });
  });
});
