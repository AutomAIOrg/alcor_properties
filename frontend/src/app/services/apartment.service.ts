import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { map, Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Apartment } from '../models/apartment.model';
import { ApartmentStatsResponse } from '../models/search.model';

export interface ApartmentResponse {
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

export type ApartmentCreateRequest = ApartmentResponse;

export interface ApartmentUpdateRequest {
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

export interface ApartmentMessageResponse {
  message: string;
}

type ApartmentSearchParams = {
  q?: string;
  apartment_id?: string;
  community?: string;
  apartment_description?: string;
  address?: string;
  parking?: string;
  owner_name?: string;
  email?: string;
  phone?: string;
  min_rooms?: number;
  min_bathrooms?: number;
  min_occupants?: number;
  max_occupants?: number;
  available_from?: string;
  available_to?: string;
};

@Injectable({ providedIn: 'root' })
export class ApartmentService {
  private readonly API = `${environment.apiUrl}/api/v1/apartments`;

  constructor(private http: HttpClient) {}

  getAllApartments(): Observable<ApartmentResponse[]> {
    return this.http.get<ApartmentResponse[]>(`${this.API}/`);
  }

  createApartment(data: ApartmentCreateRequest): Observable<ApartmentMessageResponse> {
    return this.http.post<ApartmentMessageResponse>(`${this.API}/`, data);
  }

  updateApartment(
    apartmentId: string,
    data: ApartmentUpdateRequest
  ): Observable<ApartmentMessageResponse> {
    return this.http.put<ApartmentMessageResponse>(`${this.API}/${apartmentId}`, data);
  }

  deleteApartment(apartmentId: string): Observable<ApartmentMessageResponse> {
    return this.http.delete<ApartmentMessageResponse>(`${this.API}/${apartmentId}`);
  }

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
    }).pipe(map(apartments => apartments.map(apartment => apartment.apartment_id).sort()));
  }

  getAllApartmentIds(): Observable<string[]> {
    return this.searchApartments({}).pipe(
      map(apartments =>
        apartments
          .map(apartment => apartment.apartment_id)
          .filter((bookingId): bookingId is string => bookingId !== undefined && bookingId !== null)
          .sort()
      )
    );
  }

  getApartmentStats(
    apartmentId: string,
    startDate?: string,
    endDate?: string
  ): Observable<ApartmentStatsResponse> {
    let params = new HttpParams();
    if (startDate) params = params.set('start_date', startDate);
    if (endDate) params = params.set('end_date', endDate);

    return this.http.get<ApartmentStatsResponse>(
      `${this.API}/stats/${encodeURIComponent(apartmentId)}`,
      { params }
    );
  }
}
