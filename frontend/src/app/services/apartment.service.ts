import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

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
}

export interface ApartmentMessageResponse {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class ApartmentService {
  private readonly API = `${environment.apiUrl}/api/v1/apartments`;

  constructor(private http: HttpClient) {}

  getAllApartments(): Observable<ApartmentResponse[]> {
    return this.http.get<ApartmentResponse[]>(`${this.API}/all`);
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
}
