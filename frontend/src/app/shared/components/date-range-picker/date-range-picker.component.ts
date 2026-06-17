import { Component, HostListener, computed, input, output, signal } from '@angular/core';

export type DateRangeValue = {
  from: string;
  to: string;
};

type CalendarDay = {
  iso: string;
  label: number;
  inCurrentMonth: boolean;
  isStart: boolean;
  isEnd: boolean;
  inRange: boolean;
};

@Component({
  selector: 'app-date-range-picker',
  standalone: true,
  templateUrl: './date-range-picker.component.html',
  styleUrl: './date-range-picker.component.scss',
})
export class DateRangePickerComponent {
  from = input('');
  to = input('');
  fromLabel = input('Desde');
  toLabel = input('Hasta');
  fromPlaceholder = input('Seleccionar entrada');
  toPlaceholder = input('Seleccionar salida');
  required = input(false);
  allowPartialRange = input(false);

  rangeChange = output<DateRangeValue>();
  rangeComplete = output<DateRangeValue>();
  calendarClosed = output<void>();

  readonly weekdays = ['L', 'M', 'X', 'J', 'V', 'S', 'D'];

  calendarOpen = signal(false);
  calendarMonth = signal(new Date());
  hoverIso = signal<string | null>(null);
  activeField = signal<'from' | 'to'>('from');

  calendarTitle = computed(() =>
    new Intl.DateTimeFormat('es-ES', { month: 'long', year: 'numeric' }).format(
      this.calendarMonth()
    )
  );

  calendarDays = computed<CalendarDay[]>(() => {
    const monthDate = this.calendarMonth();
    const year = monthDate.getFullYear();
    const month = monthDate.getMonth();
    const firstDay = new Date(year, month, 1);
    const firstWeekDay = (firstDay.getDay() + 6) % 7;
    const gridStart = new Date(year, month, 1 - firstWeekDay);
    const start = this.from() || null;
    const selectedEnd = this.to() || null;
    const hover = this.hoverIso();
    const previewEnd = start && !selectedEnd && hover && hover > start ? hover : selectedEnd;

    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(gridStart);
      date.setDate(gridStart.getDate() + index);
      const iso = this.isoFromDate(date);

      return {
        iso,
        label: date.getDate(),
        inCurrentMonth: date.getMonth() === month,
        isStart: iso === start,
        isEnd: iso === previewEnd,
        inRange: !!start && !!previewEnd && iso > start && iso < previewEnd,
      };
    });
  });

  openCalendar(field: 'from' | 'to' = 'from'): void {
    const selectedDate = field === 'to' ? this.to() || this.from() : this.from() || this.to();
    this.activeField.set(field);
    this.calendarMonth.set(selectedDate ? this.dateFromIso(selectedDate) : new Date());
    this.calendarOpen.set(true);
  }

  onDateInputClick(event: MouseEvent, field: 'from' | 'to'): void {
    event.stopPropagation();

    if (this.calendarOpen() && this.hasIncompleteRange() && !this.allowPartialRange()) {
      this.emitRange({ from: '', to: '' });
      this.closeCalendar();
      return;
    }

    this.openCalendar(field);
  }

  prevMonth(): void {
    const date = this.calendarMonth();
    this.calendarMonth.set(new Date(date.getFullYear(), date.getMonth() - 1, 1));
  }

  nextMonth(): void {
    const date = this.calendarMonth();
    this.calendarMonth.set(new Date(date.getFullYear(), date.getMonth() + 1, 1));
  }

  selectDate(iso: string): void {
    const from = this.from();
    const to = this.to();

    if (this.allowPartialRange() && this.activeField() === 'to') {
      const range = from && iso > from ? { from, to: iso } : { from: '', to: iso };
      this.emitRange(range);
      this.closeCalendar();
      if (range.from && range.to) this.rangeComplete.emit(range);
      return;
    }

    if (!from || to) {
      this.emitRange({ from: iso, to: '' });
      if (this.allowPartialRange()) this.closeCalendar();
      return;
    }

    if (iso <= from) {
      this.emitRange({ from: iso, to: '' });
      return;
    }

    const range = { from, to: iso };
    this.emitRange(range);
    this.closeCalendar();
    this.rangeComplete.emit(range);
  }

  clearDates(): void {
    this.emitRange({ from: '', to: '' });
    this.calendarMonth.set(new Date());
    this.hoverIso.set(null);
  }

  onDayHover(day: CalendarDay): void {
    this.hoverIso.set(day.iso);
  }

  @HostListener('document:click', ['$event.target'])
  onDocumentClick(target: EventTarget | null): void {
    if (!(target instanceof Element)) return;
    if (!this.calendarOpen() || target.closest('.range-calendar')) return;

    if (this.hasIncompleteRange() && !this.allowPartialRange()) {
      this.emitRange({ from: '', to: '' });
    }

    this.closeCalendar();
  }

  formatDisplayDate(iso: string): string {
    if (!iso) return '';
    const [year, month, day] = iso.split('-');
    return `${day}/${month}/${year}`;
  }

  closeCalendar(): void {
    const wasOpen = this.calendarOpen();
    this.calendarOpen.set(false);
    this.hoverIso.set(null);
    if (wasOpen) this.calendarClosed.emit();
  }

  private emitRange(range: DateRangeValue): void {
    this.rangeChange.emit(range);
  }

  private hasIncompleteRange(): boolean {
    return (!!this.from() && !this.to()) || (!this.from() && !!this.to());
  }

  private isoFromDate(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  private dateFromIso(iso: string): Date {
    const [year, month, day] = iso.split('-').map(Number);
    return new Date(year, month - 1, day);
  }
}
