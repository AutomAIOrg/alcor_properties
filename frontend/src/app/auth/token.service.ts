import { Injectable } from '@angular/core';
import { jwtDecode } from 'jwt-decode';
import { User } from '../models/user.model';

const TOKEN_KEY = 'auth_token';

@Injectable({ providedIn: 'root' })
export class TokenService {
  setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  decodeToken(): User | null {
    const token = this.getToken();
    if (!token) return null;
    try {
      return jwtDecode<User>(token);
    } catch {
      return null;
    }
  }

  isTokenExpired(): boolean {
    const payload = this.decodeToken();
    if (!payload?.exp) return true;
    return Date.now() / 1000 > payload.exp;
  }

  isValid(): boolean {
    return !!this.getToken() && !this.isTokenExpired();
  }
}
