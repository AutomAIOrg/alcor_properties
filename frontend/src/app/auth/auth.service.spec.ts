import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import { AuthService } from './auth.service';
import { TokenService } from './token.service';
import { AuthRequest, AuthResponse } from '../models/auth.model';
import { User, Role, Permission } from '../models/user.model';
import { ROLE_PERMISSIONS } from '../config/permissions.config';

// ─── Fixture helpers ──────────────────────────────────────────────────────────

const roles = Object.keys(ROLE_PERMISSIONS) as Role[];

const primaryRole = roles[0];
const limitedRole: Role = roles.includes('viewer') ? 'viewer' : primaryRole;
const secondaryRole = roles.find(role => role !== primaryRole) ?? ('__OTHER_ROLE__' as Role);

const primaryPermission = ROLE_PERMISSIONS[primaryRole][0] as Permission;
const deniedPermission: Permission = 'admin:access';

function makeUser(overrides: Partial<User> = {}): User {
  return {
    sub: 'user-1',
    username: 'ana@test.com',
    name: 'Ana García',
    role: primaryRole,
    exp: 4102444800,
    iat: 1735689600,
    ...overrides,
  };
}

function makeCredentials(overrides: Partial<AuthRequest> = {}): AuthRequest {
  return {
    username: 'ana@test.com',
    password: 'secret123',
    ...overrides,
  } as AuthRequest;
}

function makeAuthResponse(overrides: Partial<AuthResponse> = {}): AuthResponse {
  return {
    access_token: 'fake.jwt.token',
    ...overrides,
  } as AuthResponse;
}

type SetupOptions = {
  tokenValid?: boolean;
  decodedUser?: User | null;
  clearInitialCalls?: boolean;
};

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('AuthService', () => {
  let service: AuthService;
  let httpMock: HttpTestingController | undefined;
  let tokenServiceSpy: jest.Mocked<TokenService>;
  let routerSpy: jest.Mocked<Router>;

  function setup(options: SetupOptions = {}) {
    const { tokenValid = false, decodedUser = null, clearInitialCalls = true } = options;

    TestBed.resetTestingModule();

    tokenServiceSpy = {
      setToken: jest.fn(),
      removeToken: jest.fn(),
      decodeToken: jest.fn().mockReturnValue(decodedUser),
      isValid: jest.fn().mockReturnValue(tokenValid),
    } as unknown as jest.Mocked<TokenService>;

    routerSpy = {
      navigate: jest.fn().mockResolvedValue(true),
    } as unknown as jest.Mocked<Router>;

    TestBed.configureTestingModule({
      providers: [
        AuthService,
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: tokenServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    });

    service = TestBed.inject(AuthService);
    httpMock = TestBed.inject(HttpTestingController);

    // AuthService ejecuta loadUserFromToken() al construirse.
    // En la mayoría de tests no queremos contar esas llamadas iniciales.
    if (clearInitialCalls) {
      jest.clearAllMocks();
    }

    return {
      service,
      httpMock,
      tokenServiceSpy,
      routerSpy,
    };
  }

  afterEach(() => {
    httpMock?.verify();
  });

  // ── A: Inicialización / restaurar sesión ────────────────────────────────────

  describe('A — inicialización', () => {
    it('si el token no es válido, elimina el token y deja currentUser en null', () => {
      setup({
        tokenValid: false,
        clearInitialCalls: false,
      });

      expect(tokenServiceSpy.isValid).toHaveBeenCalledTimes(1);
      expect(tokenServiceSpy.removeToken).toHaveBeenCalledTimes(1);
      expect(tokenServiceSpy.decodeToken).not.toHaveBeenCalled();

      expect(service.currentUser()).toBeNull();
      expect(service.isAuthenticated()).toBe(false);
      expect(service.currentRole()).toBeNull();
    });

    it('si el token es válido, restaura el usuario desde decodeToken', () => {
      const user = makeUser();

      setup({
        tokenValid: true,
        decodedUser: user,
        clearInitialCalls: false,
      });

      expect(tokenServiceSpy.isValid).toHaveBeenCalledTimes(1);
      expect(tokenServiceSpy.decodeToken).toHaveBeenCalledTimes(1);
      expect(tokenServiceSpy.removeToken).not.toHaveBeenCalled();

      expect(service.currentUser()).toEqual(user);
      expect(service.isAuthenticated()).toBe(true);
      expect(service.currentRole()).toBe(user.role);
    });
  });

  // ── B: Login ────────────────────────────────────────────────────────────────

  describe('B — login', () => {
    it('hace POST a /api/auth/login con las credenciales recibidas', () => {
      setup();

      const credentials = makeCredentials();

      service.login(credentials).subscribe();

      const req = httpMock!.expectOne('/api/auth/login');

      expect(req.request.method).toBe('POST');
      expect(req.request.body).toEqual(credentials);

      req.flush(makeAuthResponse());
    });

    it('devuelve la respuesta AuthResponse al suscriptor', () => {
      setup();

      const credentials = makeCredentials();
      const authResponse = makeAuthResponse({
        access_token: 'jwt.from.backend',
      });

      let result: AuthResponse | undefined;

      service.login(credentials).subscribe(response => {
        result = response;
      });

      const req = httpMock!.expectOne('/api/auth/login');
      req.flush(authResponse);

      expect(result).toEqual(authResponse);
    });

    it('guarda el access_token recibido en TokenService', () => {
      setup();

      const credentials = makeCredentials();
      const authResponse = makeAuthResponse({
        access_token: 'jwt.to.save',
      });

      service.login(credentials).subscribe();

      const req = httpMock!.expectOne('/api/auth/login');
      req.flush(authResponse);

      expect(tokenServiceSpy.setToken).toHaveBeenCalledTimes(1);
      expect(tokenServiceSpy.setToken).toHaveBeenCalledWith('jwt.to.save');
    });

    it('actualiza currentUser usando decodeToken después del login', () => {
      setup();

      const user = makeUser({
        name: 'Usuario Login',
        role: primaryRole,
      });

      tokenServiceSpy.decodeToken.mockReturnValue(user);

      service.login(makeCredentials()).subscribe();

      const req = httpMock!.expectOne('/api/auth/login');
      req.flush(makeAuthResponse());

      expect(tokenServiceSpy.decodeToken).toHaveBeenCalledTimes(1);
      expect(service.currentUser()).toEqual(user);
      expect(service.isAuthenticated()).toBe(true);
      expect(service.currentRole()).toBe(user.role);
    });

    it('antes de recibir respuesta HTTP, no modifica el estado de autenticación', () => {
      setup();

      service.login(makeCredentials()).subscribe();

      httpMock!.expectOne('/api/auth/login');

      expect(tokenServiceSpy.setToken).not.toHaveBeenCalled();
      expect(tokenServiceSpy.decodeToken).not.toHaveBeenCalled();
      expect(service.currentUser()).toBeNull();
      expect(service.isAuthenticated()).toBe(false);
    });

    it('login no navega automáticamente a ninguna ruta', () => {
      setup();

      service.login(makeCredentials()).subscribe();

      const req = httpMock!.expectOne('/api/auth/login');
      req.flush(makeAuthResponse());

      expect(routerSpy.navigate).not.toHaveBeenCalled();
    });
  });

  // ── C: Logout ───────────────────────────────────────────────────────────────

  describe('C — logout', () => {
    it('elimina el token, limpia currentUser y navega a /login', () => {
      const user = makeUser();

      setup({
        tokenValid: true,
        decodedUser: user,
      });

      expect(service.currentUser()).toEqual(user);
      expect(service.isAuthenticated()).toBe(true);

      service.logout();

      expect(tokenServiceSpy.removeToken).toHaveBeenCalledTimes(1);
      expect(service.currentUser()).toBeNull();
      expect(service.isAuthenticated()).toBe(false);
      expect(service.currentRole()).toBeNull();

      expect(routerSpy.navigate).toHaveBeenCalledTimes(1);
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);
    });
  });

  // ── D: hasRole ──────────────────────────────────────────────────────────────

  describe('D — hasRole', () => {
    it('devuelve false si no hay usuario autenticado', () => {
      setup();

      expect(service.hasRole(primaryRole)).toBe(false);
    });

    it('devuelve true si el usuario tiene el rol indicado', () => {
      setup({
        tokenValid: true,
        decodedUser: makeUser({ role: primaryRole }),
      });

      expect(service.hasRole(primaryRole)).toBe(true);
    });

    it('devuelve false si el usuario no tiene el rol indicado', () => {
      setup({
        tokenValid: true,
        decodedUser: makeUser({ role: primaryRole }),
      });

      expect(service.hasRole(secondaryRole)).toBe(false);
    });

    it('devuelve true si el rol del usuario está dentro del array de roles permitidos', () => {
      setup({
        tokenValid: true,
        decodedUser: makeUser({ role: primaryRole }),
      });

      expect(service.hasRole([secondaryRole, primaryRole])).toBe(true);
    });

    it('devuelve false si el rol del usuario no está dentro del array de roles permitidos', () => {
      setup({
        tokenValid: true,
        decodedUser: makeUser({ role: primaryRole }),
      });

      expect(service.hasRole([secondaryRole])).toBe(false);
    });
  });

  // ── E: hasPermission ────────────────────────────────────────────────────────

  describe('E — hasPermission', () => {
    it('devuelve false si no hay usuario autenticado', () => {
      setup();

      expect(service.hasPermission(primaryPermission)).toBe(false);
    });

    it('devuelve true si el rol actual contiene el permiso', () => {
      setup({
        tokenValid: true,
        decodedUser: makeUser({ role: primaryRole }),
      });

      expect(primaryPermission).toBeDefined();
      expect(service.hasPermission(primaryPermission)).toBe(true);
    });

    it('devuelve false si el rol actual no contiene el permiso', () => {
      setup({
        tokenValid: true,
        decodedUser: makeUser({ role: limitedRole }),
      });

      expect(ROLE_PERMISSIONS[limitedRole]).not.toContain(deniedPermission);
      expect(service.hasPermission(deniedPermission)).toBe(false);
    });
  });

  // ── F: Estado reactivo ──────────────────────────────────────────────────────

  describe('F — signals / computed', () => {
    it('isAuthenticated depende de currentUser', () => {
      setup();

      expect(service.currentUser()).toBeNull();
      expect(service.isAuthenticated()).toBe(false);

      tokenServiceSpy.decodeToken.mockReturnValue(makeUser());

      service.login(makeCredentials()).subscribe();

      const req = httpMock!.expectOne('/api/auth/login');
      req.flush(makeAuthResponse());

      expect(service.currentUser()).not.toBeNull();
      expect(service.isAuthenticated()).toBe(true);
    });

    it('currentRole devuelve null si no hay usuario', () => {
      setup();

      expect(service.currentRole()).toBeNull();
    });

    it('currentRole devuelve el rol del usuario autenticado', () => {
      const user = makeUser({ role: primaryRole });

      setup({
        tokenValid: true,
        decodedUser: user,
      });

      expect(service.currentRole()).toBe(primaryRole);
    });
  });
});
