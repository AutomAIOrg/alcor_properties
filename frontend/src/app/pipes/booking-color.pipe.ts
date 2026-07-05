import { Pipe, PipeTransform, inject } from '@angular/core';
import { ApartmentColorService } from '../services/apartment-color.service';

/**
 * Pipe que devuelve el color de un apartamento a partir de su apartment_id.
 * Delega en ApartmentColorService, que aplica el color personalizado del piso
 * o, en su defecto, el color automático determinista.
 *
 * Impuro a propósito: el color no depende solo del apartment_id de entrada, sino
 * también del mapa de colores (un signal de ApartmentColorService) que se carga
 * de forma asíncrona. Un pipe puro memoizaría el color automático inicial y no
 * reflejaría el color personalizado al terminar la carga.
 */
@Pipe({
  name: 'bookingColor',
  standalone: true,
  pure: false,
})
export class BookingColorPipe implements PipeTransform {
  private readonly colors = inject(ApartmentColorService);

  transform(apartmentId: string): string {
    return this.colors.resolve(apartmentId);
  }
}
