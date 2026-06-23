import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { Permission } from '../models/user.model';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (auth.isAuthenticated()) return true;

  return router.createUrlTree(['/login']);
};

export const permissionGuard =
  (permission: Permission): CanActivateFn =>
  () => {
    const auth = inject(AuthService);
    const router = inject(Router);

    if (auth.isAuthenticated() && auth.hasPermission(permission)) return true;

    // Autenticado pero sin permiso -> volver a la vista principal de su rol
    if (auth.isAuthenticated()) return router.createUrlTree([auth.getDefaultRoute()]);

    return router.createUrlTree(['/login']);
  };
