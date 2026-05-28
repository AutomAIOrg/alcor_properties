import { Injectable } from '@angular/core';
import { jwtDecode } from 'jwt-decode';
import { User } from '../models/user.model';

const ACCESS_TOKEN_KEY = 'auth_access_token';
const REFRESH_TOKEN_KEY = 'auth_refresh_token';
const LEGACY_TOKEN_KEY = 'auth_token';

@Injectable({ providedIn: 'root' })
export class TokenService {
  setTokens(accessToken: string, refreshToken: string): void {
    this.setAccessToken(accessToken);
    this.setRefreshToken(refreshToken);
  }

  setAccessToken(token: string): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, token);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
  }

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY) ?? localStorage.getItem(LEGACY_TOKEN_KEY);
  }

  setRefreshToken(token: string): void {
    localStorage.setItem(REFRESH_TOKEN_KEY, token);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  removeTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(LEGACY_TOKEN_KEY);
  }

  setToken(token: string): void {
    this.setAccessToken(token);
  }

  getToken(): string | null {
    return this.getAccessToken();
  }

  removeToken(): void {
    this.removeTokens();
  }

  decodeToken(): User | null {
    const token = this.getAccessToken();
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
