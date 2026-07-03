import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Bill,
  BillCreateRequest,
  BillListFilters,
  BillUpdateStateRequest,
} from '../models/bill.model';

export type {
  Bill,
  BillCreateRequest,
  BillListFilters,
  BillUpdateStateRequest,
} from '../models/bill.model';

@Injectable({ providedIn: 'root' })
export class BillService {
  private readonly API = `${environment.apiUrl}/api/v1`;

  constructor(private http: HttpClient) {}

  listBills(filters: BillListFilters = {}): Observable<Bill[]> {
    let params = new HttpParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        params = params.set(key, String(value));
      }
    });
    return this.http.get<Bill[]>(`${this.API}/bills/`, { params });
  }

  createBill(payload: BillCreateRequest): Observable<Bill> {
    return this.http.post<Bill>(`${this.API}/bills/`, payload);
  }

  updateBillState(billId: number, payload: BillUpdateStateRequest): Observable<Bill> {
    return this.http.put<Bill>(`${this.API}/bills/${billId}`, payload);
  }
}
