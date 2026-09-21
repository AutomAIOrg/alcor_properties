import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router } from '@angular/router';
import { AuthService } from './auth.service';
import { TokenService } from './token.service';
import { SessionActivityService } from './session-activity.service';
import { authInterceptor } from './auth.interceptor';

function access(sid: string): string {
  const claims = { sub: '1', sid, username: 'admin', role: 'admin', exp: 4102444800 };
  return `${btoa('{}')}.${btoa(JSON.stringify(claims))}.signature`;
}

describe('authentication responses after session changes', () => {
  let auth: AuthService;
  let tokens: TokenService;
  let http: HttpClient;
  let httpMock: HttpTestingController;
  const router = { navigate: jest.fn().mockResolvedValue(true) };

  beforeEach(() => {
    localStorage.clear();
    jest.clearAllMocks();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        { provide: Router, useValue: router },
        {
          provide: SessionActivityService,
          useValue: {
            start: jest.fn(),
            stop: jest.fn(),
            recordActivity: jest.fn(),
            isIdleExpired: jest.fn().mockReturnValue(false),
          },
        },
      ],
    });
    tokens = TestBed.inject(TokenService);
    tokens.setTokens(access('old-session'), 'old-refresh');
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
    localStorage.clear();
  });

  function login(): void {
    auth.login({ username: 'admin', password: 'password' }).subscribe();
    httpMock.expectOne('/api/v1/auth/login').flush({
      access_token: access('new-session'),
      refresh_token: 'new-refresh',
      token_type: 'bearer',
    });
  }

  it.each(['logout', 'login', 'another tab'])(
    'discards a late refresh success after %s without retrying the old request',
    action => {
      const next = jest.fn();
      const complete = jest.fn();
      http.get('/api/v1/bookings/').subscribe({ next, complete });
      httpMock
        .expectOne('/api/v1/bookings/')
        .flush({}, { status: 401, statusText: 'Unauthorized' });
      const refresh = httpMock.expectOne('/api/v1/auth/refresh');
      if (action === 'logout') {
        auth.logout();
        // Also works when composed with the server-side logout branch.
        httpMock.match('/api/v1/auth/logout').forEach(req => req.flush({ message: 'ok' }));
      } else if (action === 'login') {
        login();
      } else {
        tokens.setTokens(access('new-session'), 'new-refresh');
      }
      refresh.flush({ access_token: access('old-session'), refresh_token: 'late-refresh' });
      expect(tokens.getRefreshToken()).toBe(action === 'logout' ? null : 'new-refresh');
      expect(next).not.toHaveBeenCalled();
      expect(complete).toHaveBeenCalledTimes(1);
      httpMock.expectNone('/api/v1/bookings/');
    }
  );

  it('does not log out the new login when an old refresh fails', () => {
    const error = jest.fn();
    http.get('/api/v1/bookings/').subscribe({ error });
    httpMock.expectOne('/api/v1/bookings/').flush({}, { status: 401, statusText: 'Unauthorized' });
    const refresh = httpMock.expectOne('/api/v1/auth/refresh');
    login();
    refresh.flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(tokens.getRefreshToken()).toBe('new-refresh');
    expect(auth.currentUser()?.sid).toBe('new-session');
    expect(router.navigate).not.toHaveBeenCalled();
    expect(error).not.toHaveBeenCalled();
  });

  it('does not refresh an old resource request using a different login', () => {
    http.get('/api/v1/bookings/').subscribe({ error: () => undefined });
    const request = httpMock.expectOne('/api/v1/bookings/');
    login();
    request.flush({}, { status: 401, statusText: 'Unauthorized' });
    httpMock.expectNone('/api/v1/auth/refresh');
    expect(tokens.getRefreshToken()).toBe('new-refresh');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('discards a queued refresh after a new login acquires a different session', async () => {
    const descriptor = Object.getOwnPropertyDescriptor(navigator, 'locks');
    let run!: () => Promise<unknown>;
    let release!: (value: unknown) => void;
    Object.defineProperty(navigator, 'locks', {
      configurable: true,
      value: {
        request: jest.fn((_name: string, callback: () => Promise<unknown>) => {
          run = callback;
          return new Promise(resolve => {
            release = resolve;
          });
        }),
      },
    });
    try {
      const next = jest.fn();
      const completed = new Promise<void>((resolve, reject) => {
        auth.refreshToken().subscribe({ next, complete: resolve, error: reject });
      });
      login();
      release(await run());
      await completed;
      httpMock.expectNone('/api/v1/auth/refresh');
      expect(next).not.toHaveBeenCalled();
      expect(tokens.getRefreshToken()).toBe('new-refresh');
    } finally {
      if (descriptor) Object.defineProperty(navigator, 'locks', descriptor);
      else Reflect.deleteProperty(navigator, 'locks');
    }
  });
});
