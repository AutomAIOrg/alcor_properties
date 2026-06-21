import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Bill,
  BillCreatePayload,
  BillSearchFilters,
  BillStateUpdatePayload,
} from '../models/bill.model';
import { environment } from '../../environments/environment';

export type {
  Bill,
  BillCreatePayload,
  BillSearchFilters,
  BillStateUpdatePayload,
} from '../models/bill.model';

@Injectable({ providedIn: 'root' })
export class BillService {
  private readonly API = `${environment.apiUrl}/api/v1/bills`;

  constructor(private http: HttpClient) {}

  searchBills(filters: BillSearchFilters): Observable<Bill[]> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get<Bill[]>(`${this.API}/`, { params });
  }

  createBill(data: BillCreatePayload): Observable<Bill> {
    return this.http.post<Bill>(`${this.API}/`, data);
  }

  updateBillState(billId: number, data: BillStateUpdatePayload): Observable<Bill> {
    return this.http.patch<Bill>(`${this.API}/${billId}`, data);
  }
}
