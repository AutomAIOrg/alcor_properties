import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-logging',
  imports: [FormsModule],
  templateUrl: './logging.component.html',
  styleUrl: './logging.component.scss',
})
export class LoggingComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  username = '';
  password = '';
  errorMsg = '';
  loading = signal(false);

  // Pasos del flujo de recuperación: 'login' | 'email' | 'sent'
  recoveryStep: 'login' | 'email' | 'sent' = 'login';
  recoveryEmail = '';

  onSubmit() {
    if (this.loading()) return;
    this.errorMsg = '';
    this.loading.set(true);

    this.authService.login({ username: this.username, password: this.password }).subscribe({
      next: () => this.router.navigate([this.authService.getDefaultRoute()]),
      error: () => {
        this.errorMsg = 'Usuario o contraseña incorrectos.';
        this.loading.set(false);
      },
    });
  }

  // Solicita el envío del enlace de restablecimiento al email indicado.
  // La respuesta es siempre la misma (no revela si el email existe).
  onRecovery() {
    if (this.loading()) return;
    this.errorMsg = '';
    this.loading.set(true);

    this.authService.forgotPassword(this.recoveryEmail).subscribe({
      next: () => {
        this.recoveryStep = 'sent';
        this.loading.set(false);
      },
      error: () => {
        this.errorMsg = 'No se ha podido procesar la solicitud. Inténtalo de nuevo.';
        this.loading.set(false);
      },
    });
  }

  startRecovery() {
    this.recoveryStep = 'email';
    this.errorMsg = '';
  }

  backToLogin() {
    this.recoveryStep = 'login';
    this.errorMsg = '';
    this.recoveryEmail = '';
  }
}
