import { Component, computed, input, output } from '@angular/core';

@Component({
  selector: 'app-calendar-header',
  standalone: true,
  templateUrl: './calendar-header.component.html',
  styleUrl: './calendar-header.component.scss'
})
export class CalendarHeaderComponent {
  month    = input.required<number>();
  year     = input.required<number>();
  viewMode = input<'month' | 'week'>('month');

  prev           = output<void>();
  next           = output<void>();
  today          = output<void>();
  dateChange     = output<{ month: number; year: number }>();
  viewModeChange = output<'month' | 'week'>();

  readonly MONTHS = [
    'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'
  ];

  yearOptions = computed(() => {
    const y = this.year();
    return Array.from({ length: 11 }, (_, i) => y - 5 + i);
  });

  onMonthChange(value: string): void {
    this.dateChange.emit({ month: +value, year: this.year() });
  }

  onYearChange(value: string): void {
    this.dateChange.emit({ month: this.month(), year: +value });
  }
}
