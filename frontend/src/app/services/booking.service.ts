import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Booking } from '../models/booking.model';
import { BookingSearchFilters, BookingStatsResponse } from '../models/search.model';
import { environment } from '../../environments/environment';

export type { Booking } from '../models/booking.model';

type BookingCreatePayload = Omit<Booking, 'record_id' | 'electric_allowance'>;

@Injectable({ providedIn: 'root' })
export class BookingService {
  private readonly API = `${environment.apiUrl}/api/v1/bookings`;

  constructor(private http: HttpClient) {}

  getBookings(): Observable<Booking[]> {
    return this.http.get<Booking[]>(`${this.API}/`);
  }

  searchBookings(filters: BookingSearchFilters): Observable<Booking[]> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get<Booking[]>(`${this.API}/`, { params });
  }

  getBookingStats(filters: Omit<BookingSearchFilters, 'limit'>): Observable<BookingStatsResponse> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get<BookingStatsResponse>(`${this.API}/stats`, { params });
  }

  updateBooking(recordId: number, data: Partial<Booking>): Observable<Booking> {
    return this.http.put<Booking>(`${this.API}/${recordId}`, data);
  }

  createBooking(data: BookingCreatePayload): Observable<Booking> {
    return this.http.post<Booking>(`${this.API}/`, data);
  }
}
