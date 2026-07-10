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
  // Número de semana ISO-8601 (1..53) al que pertenece esta fila. Las semanas
  // empiezan en lunes, coherente con la cabecera Lun…Dom del calendario.
  weekNumber: number;
}
