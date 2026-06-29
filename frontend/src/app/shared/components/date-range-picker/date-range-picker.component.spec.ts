import { ComponentFixture, TestBed } from '@angular/core/testing';
import { DateRangePickerComponent, type DateRangeValue } from './date-range-picker.component';

describe('DateRangePickerComponent', () => {
  let fixture: ComponentFixture<DateRangePickerComponent>;
  let component: DateRangePickerComponent;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [DateRangePickerComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(DateRangePickerComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('muestra placeholders cuando no hay fechas', () => {
    const text = fixture.nativeElement.textContent as string;

    expect(text).toContain('Seleccionar entrada');
    expect(text).toContain('Seleccionar salida');
  });

  it('seleccionar primera fecha emite from y deja to vacío', () => {
    const emitted: DateRangeValue[] = [];
    component.rangeChange.subscribe(value => emitted.push(value));

    component.selectDate('2026-06-10');

    expect(emitted).toEqual([{ from: '2026-06-10', to: '' }]);
  });

  it('seleccionar fecha final posterior emite rango completo y rangeComplete', () => {
    const changes: DateRangeValue[] = [];
    const completed: DateRangeValue[] = [];
    component.rangeChange.subscribe(value => changes.push(value));
    component.rangeComplete.subscribe(value => completed.push(value));

    fixture.componentRef.setInput('from', '2026-06-10');
    fixture.componentRef.setInput('to', '');
    fixture.detectChanges();

    component.selectDate('2026-06-14');

    const expected = { from: '2026-06-10', to: '2026-06-14' };
    expect(changes).toEqual([expected]);
    expect(completed).toEqual([expected]);
    expect(component.calendarOpen()).toBe(false);
  });

  it('seleccionar fecha anterior o igual al inicio reinicia el rango', () => {
    const emitted: DateRangeValue[] = [];
    component.rangeChange.subscribe(value => emitted.push(value));

    fixture.componentRef.setInput('from', '2026-06-10');
    fixture.componentRef.setInput('to', '');
    fixture.detectChanges();

    component.selectDate('2026-06-08');

    expect(emitted).toEqual([{ from: '2026-06-08', to: '' }]);
  });

  it('clearDates emite rango vacío', () => {
    const emitted: DateRangeValue[] = [];
    component.rangeChange.subscribe(value => emitted.push(value));

    component.clearDates();

    expect(emitted).toEqual([{ from: '', to: '' }]);
  });

  it('openCalendar usa el mes de from si existe', () => {
    fixture.componentRef.setInput('from', '2026-04-15');
    fixture.detectChanges();

    component.openCalendar();

    expect(component.calendarOpen()).toBe(true);
    expect(component.calendarMonth().getFullYear()).toBe(2026);
    expect(component.calendarMonth().getMonth()).toBe(3);
  });

  it('click fuera cierra y borra el rango si solo hay fecha inicial', () => {
    const emitted: DateRangeValue[] = [];
    const outside = document.createElement('div');
    component.rangeChange.subscribe(value => emitted.push(value));
    fixture.componentRef.setInput('from', '2026-06-10');
    fixture.componentRef.setInput('to', '');
    fixture.detectChanges();
    component.openCalendar();

    component.onDocumentClick(outside);

    expect(emitted).toEqual([{ from: '', to: '' }]);
    expect(component.calendarOpen()).toBe(false);
  });

  it('click fuera mantiene rango parcial si allowPartialRange esta activo', () => {
    const emitted: DateRangeValue[] = [];
    const outside = document.createElement('div');
    component.rangeChange.subscribe(value => emitted.push(value));
    fixture.componentRef.setInput('allowPartialRange', true);
    fixture.componentRef.setInput('from', '2026-06-10');
    fixture.componentRef.setInput('to', '');
    fixture.detectChanges();
    component.openCalendar('from');

    component.onDocumentClick(outside);

    expect(emitted).toEqual([]);
    expect(component.calendarOpen()).toBe(false);
  });

  it('permite seleccionar solo fecha hasta cuando allowPartialRange esta activo', () => {
    const emitted: DateRangeValue[] = [];
    component.rangeChange.subscribe(value => emitted.push(value));
    fixture.componentRef.setInput('allowPartialRange', true);
    fixture.detectChanges();
    component.openCalendar('to');

    component.selectDate('2026-06-14');

    expect(emitted).toEqual([{ from: '', to: '2026-06-14' }]);
    expect(component.calendarOpen()).toBe(false);
  });

  it('click fuera solo cierra si el rango esta completo', () => {
    const emitted: DateRangeValue[] = [];
    let closeCount = 0;
    const outside = document.createElement('div');
    component.rangeChange.subscribe(value => emitted.push(value));
    component.calendarClosed.subscribe(() => closeCount++);
    fixture.componentRef.setInput('from', '2026-06-10');
    fixture.componentRef.setInput('to', '2026-06-14');
    fixture.detectChanges();
    component.openCalendar();

    component.onDocumentClick(outside);

    expect(emitted).toEqual([]);
    expect(component.calendarOpen()).toBe(false);
    expect(closeCount).toBe(1);
  });

  it('click en un input de fecha cierra y borra el rango parcial', () => {
    const emitted: DateRangeValue[] = [];
    const input = fixture.nativeElement.querySelector('.date-range-input') as HTMLButtonElement;
    component.rangeChange.subscribe(value => emitted.push(value));
    fixture.componentRef.setInput('from', '2026-06-10');
    fixture.componentRef.setInput('to', '');
    fixture.detectChanges();
    component.openCalendar();

    input.click();

    expect(emitted).toEqual([{ from: '', to: '' }]);
    expect(component.calendarOpen()).toBe(false);
  });

  it('click dentro del calendario no cierra ni borra el rango parcial', () => {
    const emitted: DateRangeValue[] = [];
    component.rangeChange.subscribe(value => emitted.push(value));
    fixture.componentRef.setInput('from', '2026-06-10');
    fixture.componentRef.setInput('to', '');
    fixture.detectChanges();
    component.openCalendar();
    fixture.detectChanges();

    const calendar = fixture.nativeElement.querySelector('.range-calendar') as HTMLElement;
    component.onDocumentClick(calendar);

    expect(emitted).toEqual([]);
    expect(component.calendarOpen()).toBe(true);
  });

  describe('entrada manual de fechas', () => {
    function changeEvent(value: string): Event {
      const input = document.createElement('input');
      input.value = value;
      return { target: input } as unknown as Event;
    }

    it('muestra inputs de texto y botones de calendario cuando manualInput esta activo', () => {
      fixture.componentRef.setInput('manualInput', true);
      fixture.detectChanges();

      const inputs = fixture.nativeElement.querySelectorAll('input.date-range-input--editable');
      const toggles = fixture.nativeElement.querySelectorAll('.calendar-toggle-btn');
      expect(inputs.length).toBe(2);
      expect(toggles.length).toBe(2);
    });

    it('escribir una fecha valida en dd/mm/aaaa emite el rango', () => {
      const emitted: DateRangeValue[] = [];
      component.rangeChange.subscribe(value => emitted.push(value));

      component.onManualDateInput('from', changeEvent('10/06/2026'));

      expect(emitted).toEqual([{ from: '2026-06-10', to: '' }]);
    });

    it('admite separadores y anio de dos digitos', () => {
      const emitted: DateRangeValue[] = [];
      component.rangeChange.subscribe(value => emitted.push(value));

      component.onManualDateInput('from', changeEvent('1-6-26'));

      expect(emitted).toEqual([{ from: '2026-06-01', to: '' }]);
    });

    it('completar ambas fechas a mano emite rangeComplete', () => {
      const completed: DateRangeValue[] = [];
      component.rangeComplete.subscribe(value => completed.push(value));
      fixture.componentRef.setInput('from', '2026-06-10');
      fixture.detectChanges();

      component.onManualDateInput('to', changeEvent('14/06/2026'));

      expect(completed).toEqual([{ from: '2026-06-10', to: '2026-06-14' }]);
    });

    it('una fecha invalida no emite y restaura el valor mostrado', () => {
      const emitted: DateRangeValue[] = [];
      component.rangeChange.subscribe(value => emitted.push(value));
      fixture.componentRef.setInput('from', '2026-06-10');
      fixture.detectChanges();
      const event = changeEvent('31/02/2026');

      component.onManualDateInput('from', event);

      expect(emitted).toEqual([]);
      expect((event.target as HTMLInputElement).value).toBe('10/06/2026');
    });

    it('vaciar el input limpia esa fecha', () => {
      const emitted: DateRangeValue[] = [];
      component.rangeChange.subscribe(value => emitted.push(value));
      fixture.componentRef.setInput('from', '2026-06-10');
      fixture.componentRef.setInput('to', '2026-06-14');
      fixture.detectChanges();

      component.onManualDateInput('from', changeEvent(''));

      expect(emitted).toEqual([{ from: '', to: '2026-06-14' }]);
    });

    it('una fecha de inicio posterior a la final reinicia la fecha final', () => {
      const emitted: DateRangeValue[] = [];
      component.rangeChange.subscribe(value => emitted.push(value));
      fixture.componentRef.setInput('to', '2026-06-14');
      fixture.detectChanges();

      component.onManualDateInput('from', changeEvent('20/06/2026'));

      expect(emitted).toEqual([{ from: '2026-06-20', to: '' }]);
    });
  });
});
