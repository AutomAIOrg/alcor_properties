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
});
