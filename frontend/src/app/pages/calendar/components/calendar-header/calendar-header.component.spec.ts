import { ComponentFixture, TestBed } from '@angular/core/testing';
import { CalendarHeaderComponent } from './calendar-header.component';

describe('CalendarHeaderComponent', () => {
  let fixture: ComponentFixture<CalendarHeaderComponent>;
  let component: CalendarHeaderComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CalendarHeaderComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CalendarHeaderComponent);
    component = fixture.componentInstance;

    fixture.componentRef.setInput('month', 5); // Junio (0-based)
    fixture.componentRef.setInput('year', 2025);
    fixture.componentRef.setInput('viewMode', 'month');
    fixture.detectChanges();
  });

  // ── yearOptions ──────────────────────────────────────────────────────────────

  describe('yearOptions', () => {
    it('genera 11 años centrados en el año actual', () => {
      const opts = component.yearOptions();
      expect(opts.length).toBe(11);
      expect(opts[0]).toBe(2020);
      expect(opts[10]).toBe(2030);
    });

    it('el año de input está incluido en las opciones', () => {
      expect(component.yearOptions()).toContain(2025);
    });
  });

  // ── onMonthChange / onYearChange ─────────────────────────────────────────────

  describe('onMonthChange', () => {
    it('emite dateChange con el nuevo mes y el año actual', () => {
      const emitted: { month: number; year: number }[] = [];
      component.dateChange.subscribe(v => emitted.push(v));

      component.onMonthChange('3');

      expect(emitted.length).toBe(1);
      expect(emitted[0]).toEqual({ month: 3, year: 2025 });
    });
  });

  describe('onYearChange', () => {
    it('emite dateChange con el mes actual y el nuevo año', () => {
      const emitted: { month: number; year: number }[] = [];
      component.dateChange.subscribe(v => emitted.push(v));

      component.onYearChange('2030');

      expect(emitted.length).toBe(1);
      expect(emitted[0]).toEqual({ month: 5, year: 2030 });
    });
  });

  // ── Botones de navegación ────────────────────────────────────────────────────

  describe('botones de navegación', () => {
    it('click en ← emite prev', () => {
      const spy = jest.fn();
      component.prev.subscribe(spy);

      const btn = fixture.nativeElement.querySelector('[aria-label="Mes anterior"]');
      btn.click();

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('click en → emite next', () => {
      const spy = jest.fn();
      component.next.subscribe(spy);

      const btn = fixture.nativeElement.querySelector('[aria-label="Mes siguiente"]');
      btn.click();

      expect(spy).toHaveBeenCalledTimes(1);
    });

    it('click en "Hoy" emite today', () => {
      const spy = jest.fn();
      component.today.subscribe(spy);

      const btn = fixture.nativeElement.querySelector('.today-btn');
      btn.click();

      expect(spy).toHaveBeenCalledTimes(1);
    });
  });

  // ── Toggle de vista ──────────────────────────────────────────────────────────

  describe('toggle de vista', () => {
    it('click en "Mes" emite viewModeChange con "month"', () => {
      const emitted: string[] = [];
      component.viewModeChange.subscribe(v => emitted.push(v));

      const btns = fixture.nativeElement.querySelectorAll('.desktop-view-toggle button');
      btns[0].click(); // Mes

      expect(emitted).toEqual(['month']);
    });

    it('click en "Semana" emite viewModeChange con "week"', () => {
      const emitted: string[] = [];
      component.viewModeChange.subscribe(v => emitted.push(v));

      const btns = fixture.nativeElement.querySelectorAll('.desktop-view-toggle button');
      btns[1].click(); // Semana

      expect(emitted).toEqual(['week']);
    });
  });

  // ── DOM ──────────────────────────────────────────────────────────────────────

  describe('DOM', () => {
    it('el botón "Mes" tiene clase .active en viewMode="month"', () => {
      const btns = fixture.nativeElement.querySelectorAll('.desktop-view-toggle button');
      expect(btns[0].classList).toContain('active');
      expect(btns[1].classList).not.toContain('active');
    });

    it('el botón "Semana" tiene clase .active en viewMode="week"', () => {
      fixture.componentRef.setInput('viewMode', 'week');
      fixture.detectChanges();

      const btns = fixture.nativeElement.querySelectorAll('.desktop-view-toggle button');
      expect(btns[0].classList).not.toContain('active');
      expect(btns[1].classList).toContain('active');
    });

    it('el select de mes tiene la option correcta seleccionada', () => {
      const options: HTMLOptionElement[] = Array.from(
        fixture.nativeElement.querySelectorAll('.date-selects select:first-of-type option')
      );
      const selected = options.find(o => o.selected);
      // month=5 → "Junio" → index 5
      expect(options.indexOf(selected!)).toBe(5);
    });
  });
});
