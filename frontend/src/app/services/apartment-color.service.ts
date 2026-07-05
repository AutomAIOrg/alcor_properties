import { Injectable, inject, signal } from '@angular/core';
import { ApartmentService } from './apartment.service';

/** Convierte un color HSL a hexadecimal #RRGGBB. */
function hslToHex(h: number, s: number, l: number): string {
  const sn = s / 100;
  const ln = l / 100;
  const a = sn * Math.min(ln, 1 - ln);
  const channel = (n: number): string => {
    const k = (n + h / 30) % 12;
    const value = ln - a * Math.max(-1, Math.min(k - 3, 9 - k, 1));
    return Math.round(255 * value)
      .toString(16)
      .padStart(2, '0');
  };
  return `#${channel(0)}${channel(8)}${channel(4)}`;
}

/**
 * Color automático determinista por apartment_id, en hexadecimal #RRGGBB.
 * Usa el ángulo dorado (137.508°) para que apartamentos contiguos en el espacio
 * de hash nunca reciban colores similares. Es el color de respaldo cuando el
 * apartamento no tiene un color personalizado asignado.
 */
export function autoApartmentColor(apartmentId: string): string {
  let hash = 0;
  for (const c of apartmentId) hash = (hash * 31 + c.charCodeAt(0)) & 0xffff;
  const hue = Math.round((hash * 137.508) % 360);
  return hslToHex(hue, 65, 42);
}

/**
 * Fuente única de verdad del color de cada apartamento en toda la app.
 *
 * Resuelve el color final de un apartamento: si tiene un color personalizado
 * (configurado en el panel de administración) lo devuelve; si no, recurre al
 * color automático determinista. El mapa de colores es un signal, de modo que
 * las vistas reactivas (calendario, limpieza) se recalculan solas al cargarse
 * o actualizarse los colores.
 */
@Injectable({ providedIn: 'root' })
export class ApartmentColorService {
  private readonly apartmentService = inject(ApartmentService);

  /** apartment_id → color personalizado (#RRGGBB). Solo contiene los que lo tienen. */
  private readonly overrides = signal<ReadonlyMap<string, string>>(new Map());

  /** Evita recargas redundantes del mapa de colores. */
  private loaded = false;

  /** Color personalizado del apartamento o, si no tiene, el color automático. */
  resolve(apartmentId: string): string {
    return this.overrides().get(apartmentId) ?? autoApartmentColor(apartmentId);
  }

  /**
   * Carga el mapa de colores una sola vez (idempotente). Pensado para las vistas
   * que muestran colores. Si la carga falla, se permite reintentar y las vistas
   * siguen funcionando con el color automático.
   */
  ensureLoaded(): void {
    if (this.loaded) return;
    this.loaded = true;

    this.apartmentService.getAllApartments().subscribe({
      next: apartments => this.setFromApartments(apartments),
      error: () => {
        this.loaded = false;
      },
    });
  }

  /**
   * Refresca el mapa a partir de una lista de apartamentos ya cargada (p. ej.
   * tras crear/editar un apartamento en el panel de administración), para que el
   * resto de vistas reflejen el cambio sin volver a pedir los datos.
   */
  setFromApartments(apartments: readonly { apartment_id: string; color: string | null }[]): void {
    const map = new Map<string, string>();
    for (const apartment of apartments) {
      if (apartment.color) map.set(apartment.apartment_id, apartment.color);
    }
    this.overrides.set(map);
    this.loaded = true;
  }
}
