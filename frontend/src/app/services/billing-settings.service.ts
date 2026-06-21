import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

export interface CleaningRateResponse {
  cleaning_hourly_rate: number;
}

@Injectable({ providedIn: 'root' })
export class BillingSettingsService {
  private readonly API = `${environment.apiUrl}/api/v1/settings`;

  constructor(private http: HttpClient) {}

  getCleaningRate(): Observable<CleaningRateResponse> {
    return this.http.get<CleaningRateResponse>(`${this.API}/cleaning-rate`);
  }

  updateCleaningRate(rate: number): Observable<CleaningRateResponse> {
    return this.http.put<CleaningRateResponse>(`${this.API}/cleaning-rate`, {
      cleaning_hourly_rate: rate,
    });
  }
}
