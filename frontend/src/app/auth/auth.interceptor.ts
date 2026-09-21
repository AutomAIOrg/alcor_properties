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

  const isRefreshRequest = req.url.includes('/api/v1/auth/refresh');
  const isAuthRequest = req.url.includes('/api/v1/auth/login') || isRefreshRequest;
  const token = tokenService.getAccessToken();

  const authReq =
    token && !isAuthRequest ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } }) : req;

  return next(authReq).pipe(
    catchError((error: HttpErrorResponse) => {
      if (error.status !== 401) {
        return throwError(() => error);
      }

      // Refresh errors belong to its caller. A late failure must not log out a new login.
      if (isRefreshRequest || (!isAuthRequest && tokenService.getAccessToken() !== token)) {
        return throwError(() => error);
      }

      if (isAuthRequest || sessionActivity.isIdleExpired() || !tokenService.getRefreshToken()) {
        authService.logout();
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
        catchError(refreshError => {
          if (tokenService.getAccessToken() === token) authService.logout();
          return throwError(() => refreshError);
        }),
        switchMap(accessToken =>
          next(req.clone({ setHeaders: { Authorization: `Bearer ${accessToken}` } })).pipe(
            catchError(error => {
              if (error.status === 401 && tokenService.getAccessToken() === accessToken) {
                authService.logout();
              }
              return throwError(() => error);
            })
          )
        )
      );
    })
  );
};
