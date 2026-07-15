import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import { Role } from '../models/user.model';

export interface AdminUserResponse {
  id: number;
  username: string;
  name: string;
  lastname?: string | null;
  email?: string | null;
  role: Role;
}

export interface AdminUserSaveRequest {
  username: string;
  name: string;
  lastname: string;
  email?: string;
  role: Role;
}

export interface ApiMessageResponse {
  message: string;
}

@Injectable({ providedIn: 'root' })
export class AdminUserService {
  private readonly API = `${environment.apiUrl}/api/v1/users/`;

  constructor(private http: HttpClient) {}

  getUsers(): Observable<AdminUserResponse[]> {
    return this.http.get<AdminUserResponse[]>(this.API);
  }

  createUser(data: AdminUserSaveRequest): Observable<ApiMessageResponse> {
    return this.http.post<ApiMessageResponse>(this.API, data);
  }

  updateUser(userId: number, data: AdminUserSaveRequest): Observable<ApiMessageResponse> {
    return this.http.put<ApiMessageResponse>(`${this.API}${userId}`, data);
  }

  deleteUser(userId: number): Observable<ApiMessageResponse> {
    return this.http.delete<ApiMessageResponse>(`${this.API}${userId}`);
  }
}
