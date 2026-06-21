import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { of, throwError } from 'rxjs';

import { ResetPasswordComponent } from './reset-password.component';
import { AuthService } from '../../auth/auth.service';
import { MessageResponse } from '../../models/auth.model';

function makeMessageResponse(message = 'Contraseña actualizada.'): MessageResponse {
  return { message };
}

function configure(token: string | null) {
  const authServiceSpy = {
    resetPassword: jest.fn(),
  } as unknown as jest.Mocked<AuthService>;

  const routerSpy = {
    navigate: jest.fn().mockResolvedValue(true),
  } as unknown as jest.Mocked<Router>;

  const activatedRoute = {
    snapshot: { queryParamMap: { get: () => token } },
  } as unknown as ActivatedRoute;

  TestBed.configureTestingModule({
    imports: [ResetPasswordComponent],
    providers: [
      { provide: AuthService, useValue: authServiceSpy },
      { provide: Router, useValue: routerSpy },
      { provide: ActivatedRoute, useValue: activatedRoute },
    ],
  }).overrideComponent(ResetPasswordComponent, {
    set: { imports: [FormsModule], template: '<span></span>' },
  });

  const fixture: ComponentFixture<ResetPasswordComponent> =
    TestBed.createComponent(ResetPasswordComponent);
  return { fixture, component: fixture.componentInstance, authServiceSpy, routerSpy };
}

describe('ResetPasswordComponent', () => {
  afterEach(() => {
    jest.useRealTimers();
    TestBed.resetTestingModule();
  });

  describe('token ausente', () => {
    it('hasToken es false cuando no hay token en la URL', () => {
      const { component } = configure(null);
      expect(component.hasToken).toBe(false);
    });
  });

  describe('token presente', () => {
    it('hasToken es true cuando hay token en la URL', () => {
      const { component } = configure('reset-token');
      expect(component.hasToken).toBe(true);
    });

    it('no envía si las contraseñas no coinciden', () => {
      const { component, authServiceSpy } = configure('reset-token');
      component.newPassword = 'nueva123';
      component.confirmPassword = 'otra456';

      component.onSubmit();

      expect(component.errorMsg).toBe('Las contraseñas no coinciden.');
      expect(authServiceSpy.resetPassword).not.toHaveBeenCalled();
    });

    it('cambia la contraseña con el token de la URL y marca done', () => {
      jest.useFakeTimers();
      const { component, authServiceSpy, routerSpy } = configure('reset-token');
      authServiceSpy.resetPassword.mockReturnValue(of(makeMessageResponse()));

      component.newPassword = 'nueva123';
      component.confirmPassword = 'nueva123';

      component.onSubmit();

      expect(authServiceSpy.resetPassword).toHaveBeenCalledWith('reset-token', 'nueva123');
      expect(component.done()).toBe(true);
      expect(component.loading()).toBe(false);

      jest.runAllTimers();
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/login']);
    });

    it('muestra error de longitud mínima ante un 422', () => {
      const { component, authServiceSpy } = configure('reset-token');
      authServiceSpy.resetPassword.mockReturnValue(throwError(() => ({ status: 422 })));

      component.newPassword = '123';
      component.confirmPassword = '123';

      component.onSubmit();

      expect(component.errorMsg).toBe('La contraseña debe tener al menos 6 caracteres.');
      expect(component.loading()).toBe(false);
    });

    it('muestra error de enlace caducado ante un 401', () => {
      const { component, authServiceSpy } = configure('reset-token');
      authServiceSpy.resetPassword.mockReturnValue(throwError(() => ({ status: 401 })));

      component.newPassword = 'nueva123';
      component.confirmPassword = 'nueva123';

      component.onSubmit();

      expect(component.errorMsg).toBe('El enlace no es válido o ha caducado. Solicita uno nuevo.');
    });
  });
});
