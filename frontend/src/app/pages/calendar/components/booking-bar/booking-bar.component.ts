import { Component, inject, input, output } from '@angular/core';
import { Booking } from '../../../../models/booking.model';
import { WeekBar } from '../../../../models/calendar.model';
import { CalendarLayoutService } from '../../../../services/calendar-layout.service';

@Component({
  selector: 'app-booking-bar',
  standalone: true,
  templateUrl: './booking-bar.component.html',
  styleUrl: './booking-bar.component.scss',
})
export class BookingBarComponent {
  bar = input.required<WeekBar>();
  barClick = output<Booking>();

  private layout = inject(CalendarLayoutService);

  get height(): number {
    return this.layout.BAR_HEIGHT;
  }
  get top(): number {
    return this.layout.barTop(this.bar().laneIndex);
  }
}
