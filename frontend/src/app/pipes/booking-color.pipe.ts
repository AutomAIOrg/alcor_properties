import { Pipe, PipeTransform, inject } from '@angular/core';
import { ApartmentColorService } from '../services/apartment-color.service';

/**
 * Pipe que devuelve el color de un apartamento a partir de su apartment_id.
 * Delega en ApartmentColorService, que aplica el color personalizado del piso
 * o, en su defecto, el color automático determinista.
 */
@Pipe({
  name: 'bookingColor',
  standalone: true,
})
export class BookingColorPipe implements PipeTransform {
  private readonly colors = inject(ApartmentColorService);

  transform(apartmentId: string): string {
    return this.colors.resolve(apartmentId);
  }
}
