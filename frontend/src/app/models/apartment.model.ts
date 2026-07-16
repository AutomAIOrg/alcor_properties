/**
 * Importe por noche que se propone al activar el cupo eléctrico de un apartamento.
 * Coincide con el valor por defecto del backend; cada apartamento guarda el suyo y el
 * administrador puede cambiarlo.
 */
export const DEFAULT_ELECTRIC_ALLOWANCE_RATE = 4;

export interface Apartment {
  apartment_id: string;
  community: string | null;
  apartment_description: string | null;
  address: string | null;
  rooms: number;
  bathrooms: number;
  parking: string;
  total_occupants: number;
  owner_name: string | null;
  email: string | null;
  phone: string | null;
  color: string | null;
  electric_allowance_enabled: boolean;
  electric_allowance_rate: number;
}
