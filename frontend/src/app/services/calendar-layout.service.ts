import { Injectable } from '@angular/core';
import { Booking } from '../models/booking.model';
import { CalendarDay, CalendarWeek, WeekBar } from '../models/calendar.model';
import { BookingColorPipe } from '../pipes/booking-color.pipe';

/**
 * Servicio de layout del calendario.
 * Responsabilidad única: transformar una lista de reservas + un mes
 * en la estructura de semanas + barras posicionadas que el template necesita.
 *
 * Completamente desacoplado del DOM: es testeable de forma unitaria.
 */
@Injectable({ providedIn: 'root' })
export class CalendarLayoutService {
  // Constantes de layout exportadas para que los componentes puedan usarlas
  readonly BAR_HEIGHT = 22; // px
  readonly BAR_GAP = 2; // px entre carriles
  readonly DAY_HEADER_H = 30; // px del número de día
  readonly BAR_TOP_PAD = 4; // px de padding superior sobre las barras

  private readonly colorPipe = new BookingColorPipe();

  /**
   * Altura mínima de una fila semanal según el número de carriles activos.
   */
  weekHeight(totalLanes: number): number {
    return this.DAY_HEADER_H + this.BAR_TOP_PAD + totalLanes * (this.BAR_HEIGHT + this.BAR_GAP) + 8;
  }

  /**
   * Posición vertical (top) de un carril dentro de la fila semanal.
   */
  barTop(laneIndex: number): number {
    return this.DAY_HEADER_H + this.BAR_TOP_PAD + laneIndex * (this.BAR_HEIGHT + this.BAR_GAP);
  }

  /**
   * Asigna a cada reserva (record_id) un índice de carril fijo
   * usando un algoritmo greedy: busca el primer carril libre.
   * Usa record_id (único en BD) como clave, NO apartment_id (identificador de piso).
   */
  buildLaneAssignment(bookings: Booking[]): Map<number, number> {
    const sorted = [...bookings].sort((a, b) => a.check_in.localeCompare(b.check_in));
    const laneEnd: string[] = [];
    const assignment = new Map<number, number>();

    for (const b of sorted) {
      let lane = laneEnd.findIndex(end => end <= b.check_in);
      if (lane === -1) lane = laneEnd.length;
      assignment.set(b.record_id, lane);
      laneEnd[lane] = b.check_out;
    }

    return assignment;
  }

  /**
   * Construye la lista de semanas del mes visible (incluye días de meses
   * adyacentes para completar filas de 7).
   */
  buildWeeks(
    year: number,
    month: number,
    bookings: Booking[],
    todayStr: string,
    assignment: Map<number, number>
  ): CalendarWeek[] {
    const calDates = this.buildCalendarDates(year, month);
    const result: CalendarWeek[] = [];

    for (let w = 0; w < calDates.length; w += 7) {
      const weekDates = calDates.slice(w, w + 7);
      const weekStartStr = weekDates[0].iso;
      const weekEndStr = weekDates[6].iso;

      const days: CalendarDay[] = weekDates.map(wd => ({
        date: wd.date,
        currentMonth: wd.currentMonth,
        isToday: wd.iso === todayStr,
      }));

      const overlapping = bookings.filter(
        b => b.check_in <= weekEndStr && b.check_out >= weekStartStr
      );

      const rawBars: WeekBar[] = [];

      for (const b of overlapping) {
        const bar = this.buildBar(b, weekDates, weekStartStr, weekEndStr, assignment);
        if (bar) rawBars.push(bar);
      }

      // Reindexar carriles: mantener orden relativo pero compactar a 0, 1, 2...
      // El alto de la fila = nº de reservas visibles en esa semana, no su posición global.
      // Usar Set para deduplicar carriles globales, de modo que checkout+checkin el mismo día
      // en el mismo apartamento compartan el mismo índice visual.
      rawBars.sort((a, b) => a.laneIndex - b.laneIndex);
      const uniqueLanes = [...new Set(rawBars.map(b => b.laneIndex))];
      const laneRemap = new Map(uniqueLanes.map((lane, i) => [lane, i]));
      const bars: WeekBar[] = rawBars.map(bar => ({
        ...bar,
        laneIndex: laneRemap.get(bar.laneIndex)!,
      }));
      const totalLanes = uniqueLanes.length;

      result.push({ days, bars, totalLanes });
    }

    return result;
  }

  // ─── Métodos privados ────────────────────────────────────────────────────

  private buildCalendarDates(year: number, month: number) {
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);

    let startOffset = firstDay.getDay() - 1;
    if (startOffset < 0) startOffset = 6;

    const dates: { date: Date; currentMonth: boolean; iso: string }[] = [];

    for (let i = startOffset - 1; i >= 0; i--) {
      const d = new Date(year, month, -i);
      dates.push({ date: d, currentMonth: false, iso: this.toIso(d) });
    }
    for (let i = 1; i <= lastDay.getDate(); i++) {
      const d = new Date(year, month, i);
      dates.push({ date: d, currentMonth: true, iso: this.toIso(d) });
    }
    const remaining = (7 - (dates.length % 7)) % 7;
    for (let i = 1; i <= remaining; i++) {
      const d = new Date(year, month + 1, i);
      dates.push({ date: d, currentMonth: false, iso: this.toIso(d) });
    }

    return dates;
  }

  private buildBar(
    b: Booking,
    weekDates: { date: Date; currentMonth: boolean; iso: string }[],
    weekStartStr: string,
    weekEndStr: string,
    assignment: Map<number, number>
  ): WeekBar | null {
    const laneIndex = assignment.get(b.record_id) ?? 0;
    const isCheckin = b.check_in >= weekStartStr && b.check_in <= weekEndStr;
    const isCheckout = b.check_out >= weekStartStr && b.check_out <= weekEndStr;

    // Columna de inicio/fin dentro de esta semana
    const colStart = isCheckin ? weekDates.findIndex(wd => wd.iso === b.check_in) : 0;
    const colEnd = isCheckout ? weekDates.findIndex(wd => wd.iso === b.check_out) : 6;

    if (colStart < 0 || colEnd < 0) return null;

    // Checkin arranca en el último tercio de su celda; checkout termina en el primero
    const cellPct = 100 / 7;
    const leftPct = isCheckin ? (colStart + 2 / 3) * cellPct : colStart * cellPct;
    const rightPct = isCheckout ? (colEnd + 1 / 3) * cellPct : (colEnd + 1) * cellPct;
    const widthPct = rightPct - leftPct;

    if (widthPct <= 0) return null;

    const background = this.buildBackground(b.apartment_id, isCheckin, isCheckout, widthPct);

    return { booking: b, laneIndex, leftPct, widthPct, isCheckin, isCheckout, background };
  }

  private buildBackground(
    bookingId: string,
    isCheckin: boolean,
    isCheckout: boolean,
    widthPct: number
  ): string {
    const color = this.colorPipe.transform(bookingId);

    // Indicador de tamaño fijo: 10% de 1/3 de celda, expresado como % de la barra
    const indicatorPct = 1000 / 10 / widthPct;
    const g = indicatorPct.toFixed(3);
    const r = (100 - indicatorPct).toFixed(3);

    if (isCheckin && isCheckout) {
      return `linear-gradient(to right, #54de4a 0%, #54de4a ${g}%, ${color} ${g}%, ${color} ${r}%, #fd0202 ${r}%, #fd0202 100%)`;
    }
    if (isCheckin) {
      return `linear-gradient(to right, #54de4a 0%, #54de4a ${g}%, ${color} ${g}%)`;
    }
    if (isCheckout) {
      return `linear-gradient(to right, ${color} 0%, ${color} ${r}%, #fd0202 ${r}%, #fd0202 100%)`;
    }
    return color;
  }

  toIso(date: Date): string {
    const y = date.getFullYear();
    const m = String(date.getMonth() + 1).padStart(2, '0');
    const d = String(date.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }
}
