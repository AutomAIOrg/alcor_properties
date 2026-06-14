import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { AppComponent } from './app.component';
import { AuthService } from './auth/auth.service';
import { Permission, User } from './models/user.model';

@Component({
  standalone: true,
  template: '',
})
class StubRouteComponent {}

function makeUser(overrides: Partial<User> = {}): User {
  return {
    sub: 'user-1',
    username: 'cleaner@test.com',
    name: 'Cleaner',
    role: 'limpiadora',
    exp: 4102444800,
    iat: 1735689600,
    ...overrides,
  };
}

describe('AppComponent', () => {
  let fixture: ComponentFixture<AppComponent>;
  let authServiceSpy: jest.Mocked<AuthService>;
  let permissions: Set<Permission>;
  let currentUser: User | null;

  function setup(): void {
    authServiceSpy = {
      currentUser: jest.fn(() => currentUser),
      hasPermission: jest.fn((permission: Permission) => permissions.has(permission)),
      logout: jest.fn(),
    } as unknown as jest.Mocked<AuthService>;

    TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [
        provideRouter([
          { path: 'calendar', component: StubRouteComponent },
          { path: 'cleaning-organization', component: StubRouteComponent },
          { path: 'searches', component: StubRouteComponent },
          { path: 'admin', component: StubRouteComponent },
        ]),
        { provide: AuthService, useValue: authServiceSpy },
      ],
    });

    fixture = TestBed.createComponent(AppComponent);
    fixture.detectChanges();
  }

  beforeEach(() => {
    permissions = new Set<Permission>();
    currentUser = makeUser();
    TestBed.resetTestingModule();
  });

  it('muestra únicamente Organización Limpiezas como enlace de menú para limpiadora', () => {
    permissions = new Set<Permission>(['cleaning:access', 'bookings:read']);
    currentUser = makeUser({ role: 'limpiadora' });

    setup();

    const menuLinks = [...fixture.nativeElement.querySelectorAll('.menu a')].map(link =>
      (link.textContent ?? '').trim()
    );
    const sidebarText = fixture.nativeElement.textContent;

    expect(menuLinks).toEqual(['🧹 Org. Limpiezas']);
    expect(sidebarText).not.toContain('Calendario');
    expect(sidebarText).not.toContain('Búsquedas');
    expect(sidebarText).not.toContain('Panel de Administrador');
  });

  it('mantiene Calendario visible para usuarios con permiso de calendario', () => {
    permissions = new Set<Permission>(['calendar:access']);
    currentUser = makeUser({ role: 'admin' });

    setup();

    const menuLinks = [...fixture.nativeElement.querySelectorAll('.menu a')].map(link =>
      (link.textContent ?? '').trim()
    );

    expect(menuLinks).toContain('📅 Calendario');
  });

  it('ejecuta logout desde el botón de cerrar sesión', () => {
    permissions = new Set<Permission>(['cleaning:access']);

    setup();

    const logoutButton: HTMLButtonElement = fixture.nativeElement.querySelector('.logout-btn');
    logoutButton.click();

    expect(authServiceSpy.logout).toHaveBeenCalledTimes(1);
  });
});
