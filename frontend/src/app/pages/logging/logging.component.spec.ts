import { ComponentFixture, TestBed } from '@angular/core/testing';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { of, Subject, throwError } from 'rxjs';

import { LoggingComponent } from './logging.component';
import { AuthService } from '../../auth/auth.service';
import { AuthResponse, MessageResponse } from '../../models/auth.model';

// ─── Fixture helpers ──────────────────────────────────────────────────────────

function makeAuthResponse(overrides: Partial<AuthResponse> = {}): AuthResponse {
  return {
    access_token: 'fake.jwt.token',
    ...overrides,
  } as AuthResponse;
}

function makeMessageResponse(
  message = 'Si el email está registrado, recibirás un enlace.'
): MessageResponse {
  return { message };
}

// ─── Spec ─────────────────────────────────────────────────────────────────────

describe('LoggingComponent', () => {
  let fixture: ComponentFixture<LoggingComponent>;
  let component: LoggingComponent;
  let authServiceSpy: jest.Mocked<AuthService>;
  let routerSpy: jest.Mocked<Router>;

  beforeEach(async () => {
    authServiceSpy = {
      login: jest.fn(),
      forgotPassword: jest.fn(),
      mustChangePassword: jest.fn().mockReturnValue(false),
      getDefaultRoute: jest.fn().mockReturnValue('/calendar'),
    } as unknown as jest.Mocked<AuthService>;

    routerSpy = {
      navigate: jest.fn().mockResolvedValue(true),
    } as unknown as jest.Mocked<Router>;

    await TestBed.configureTestingModule({
      imports: [LoggingComponent],
      providers: [
        { provide: AuthService, useValue: authServiceSpy },
        { provide: Router, useValue: routerSpy },
      ],
    })
      .overrideComponent(LoggingComponent, {
        set: {
          imports: [FormsModule],
          template: `
            <form class="login-form" (ngSubmit)="onSubmit()">
              <input
                class="username-input"
                name="username"
                [(ngModel)]="username"
              />

              <input
                class="password-input"
                name="password"
                [(ngModel)]="password"
              />

              <button class="submit-btn" type="submit">
                Entrar
              </button>
            </form>

            <input
              class="recovery-email-input"
              name="recoveryEmail"
              [(ngModel)]="recoveryEmail"
            />

            <button class="recovery-btn" type="button" (click)="onRecovery()">
              Recuperar contraseña
            </button>

            <button class="back-btn" type="button" (click)="backToLogin()">
              Volver
            </button>

            <p class="error-msg">{{ errorMsg }}</p>
            <p class="recovery-step">{{ recoveryStep }}</p>
            <p class="loading-state">{{ loading() }}</p>
          `,
        },
      })
      .compileComponents();

    fixture = TestBed.createComponent(LoggingComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  // ── A: Inicialización ───────────────────────────────────────────────────────

  describe('A — inicialización', () => {
    it('crea el componente correctamente', () => {
      expect(component).toBeTruthy();
    });

    it('inicia con el estado por defecto', () => {
      expect(component.username).toBe('');
      expect(component.password).toBe('');
      expect(component.errorMsg).toBe('');
      expect(component.loading()).toBe(false);
      expect(component.recoveryStep).toBe('login');
      expect(component.recoveryEmail).toBe('');
    });
  });

  // ── B: onSubmit success ─────────────────────────────────────────────────────

  describe('B — onSubmit success', () => {
    it('envía credenciales, limpia errores, activa loading y navega a la ruta por defecto', () => {
      authServiceSpy.login.mockReturnValue(of(makeAuthResponse()));
      authServiceSpy.getDefaultRoute.mockReturnValue('/cleaning-organization');

      component.errorMsg = 'Error anterior';
      component.username = 'admin@test.com';
      component.password = '123456';

      component.onSubmit();

      expect(authServiceSpy.login).toHaveBeenCalledTimes(1);
      expect(authServiceSpy.login).toHaveBeenCalledWith({
        username: 'admin@test.com',
        password: '123456',
      });
      expect(component.errorMsg).toBe('');
      expect(component.loading()).toBe(true);
      expect(authServiceSpy.getDefaultRoute).toHaveBeenCalledTimes(1);
      expect(routerSpy.navigate).toHaveBeenCalledTimes(1);
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/cleaning-organization']);
    });

    it('navega al cambio de contraseña si el usuario aún tiene la inicial', () => {
      authServiceSpy.login.mockReturnValue(of(makeAuthResponse()));
      authServiceSpy.mustChangePassword.mockReturnValue(true);

      component.username = 'nueva@test.com';
      component.password = 'alcor1234';

      component.onSubmit();

      expect(routerSpy.navigate).toHaveBeenCalledWith(['/change-initial-password']);
      expect(authServiceSpy.getDefaultRoute).not.toHaveBeenCalled();
    });
  });

  // ── C: onSubmit error ───────────────────────────────────────────────────────

  describe('C — onSubmit error', () => {
    it('muestra mensaje de error si el login falla', () => {
      authServiceSpy.login.mockReturnValue(throwError(() => new Error('Unauthorized')));

      component.username = 'wrong@test.com';
      component.password = 'bad-password';

      component.onSubmit();

      expect(component.errorMsg).toBe('Usuario o contraseña incorrectos.');
    });

    it('pone loading en false si el login falla', () => {
      authServiceSpy.login.mockReturnValue(throwError(() => new Error('Unauthorized')));

      component.onSubmit();

      expect(component.loading()).toBe(false);
    });

    it('no navega si el login falla', () => {
      authServiceSpy.login.mockReturnValue(throwError(() => new Error('Unauthorized')));

      component.onSubmit();

      expect(routerSpy.navigate).not.toHaveBeenCalled();
    });
  });

  // ── D: Protección contra doble submit ───────────────────────────────────────

  describe('D — protección contra doble submit', () => {
    it('no llama a login si loading ya está en true', () => {
      component.loading.set(true);

      component.onSubmit();

      expect(authServiceSpy.login).not.toHaveBeenCalled();
    });

    it('evita doble submit mientras el primer login está pendiente', () => {
      const loginSubject = new Subject<AuthResponse>();

      authServiceSpy.login.mockReturnValue(loginSubject.asObservable());

      component.username = 'admin@test.com';
      component.password = '123456';

      component.onSubmit();
      component.onSubmit();

      expect(authServiceSpy.login).toHaveBeenCalledTimes(1);

      loginSubject.next(makeAuthResponse());
      loginSubject.complete();
    });
  });

  // ── E: onRecovery (solicitar enlace por email) ──────────────────────────────

  describe('E — onRecovery', () => {
    it('solicita el enlace, avanza al paso "sent" y limpia errores', () => {
      authServiceSpy.forgotPassword.mockReturnValue(of(makeMessageResponse()));

      component.errorMsg = 'Error anterior';
      component.recoveryEmail = 'user@test.com';

      component.onRecovery();

      expect(authServiceSpy.forgotPassword).toHaveBeenCalledWith('user@test.com');
      expect(component.errorMsg).toBe('');
      expect(component.recoveryStep).toBe('sent');
      expect(component.loading()).toBe(false);
    });

    it('muestra error genérico ante un fallo y permanece en el paso email', () => {
      authServiceSpy.forgotPassword.mockReturnValue(throwError(() => ({ status: 500 })));

      component.recoveryStep = 'email';
      component.recoveryEmail = 'user@test.com';

      component.onRecovery();

      expect(component.errorMsg).toBe('No se ha podido procesar la solicitud. Inténtalo de nuevo.');
      expect(component.recoveryStep).toBe('email');
      expect(component.loading()).toBe(false);
    });

    it('no llama a forgotPassword si loading ya está en true', () => {
      component.loading.set(true);

      component.onRecovery();

      expect(authServiceSpy.forgotPassword).not.toHaveBeenCalled();
    });
  });

  // ── F: backToLogin ──────────────────────────────────────────────────────────

  describe('F — backToLogin', () => {
    it('vuelve al paso de login y limpia el estado de recuperación', () => {
      component.recoveryStep = 'sent';
      component.errorMsg = 'Error anterior';
      component.recoveryEmail = 'user@test.com';

      component.backToLogin();

      expect(component.recoveryStep).toBe('login');
      expect(component.errorMsg).toBe('');
      expect(component.recoveryEmail).toBe('');
    });
  });

  // ── G: Integración con DOM ──────────────────────────────────────────────────

  describe('G — integración con el DOM', () => {
    it('actualiza username y password al escribir en los inputs', async () => {
      const usernameInput: HTMLInputElement =
        fixture.nativeElement.querySelector('.username-input');

      const passwordInput: HTMLInputElement =
        fixture.nativeElement.querySelector('.password-input');

      usernameInput.value = 'admin@test.com';
      usernameInput.dispatchEvent(new Event('input'));

      passwordInput.value = '123456';
      passwordInput.dispatchEvent(new Event('input'));

      fixture.detectChanges();
      await fixture.whenStable();

      expect(component.username).toBe('admin@test.com');
      expect(component.password).toBe('123456');
    });

    it('submit del formulario llama a onSubmit y hace login', async () => {
      authServiceSpy.login.mockReturnValue(of(makeAuthResponse()));

      const usernameInput: HTMLInputElement =
        fixture.nativeElement.querySelector('.username-input');

      const passwordInput: HTMLInputElement =
        fixture.nativeElement.querySelector('.password-input');

      const form: HTMLFormElement = fixture.nativeElement.querySelector('.login-form');

      usernameInput.value = 'admin@test.com';
      usernameInput.dispatchEvent(new Event('input'));

      passwordInput.value = '123456';
      passwordInput.dispatchEvent(new Event('input'));

      fixture.detectChanges();
      await fixture.whenStable();

      form.dispatchEvent(new Event('submit'));

      expect(authServiceSpy.login).toHaveBeenCalledWith({
        username: 'admin@test.com',
        password: '123456',
      });

      expect(authServiceSpy.getDefaultRoute).toHaveBeenCalledTimes(1);
      expect(routerSpy.navigate).toHaveBeenCalledWith(['/calendar']);
    });

    it('click en recuperación ejecuta onRecovery y avanza a "sent"', async () => {
      authServiceSpy.forgotPassword.mockReturnValue(of(makeMessageResponse()));

      const recoveryInput: HTMLInputElement =
        fixture.nativeElement.querySelector('.recovery-email-input');

      const recoveryButton: HTMLButtonElement =
        fixture.nativeElement.querySelector('.recovery-btn');

      recoveryInput.value = 'recovery@test.com';
      recoveryInput.dispatchEvent(new Event('input'));

      fixture.detectChanges();
      await fixture.whenStable();

      recoveryButton.click();

      expect(authServiceSpy.forgotPassword).toHaveBeenCalledWith('recovery@test.com');
      expect(component.recoveryStep).toBe('sent');
    });

    it('click en volver ejecuta backToLogin', () => {
      component.recoveryStep = 'sent';
      component.errorMsg = 'Error';

      fixture.detectChanges();

      const backButton: HTMLButtonElement = fixture.nativeElement.querySelector('.back-btn');

      backButton.click();

      expect(component.recoveryStep).toBe('login');
      expect(component.errorMsg).toBe('');
    });
  });
});
