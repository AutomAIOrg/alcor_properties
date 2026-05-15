import { Component, inject, input, output } from '@angular/core';
import { Booking } from '../../../../models/booking.model';
import { CalendarWeek } from '../../../../models/calendar.model';
import { CalendarLayoutService } from '../../../../services/calendar-layout.service';
import { BookingBarComponent } from '../booking-bar/booking-bar.component';

@Component({
  selector: 'app-week-row',
  standalone: true,
  imports: [BookingBarComponent],
  templateUrl: './week-row.component.html',
  styleUrl: './week-row.component.scss'
})
export class WeekRowComponent {
  week = input.required<CalendarWeek>();
  barClick = output<Booking>();

  private layout = inject(CalendarLayoutService);

  get weekHeight(): number {
    return this.layout.weekHeight(this.week().totalLanes);
  }
}
