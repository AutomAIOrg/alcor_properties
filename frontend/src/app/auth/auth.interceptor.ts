import { HttpInterceptorFn, HttpErrorResponse } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, finalize, map, Observable, shareReplay, switchMap, throwError } from 'rxjs';
import { TokenService } from './token.service';
import { AuthService } from './auth.service';
import { SessionActivityService } from './session-activity.service';

let refreshInProgress$: Observable<string> | null = null;

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const tokenService = inject(TokenService);
  const authService = inject(AuthService);
  const sessionActivity = inject(SessionActivityService);

  const isAuthRequest =
    req.url.includes('/api/v1/auth/login') ||
    req.url.includes('/api/v1/auth/refresh') ||
    req.url.includes('/api/v1/auth/logout');
  const token = tokenService.getAccessToken();

  const authReq =
    token && !isAuthRequest ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401) {
        return throwError(() => error);
      }

      // Logout ya limpia la sesión local; no reentrar en logout() ante su propio 401.
      if (
        req.url.includes('/api/v1/auth/logout') ||
        isAuthRequest ||
        sessionActivity.isIdleExpired() ||
        !tokenService.getRefreshToken()
      ) {
        if (!req.url.includes('/api/v1/auth/logout')) {
          authService.logout();
        }
        return throwError(() => error);
      }

      refreshInProgress$ ??= authService.refreshToken().pipe(
        map(response => response.access_token),
        finalize(() => {
          refreshInProgress$ = null;
        }),
        shareReplay({ bufferSize: 1, refCount: false })
      );

      return refreshInProgress$.pipe(
        switchMap(accessToken =>
          next(req.clone({ setHeaders: { Authorization: `Bearer ${accessToken}` } }))
        ),
        catchError(refreshError => {
          authService.logout();
          return throwError(() => refreshError);
        })
      );
    })
  );
};
