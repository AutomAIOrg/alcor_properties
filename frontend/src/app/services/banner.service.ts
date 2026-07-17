import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { environment } from '../../environments/environment';

export interface BannerSetting {
  enabled: boolean;
}

/**
 * Estado global del banner de avisos. El interruptor lo controla la cuenta de desarrollo
 * y el valor se persiste en el backend, por lo que afecta a todos los usuarios.
 */
@Injectable({ providedIn: 'root' })
export class BannerService {
  private http = inject(HttpClient);
  private readonly API = `${environment.apiUrl}/api/v1/settings/banner`;

  private _enabled = signal(false);
  /** Si el banner está activado globalmente. Arranca en false hasta que se carga del backend. */
  enabled = this._enabled.asReadonly();

  /** Carga el estado del banner desde el backend. Ante cualquier error, lo deja oculto. */
  load(): void {
    this.http.get<BannerSetting>(this.API).subscribe({
      next: setting => this._enabled.set(setting.enabled),
      error: () => this._enabled.set(false),
    });
  }

  /** Activa o desactiva el banner de forma global (solo lo permite la cuenta de desarrollo). */
  setEnabled(enabled: boolean): Observable<BannerSetting> {
    return this.http
      .put<BannerSetting>(this.API, { enabled })
      .pipe(tap(setting => this._enabled.set(setting.enabled)));
  }
}
