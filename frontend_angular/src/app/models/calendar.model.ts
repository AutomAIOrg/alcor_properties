import { Booking } from './booking.model';

export interface CalendarDay {
  date: Date;
  currentMonth: boolean;
  isToday: boolean;
}

export interface WeekBar {
  booking: Booking;
  laneIndex: number;
  leftPct: number;
  widthPct: number;
  isCheckin: boolean;
  isCheckout: boolean;
  background: string;
}

export interface CalendarWeek {
  days: CalendarDay[];
  bars: WeekBar[];
  totalLanes: number;
}
