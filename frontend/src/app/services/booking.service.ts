import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { Booking, CleaningOpportunity } from '../models/booking.model';
import { environment } from '../../environments/environment';

// Re-export so existing imports of BookingService still get Booking from here
export type { Booking, CleaningOpportunity } from '../models/booking.model';

@Injectable({ providedIn: 'root' })
export class BookingService {
  private readonly API = `${environment.apiUrl}/api/v1/bookings`;

  constructor(private http: HttpClient) {}

  getBookings(): Observable<Booking[]> {
    return this.http.get<Booking[]>(`${this.API}/`);
  }

  getCleaningOpportunities(): Observable<CleaningOpportunity[]> {
    return this.http.get<CleaningOpportunity[]>(`${this.API}/cleaning-opportunities`);
  }

  updateBooking(recordId: number, data: Partial<Booking>): Observable<Booking> {
    return this.http.put<Booking>(`${this.API}/${recordId}`, data);
  }

  createBooking(data: Omit<Booking, 'record_id'>): Observable<Booking> {
    return this.http.post<Booking>(`${this.API}/`, data);
  }
}
