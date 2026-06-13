import { Pipe, PipeTransform } from '@angular/core';

/**
 * Pipe pura que genera un color HSL único por apartment_id.
 * Usa el ángulo dorado (137.508°) para garantizar que colores adyacentes
 * en el espacio de hash nunca sean similares entre sí.
 *
 * Al ser `pure: true` (por defecto), Angular la memoiza automáticamente.
 */
@Pipe({
  name: 'bookingColor',
  standalone: true,
})
export class BookingColorPipe implements PipeTransform {
  transform(bookingId: string): string {
    let hash = 0;
    for (const c of bookingId) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff;
    const hue = Math.round((hash * 137.508) % 360);
    return `hsl(${hue}, 65%, 42%)`;
  }
}
