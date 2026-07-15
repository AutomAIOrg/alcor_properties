import { Component, inject, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../auth/auth.service';

/**
 * Pantalla de cambio obligatorio de la contraseña inicial.
 *
 * Se muestra al primer acceso de un usuario recién creado y tras un
 * restablecimiento del administrador, mientras la cuenta conserve la contraseña
 * inicial del sistema. No pide la contraseña actual: el usuario ya está
 * autenticado con ella.
 */
@Component({
  selector: 'app-change-initial-password',
  imports: [FormsModule],
  templateUrl: './change-initial-password.component.html',
  styleUrl: '../logging/logging.component.scss',
})
export class ChangeInitialPasswordComponent {
  private authService = inject(AuthService);
  private router = inject(Router);

  readonly MIN_PASSWORD_LENGTH = 6;

  newPassword = '';
  confirmPassword = '';
  errorMsg = '';
  loading = signal(false);
  done = signal(false);

  onSubmit(): void {
    if (this.loading()) return;
    this.errorMsg = '';

    if (this.newPassword.length < this.MIN_PASSWORD_LENGTH) {
      this.errorMsg = `La contraseña debe tener al menos ${this.MIN_PASSWORD_LENGTH} caracteres.`;
      return;
    }

    if (this.newPassword !== this.confirmPassword) {
      this.errorMsg = 'Las contraseñas no coinciden.';
      return;
    }

    this.loading.set(true);
    this.authService.changeInitialPassword(this.newPassword).subscribe({
      next: () => {
        this.done.set(true);
        this.loading.set(false);
        setTimeout(() => this.goToApp(), 2500);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMsg = this.messageForError(error);
        this.loading.set(false);
      },
    });
  }

  goToApp(): void {
    void this.router.navigate([this.authService.getDefaultRoute()]);
  }

  private messageForError(error: HttpErrorResponse): string {
    const detail = error.error?.detail;

    if (typeof detail === 'string') return detail;

    if (Array.isArray(detail)) {
      const message = detail
        .map((item: { msg?: string }) => item.msg)
        .filter(Boolean)
        .join('. ');
      if (message) return message;
    }

    return 'No se ha podido cambiar la contraseña. Vuelve a intentarlo.';
  }
}
