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
}
