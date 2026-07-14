import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { Observable, tap } from 'rxjs';
import { TokenService } from './token.service';
import { SessionActivityService } from './session-activity.service';
import {
  AccessTokenResponse,
  AuthRequest,
  AuthResponse,
  MessageResponse,
} from '../models/auth.model';
import { User, Role, Permission } from '../models/user.model';
import { ROLE_PERMISSIONS } from '../config/permissions.config';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private http = inject(HttpClient);
  private router = inject(Router);
  private tokenService = inject(TokenService);
  private sessionActivity = inject(SessionActivityService);

  private readonly API = '/api/v1/auth';

  // ── Estado reactivo ────────────────────────────────────────────────────────
  private _currentUser = signal<User | null>(this.loadUserFromToken());

  currentUser = this._currentUser.asReadonly();
  isAuthenticated = computed(() => !!this._currentUser());
  currentRole = computed(() => this._currentUser()?.role ?? null);

  // ── Login / Logout ─────────────────────────────────────────────────────────
  login(credentials: AuthRequest): Observable<AuthResponse> {
    return this.http.post<AuthResponse>(`${this.API}/login`, credentials).pipe(
      tap(response => {
        this.tokenService.setTokens(response.access_token, response.refresh_token);
        this.sessionActivity.recordActivity();
        this.sessionActivity.start(() => this.logout());
        this._currentUser.set(this.tokenService.decodeToken());
      })
    );
  }

  // ── Recuperación de contraseña ─────────────────────────────────────────────
  // Si el email está registrado, el backend envía un enlace de restablecimiento.
  // La respuesta es siempre la misma (no revela si el email existe).
  forgotPassword(email: string): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.API}/forgot-password`, { email });
  }

  // Fija la nueva contraseña a partir del token recibido por email.
  // No deja al usuario autenticado: tras el cambio debe iniciar sesión.
  resetPassword(resetToken: string, newPassword: string): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.API}/reset-password`, {
      reset_token: resetToken,
      new_password: newPassword,
    });
  }

  // Cambia la contraseña del usuario autenticado. Exige la contraseña actual.
  // No renueva la sesión: el backend mantiene válida la sesión en curso.
  changePassword(currentPassword: string, newPassword: string): Observable<MessageResponse> {
    return this.http.post<MessageResponse>(`${this.API}/change-password`, {
      current_password: currentPassword,
      new_password: newPassword,
    });
  }

  refreshToken(): Observable<AccessTokenResponse> {
    const refreshToken = this.tokenService.getRefreshToken();
    if (!refreshToken) {
      throw new Error('No hay refresh token disponible.');
    }

    return this.http
      .post<AccessTokenResponse>(`${this.API}/refresh`, { refresh_token: refreshToken })
      .pipe(
        tap(response => {
          this.tokenService.setAccessToken(response.access_token);
          this._currentUser.set(this.tokenService.decodeToken());
        })
      );
  }

  logout(): void {
    this.sessionActivity.stop();
    this.tokenService.removeTokens();
    this._currentUser.set(null);
    void this.router.navigate(['/login']);
  }

  // ── Control de acceso ──────────────────────────────────────────────────────
  hasRole(roles: Role | Role[]): boolean {
    const role = this.currentRole();
    if (!role) return false;
    return Array.isArray(roles) ? roles.includes(role) : role === roles;
  }

  hasPermission(permission: Permission): boolean {
    const role = this.currentRole();
    if (!role) return false;
    return ROLE_PERMISSIONS[role].includes(permission);
  }

  getDefaultRoute(): string {
    return this.currentRole() === 'limpiadora' ? '/cleaning-organization' : '/calendar';
  }

  // ── Restaurar sesión desde localStorage ───────────────────────────────────
  private loadUserFromToken(): User | null {
    if (!this.tokenService.isValid()) {
      this.tokenService.removeTokens();
      return null;
    }
    this.sessionActivity.start(() => this.logout());
    return this.tokenService.decodeToken();
  }
}
