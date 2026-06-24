import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { permissionGuard } from './auth/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    loadComponent: () => import('./pages/logging/logging.component').then(m => m.LoggingComponent),
  },
  {
    path: 'calendar',
    loadComponent: () =>
      import('./pages/calendar/calendar.component').then(m => m.CalendarComponent),
    canActivate: [authGuard, permissionGuard('calendar:access')],
  },
  {
    path: 'cleaning-organization',
    loadComponent: () =>
      import('./pages/cleaning-organization/cleaning-organization.component').then(
        m => m.CleaningOrganizationComponent
      ),
    canActivate: [authGuard, permissionGuard('cleaning:access')],
  },
  {
    path: 'searches',
    loadComponent: () =>
      import('./pages/searches/searches.component').then(m => m.SearchesComponent),
    canActivate: [authGuard, permissionGuard('searches:access')],
  },
  {
    path: 'bills',
    loadComponent: () => import('./pages/bills/bills.component').then(m => m.BillsComponent),
    canActivate: [authGuard, permissionGuard('bills:access')],
  },
  {
    path: 'admin',
    loadComponent: () => import('./pages/admin/admin.component').then(m => m.AdminComponent),
    canActivate: [authGuard, permissionGuard('admin:access')],
  },
  { path: '', redirectTo: 'login', pathMatch: 'full' },
  { path: '**', redirectTo: 'login' },
];
