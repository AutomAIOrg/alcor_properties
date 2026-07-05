import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  CleaningType,
  CleaningTypeCreateRequest,
  CleaningTypeUpdateRequest,
} from '../models/cleaning-type.model';

export type {
  CleaningType,
  CleaningTypeCreateRequest,
  CleaningTypeUpdateRequest,
} from '../models/cleaning-type.model';

@Injectable({ providedIn: 'root' })
export class CleaningTypeService {
  private readonly API = `${environment.apiUrl}/api/v1/cleaning-types`;

  constructor(private http: HttpClient) {}

  list(activeOnly = false): Observable<CleaningType[]> {
    let params = new HttpParams();
    if (activeOnly) {
      params = params.set('active_only', 'true');
    }
    return this.http.get<CleaningType[]>(`${this.API}/`, { params });
  }

  create(payload: CleaningTypeCreateRequest): Observable<CleaningType> {
    return this.http.post<CleaningType>(`${this.API}/`, payload);
  }

  update(cleaningTypeId: number, payload: CleaningTypeUpdateRequest): Observable<CleaningType> {
    return this.http.put<CleaningType>(`${this.API}/${cleaningTypeId}`, payload);
  }

  delete(cleaningTypeId: number): Observable<void> {
    return this.http.delete<void>(`${this.API}/${cleaningTypeId}`);
  }
}
