import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { map, Observable } from 'rxjs';

import { environment } from '../../environments/environment';
import { Apartment } from '../models/apartment.model';

type ApartmentSearchParams = {
  q?: string;
  booking_id?: string;
  community?: string;
  booking_name?: string;
  address?: string;
  parking?: string;
  owner_name?: string;
  email?: string;
  phone?: string;
  min_rooms?: number;
  max_rooms?: number;
  min_bathrooms?: number;
  max_bathrooms?: number;
  min_occupants?: number;
  max_occupants?: number;
  available_from?: string;
  available_to?: string;
};

@Injectable({ providedIn: 'root' })
export class ApartmentService {
  private readonly API = `${environment.apiUrl}/api/v1/apartments`;

  constructor(private http: HttpClient) {}

  searchApartments(filters: ApartmentSearchParams): Observable<Apartment[]> {
    let params = new HttpParams();

    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });

    return this.http.get<Apartment[]>(`${this.API}/search`, { params });
  }

  getAvailableApartmentIds(checkIn: string, checkOut: string): Observable<string[]> {
    return this.searchApartments({
      available_from: checkIn,
      available_to: checkOut,
    }).pipe(map(apartments => apartments.map(apartment => apartment.booking_id).sort()));
  }
}