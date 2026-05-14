import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { permissionGuard } from './auth/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/logging/logging.component')
      .then(m => m.LoggingComponent)
  },
  {
    path: 'calendar',
    loadComponent: () => import('./pages/calendar/calendar.component')
      .then(m => m.CalendarComponent),
    canActivate: [authGuard]
  },
  {
    path: 'searches',
    loadComponent: () => import('./pages/searches/searches.component')
      .then(m => m.SearchesComponent),
    canActivate: [authGuard, permissionGuard('searches:access')]
  },
  { path: '',   redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' },
];
