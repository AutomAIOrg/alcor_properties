import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { Permission } from '../models/user.model';

export const CHANGE_INITIAL_PASSWORD_ROUTE = '/change-initial-password';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) return router.createUrlTree(['/login']);

  // Con la contraseña inicial no se accede a nada más que a la pantalla de cambio.
  if (auth.mustChangePassword()) return router.createUrlTree([CHANGE_INITIAL_PASSWORD_ROUTE]);

  return true;
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

/**
 * Protege la pantalla de cambio de la contraseña inicial: solo es accesible
 * mientras el usuario tenga pendiente el cambio.
 */
export const initialPasswordGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);

  if (!auth.isAuthenticated()) return router.createUrlTree(['/login']);

  if (!auth.mustChangePassword()) return router.createUrlTree([auth.getDefaultRoute()]);

  return true;
};
