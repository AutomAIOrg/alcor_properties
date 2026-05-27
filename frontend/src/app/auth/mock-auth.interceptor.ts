import { HttpInterceptorFn, HttpResponse } from '@angular/common/http';
import { of, throwError } from 'rxjs';
import { delay } from 'rxjs/operators';
import { Role } from '../models/user.model';

interface MockUser {
  sub: string;
  username: string;
  password: string;
  name: string;
  role: Role;
}

const MOCK_USERS: MockUser[] = [
  { sub: '1', username: 'admin', password: 'admin123', name: 'GUIRUFO', role: 'admin' },
  { sub: '2', username: 'employee', password: 'emp123', name: 'Employee User', role: 'employee' },
  { sub: '3', username: 'viewer', password: 'view123', name: 'Viewer User', role: 'viewer' },
];

function base64url(obj: object): string {
  return btoa(JSON.stringify(obj)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
}

function generateMockJwt(user: MockUser): string {
  const header = base64url({ alg: 'HS256', typ: 'JWT' });
  const iat = Math.floor(Date.now() / 1000);
  const exp = iat + 8 * 60 * 60; // 8 horas
  const payload = base64url({
    sub: user.sub,
    username: user.username,
    name: user.name,
    role: user.role,
    iat,
    exp,
  });
  return `${header}.${payload}.mock_signature`;
}

/**
 * MOCK INTERCEPTOR — intercepta POST /api/auth/login con usuarios hardcodeados.
 * Para conectar el backend real: eliminar este interceptor de app.config.ts.
 * El resto del sistema (AuthService, TokenService, guards) no requiere cambios.
 */
export const mockAuthInterceptor: HttpInterceptorFn = (req, next) => {
  if (req.method === 'POST' && req.url.includes('/api/auth/login')) {
    const { username, password } = req.body as { username: string; password: string };
    const user = MOCK_USERS.find(u => u.username === username && u.password === password);

    if (!user) {
      return throwError(() => ({
        status: 401,
        error: { detail: 'Credenciales incorrectas.' },
      })).pipe(delay(400));
    }

    const response = new HttpResponse({
      status: 200,
      body: {
        access_token: generateMockJwt(user),
        token_type: 'bearer',
        expires_in: 28800,
        role: user.role,
      },
    });

    return of(response).pipe(delay(400));
  }

  return next(req);
};
