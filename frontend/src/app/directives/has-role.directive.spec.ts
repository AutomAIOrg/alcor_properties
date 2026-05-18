import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AuthService } from '../auth/auth.service';
import { Role } from '../models/user.model';
import { HasRoleDirective } from './has-role.directive';

type AuthServiceMock = Pick<jest.Mocked<AuthService>, 'hasRole'>;

@Component({
  standalone: true,
  imports: [HasRoleDirective],
  template: `
    <span data-testid="protected-content" *appHasRole="roles"> Contenido protegido </span>
  `,
})
class HostComponent {
  roles: Role | Role[] = 'admin';
}

describe('HasRoleDirective', () => {
  let fixture: ComponentFixture<HostComponent>;
  let component: HostComponent;
  let authServiceMock: AuthServiceMock;

  function setup(hasRole: boolean): void {
    authServiceMock = {
      hasRole: jest.fn().mockReturnValue(hasRole),
    };

    TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [{ provide: AuthService, useValue: authServiceMock }],
    });

    fixture = TestBed.createComponent(HostComponent);
    component = fixture.componentInstance;
  }

  function protectedContent(): HTMLElement | null {
    return fixture.nativeElement.querySelector('[data-testid="protected-content"]');
  }

  afterEach(() => {
    TestBed.resetTestingModule();
  });

  it('muestra el contenido si el usuario tiene el rol requerido', () => {
    setup(true);

    fixture.detectChanges();

    expect(authServiceMock.hasRole).toHaveBeenCalledWith('admin');
    expect(protectedContent()?.textContent).toContain('Contenido protegido');
  });

  it('elimina el contenido del DOM si el usuario no tiene el rol requerido', () => {
    setup(false);

    fixture.detectChanges();

    expect(authServiceMock.hasRole).toHaveBeenCalledWith('admin');
    expect(protectedContent()).toBeNull();
  });

  it('acepta un array de roles permitidos', () => {
    setup(true);
    component.roles = ['admin', 'employee'];

    fixture.detectChanges();

    expect(authServiceMock.hasRole).toHaveBeenCalledWith(['admin', 'employee']);
    expect(protectedContent()).not.toBeNull();
  });

  it('limpia la vista si el rol deja de estar permitido', () => {
    setup(true);

    fixture.detectChanges();
    expect(protectedContent()).not.toBeNull();

    authServiceMock.hasRole.mockReturnValue(false);
    component.roles = 'viewer';
    fixture.detectChanges();

    expect(authServiceMock.hasRole).toHaveBeenLastCalledWith('viewer');
    expect(protectedContent()).toBeNull();
  });

  it('crea la vista si el rol pasa a estar permitido', () => {
    setup(false);

    fixture.detectChanges();
    expect(protectedContent()).toBeNull();

    authServiceMock.hasRole.mockReturnValue(true);
    component.roles = 'employee';
    fixture.detectChanges();

    expect(authServiceMock.hasRole).toHaveBeenLastCalledWith('employee');
    expect(protectedContent()?.textContent).toContain('Contenido protegido');
  });
});
