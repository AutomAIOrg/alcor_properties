import { ApplicationConfig, provideZoneChangeDetection, LOCALE_ID } from '@angular/core';
import { provideRouter } from '@angular/router';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { registerLocaleData } from '@angular/common';
import localeEs from '@angular/common/locales/es';

import { routes } from './app.routes';
import { mockAuthInterceptor } from './auth/mock-auth.interceptor';
import { authInterceptor } from './auth/auth.interceptor';

registerLocaleData(localeEs);

export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({ eventCoalescing: true }),
    provideRouter(routes),
    provideHttpClient(
      withInterceptors([
        mockAuthInterceptor, // ELIMINAR cuando el backend esté listo
        authInterceptor,
      ])
    ),
    { provide: LOCALE_ID, useValue: 'es' }
  ]
};
