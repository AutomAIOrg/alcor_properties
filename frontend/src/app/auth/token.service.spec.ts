import { TestBed } from '@angular/core/testing';

import { TokenService } from './token.service';

function makeJwt(payload: object): string {
  const encodedPayload = btoa(JSON.stringify(payload))
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=+$/g, '');

  return `e30.${encodedPayload}.signature`;
}

describe('TokenService', () => {
  let service: TokenService;

  beforeEach(() => {
    localStorage.clear();

    TestBed.configureTestingModule({
      providers: [TokenService],
    });

    service = TestBed.inject(TokenService);
  });

  afterEach(() => {
    localStorage.clear();
  });

  it('guarda y recupera access y refresh tokens por separado', () => {
    service.setTokens('access-token', 'refresh-token');

    expect(service.getAccessToken()).toBe('access-token');
    expect(service.getRefreshToken()).toBe('refresh-token');
  });

  it('removeTokens elimina access, refresh y token legacy', () => {
    localStorage.setItem('auth_token', 'legacy-token');
    service.setTokens('access-token', 'refresh-token');

    service.removeTokens();

    expect(service.getAccessToken()).toBeNull();
    expect(service.getRefreshToken()).toBeNull();
    expect(localStorage.getItem('auth_token')).toBeNull();
  });

  it('decodeToken decodifica el access token', () => {
    service.setAccessToken(
      makeJwt({
        sub: '1',
        username: 'admin',
        name: 'Admin',
        role: 'admin',
        iat: 1735689600,
        exp: 4102444800,
      })
    );

    expect(service.decodeToken()).toEqual({
      sub: '1',
      username: 'admin',
      name: 'Admin',
      role: 'admin',
      iat: 1735689600,
      exp: 4102444800,
    });
  });

  it('isValid devuelve false cuando el access token ha expirado', () => {
    service.setAccessToken(
      makeJwt({
        exp: 1,
      })
    );

    expect(service.isValid()).toBe(false);
  });
});
