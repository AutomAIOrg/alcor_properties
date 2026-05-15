import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: 'calendar',
    loadComponent: () => import('./pages/calendar/calendar.component')
      .then(m => m.CalendarComponent)
  },
  {
    path: 'searches',
    loadComponent: () => import('./pages/searches/searches.component')
      .then(m => m.SearchesComponent)
  },
  { path: '', redirectTo: 'calendar', pathMatch: 'full' },
];
