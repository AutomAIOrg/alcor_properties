import { Component, inject, output, signal } from '@angular/core';
import { HttpErrorResponse } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../../auth/auth.service';

/**
 * Formulario reutilizable de cambio de contraseña del usuario autenticado.
 *
 * Exige la contraseña actual y la nueva por duplicado. Gestiona por sí mismo la
 * llamada a la API y los mensajes en línea, de modo que puede embeberse tanto en
 * el panel de administrador como en la vista de gestión de la cuenta.
 */
@Component({
  selector: 'app-change-password-form',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './change-password-form.component.html',
  styleUrl: './change-password-form.component.scss',
})
export class ChangePasswordFormComponent {
  private authService = inject(AuthService);

  /** Se emite cuando la contraseña se ha cambiado correctamente. */
  readonly changed = output<void>();

  readonly MIN_PASSWORD_LENGTH = 6;

  currentPassword = signal('');
  newPassword = signal('');
  confirmPassword = signal('');

  isSaving = signal(false);
  errorMsg = signal<string | null>(null);
  successMsg = signal<string | null>(null);

  updateCurrentPassword(value: string): void {
    this.currentPassword.set(value);
  }

  updateNewPassword(value: string): void {
    this.newPassword.set(value);
  }

  updateConfirmPassword(value: string): void {
    this.confirmPassword.set(value);
  }

  onSubmit(): void {
    if (this.isSaving()) return;

    this.errorMsg.set(null);
    this.successMsg.set(null);

    const current = this.currentPassword();
    const next = this.newPassword();
    const confirm = this.confirmPassword();

    if (!current || !next || !confirm) {
      this.errorMsg.set('Rellena todos los campos.');
      return;
    }

    if (next.length < this.MIN_PASSWORD_LENGTH) {
      this.errorMsg.set(
        `La nueva contraseña debe tener al menos ${this.MIN_PASSWORD_LENGTH} caracteres.`
      );
      return;
    }

    if (next !== confirm) {
      this.errorMsg.set('Las contraseñas nuevas no coinciden.');
      return;
    }

    this.isSaving.set(true);
    this.authService.changePassword(current, next).subscribe({
      next: response => {
        this.isSaving.set(false);
        this.resetForm();
        this.successMsg.set(response.message || 'Contraseña actualizada correctamente.');
        this.changed.emit();
      },
      error: (error: HttpErrorResponse) => {
        this.isSaving.set(false);
        this.errorMsg.set(this.getErrorMessage(error));
      },
    });
  }

  private resetForm(): void {
    this.currentPassword.set('');
    this.newPassword.set('');
    this.confirmPassword.set('');
  }

  private getErrorMessage(error: HttpErrorResponse): string {
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
