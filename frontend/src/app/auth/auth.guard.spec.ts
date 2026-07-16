import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';

import { authGuard, initialPasswordGuard, permissionGuard } from './auth.guard';
import { AuthService } from './auth.service';

describe('authGuard', () => {
  let authServiceSpy: jest.Mocked<AuthService>;
  let routerSpy: jest.Mocked<Router>;

  function runGuard(guard = authGuard) {
    return TestBed.runInInjectionContext(() => guard({} as never, {} as never));
  }

  beforeEach(() => {
    authServiceSpy = {
      isAuthenticated: jest.fn().mockReturnValue(false),
      mustChangePassword: jest.fn().mockReturnValue(false),
      hasPermission: jest.fn().mockReturnValue(false),
      getDefaultRoute: jest.fn().mockReturnValue('/calendar'),
    } as unknown as jest.Mocked<AuthService>;

    routerSpy = {
      createUrlTree: jest.fn((paths: string[]) => ({ paths })),
    } as unknown as jest.Mocked<Router>;

    TestBed.configureTestingModule({
      providers: [
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    });
  });

  it('authGuard permite continuar si el usuario está autenticado', () => {
    authServiceSpy.isAuthenticated.mockReturnValue(true);

    expect(runGuard()).toBe(true);
  });

  it('authGuard redirige a login si no hay usuario autenticado', () => {
    expect(runGuard()).toEqual({ paths: ['/login'] });
  });

  it('authGuard redirige al cambio de contraseña si el usuario tiene la inicial', () => {
    authServiceSpy.isAuthenticated.mockReturnValue(true);
    authServiceSpy.mustChangePassword.mockReturnValue(true);

    expect(runGuard()).toEqual({ paths: ['/change-initial-password'] });
  });

  it('initialPasswordGuard permite continuar si el cambio está pendiente', () => {
    authServiceSpy.isAuthenticated.mockReturnValue(true);
    authServiceSpy.mustChangePassword.mockReturnValue(true);

    expect(runGuard(initialPasswordGuard)).toBe(true);
  });

  it('initialPasswordGuard redirige a la ruta por defecto si no hay cambio pendiente', () => {
    authServiceSpy.isAuthenticated.mockReturnValue(true);
    authServiceSpy.mustChangePassword.mockReturnValue(false);

    expect(runGuard(initialPasswordGuard)).toEqual({ paths: ['/calendar'] });
  });

  it('initialPasswordGuard redirige a login si no hay usuario autenticado', () => {
    expect(runGuard(initialPasswordGuard)).toEqual({ paths: ['/login'] });
  });

  it('permissionGuard permite continuar si el usuario tiene el permiso requerido', () => {
    authServiceSpy.isAuthenticated.mockReturnValue(true);
    authServiceSpy.hasPermission.mockReturnValue(true);

    expect(runGuard(permissionGuard('cleaning:access'))).toBe(true);
  });

  it('permissionGuard redirige a login si el usuario no está autenticado', () => {
    expect(runGuard(permissionGuard('cleaning:access'))).toEqual({ paths: ['/login'] });
  });

  it('permissionGuard redirige a la ruta por defecto del rol si falta el permiso', () => {
    authServiceSpy.isAuthenticated.mockReturnValue(true);
    authServiceSpy.hasPermission.mockReturnValue(false);
    authServiceSpy.getDefaultRoute.mockReturnValue('/cleaning-organization');

    expect(runGuard(permissionGuard('calendar:access'))).toEqual({
      paths: ['/cleaning-organization'],
    });
  });
});
