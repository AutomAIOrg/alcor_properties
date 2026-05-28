import { TestBed } from '@angular/core/testing';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { of, Subject, throwError } from 'rxjs';

import { authInterceptor } from './auth.interceptor';
import { AuthService } from './auth.service';
import { TokenService } from './token.service';
import { SessionActivityService } from './session-activity.service';
import { AccessTokenResponse } from '../models/auth.model';

describe('authInterceptor', () => {
  let http: HttpClient;
  let httpMock: HttpTestingController;
  let tokenServiceSpy: jest.Mocked<TokenService>;
  let authServiceSpy: jest.Mocked<AuthService>;
  let sessionActivitySpy: jest.Mocked<SessionActivityService>;

  beforeEach(() => {
    tokenServiceSpy = {
      getAccessToken: jest.fn().mockReturnValue('access-token'),
      getRefreshToken: jest.fn().mockReturnValue('refresh-token'),
    } as unknown as jest.Mocked<TokenService>;

    authServiceSpy = {
      refreshToken: jest
        .fn()
        .mockReturnValue(of({ access_token: 'new-token', token_type: 'bearer' })),
      logout: jest.fn(),
    } as unknown as jest.Mocked<AuthService>;

    sessionActivitySpy = {
      isIdleExpired: jest.fn().mockReturnValue(false),
    } as unknown as jest.Mocked<SessionActivityService>;

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: TokenService, useValue: tokenServiceSpy },
        { provide: AuthService, useValue: authServiceSpy },
        { provide: SessionActivityService, useValue: sessionActivitySpy },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('añade Authorization con el access token en requests normales', () => {
    http.get('/api/v1/bookings/').subscribe();

    const req = httpMock.expectOne('/api/v1/bookings/');
    expect(req.request.headers.get('Authorization')).toBe('Bearer access-token');
    req.flush([]);
  });

  it('no añade Authorization a login ni refresh', () => {
    http.post('/api/v1/auth/login', {}).subscribe();

    const loginReq = httpMock.expectOne('/api/v1/auth/login');
    expect(loginReq.request.headers.has('Authorization')).toBe(false);
    loginReq.flush({
      access_token: 'access-token',
      refresh_token: 'refresh-token',
      token_type: 'bearer',
    });
  });

  it('ante 401 refresca el access token y reintenta la request original', () => {
    http.get('/api/v1/bookings/').subscribe(response => {
      expect(response).toEqual([{ id: 1 }]);
    });

    const firstReq = httpMock.expectOne('/api/v1/bookings/');
    firstReq.flush({ detail: 'Token expirado' }, { status: 401, statusText: 'Unauthorized' });

    const retryReq = httpMock.expectOne('/api/v1/bookings/');
    expect(retryReq.request.headers.get('Authorization')).toBe('Bearer new-token');
    retryReq.flush([{ id: 1 }]);

    expect(authServiceSpy.refreshToken).toHaveBeenCalledTimes(1);
    expect(authServiceSpy.logout).not.toHaveBeenCalled();
  });

  it('si la sesión está inactiva, hace logout sin refrescar', () => {
    sessionActivitySpy.isIdleExpired.mockReturnValue(true);

    http.get('/api/v1/bookings/').subscribe({
      error: error => expect(error.status).toBe(401),
    });

    const req = httpMock.expectOne('/api/v1/bookings/');
    req.flush({ detail: 'Token expirado' }, { status: 401, statusText: 'Unauthorized' });

    expect(authServiceSpy.refreshToken).not.toHaveBeenCalled();
    expect(authServiceSpy.logout).toHaveBeenCalledTimes(1);
  });

  it('si refresh falla, hace logout', () => {
    authServiceSpy.refreshToken.mockReturnValue(
      throwError(() => ({ status: 401, statusText: 'Unauthorized' }))
    );

    http.get('/api/v1/bookings/').subscribe({
      error: error => expect(error.status).toBe(401),
    });

    const req = httpMock.expectOne('/api/v1/bookings/');
    req.flush({ detail: 'Token expirado' }, { status: 401, statusText: 'Unauthorized' });

    expect(authServiceSpy.logout).toHaveBeenCalledTimes(1);
  });

  it('comparte un único refresh para 401 concurrentes', () => {
    const refreshSubject = new Subject<AccessTokenResponse>();
    authServiceSpy.refreshToken.mockReturnValue(refreshSubject.asObservable());

    http.get('/api/v1/bookings/active').subscribe();
    http.get('/api/v1/bookings/upcoming-checkouts').subscribe();

    const activeReq = httpMock.expectOne('/api/v1/bookings/active');
    const checkoutsReq = httpMock.expectOne('/api/v1/bookings/upcoming-checkouts');

    activeReq.flush({ detail: 'Token expirado' }, { status: 401, statusText: 'Unauthorized' });
    checkoutsReq.flush({ detail: 'Token expirado' }, { status: 401, statusText: 'Unauthorized' });

    expect(authServiceSpy.refreshToken).toHaveBeenCalledTimes(1);

    refreshSubject.next({ access_token: 'shared-new-token', token_type: 'bearer' });
    refreshSubject.complete();

    const retries = httpMock.match(req =>
      ['/api/v1/bookings/active', '/api/v1/bookings/upcoming-checkouts'].includes(req.url)
    );
    expect(retries).toHaveLength(2);
    retries.forEach(req => {
      expect(req.request.headers.get('Authorization')).toBe('Bearer shared-new-token');
      req.flush([]);
    });
  });
});
