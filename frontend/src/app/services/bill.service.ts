import { Injectable } from '@angular/core';
import { HttpClient, HttpParams, HttpResponse } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Bill,
  BillCreateRequest,
  BillListFilters,
  BillRectifyRequest,
  BillUpdateStateRequest,
} from '../models/bill.model';

export type {
  Bill,
  BillCreateRequest,
  BillListFilters,
  BillRectifyRequest,
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

  rectifyBill(billId: number, payload: BillRectifyRequest): Observable<Bill> {
    return this.http.put<Bill>(`${this.API}/bills/${billId}/rectify`, payload);
  }

  /**
   * Descarga el recibo en PDF de una factura.
   *
   * Va por HttpClient (y no por un enlace directo) porque la petición necesita el token que
   * añade el interceptor. Se observa la respuesta completa para poder leer el nombre del
   * archivo de la cabecera Content-Disposition.
   */
  downloadBillDocument(billId: number): Observable<HttpResponse<Blob>> {
    return this.http.get(`${this.API}/bills/${billId}/document`, {
      responseType: 'blob',
      observe: 'response',
    });
  }
}
