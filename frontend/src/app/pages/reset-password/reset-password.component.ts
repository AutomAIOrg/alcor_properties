import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { AuthService } from '../../auth/auth.service';

@Component({
  selector: 'app-reset-password',
  imports: [FormsModule],
  templateUrl: './reset-password.component.html',
  styleUrl: '../logging/logging.component.scss',
})
export class ResetPasswordComponent {
  private authService = inject(AuthService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);

  private readonly token = this.route.snapshot.queryParamMap.get('token') ?? '';

  newPassword = '';
  confirmPassword = '';
  errorMsg = '';
  loading = signal(false);
  done = signal(false);

  get hasToken(): boolean {
    return this.token.length > 0;
  }

  onSubmit(): void {
    if (this.loading()) return;
    this.errorMsg = '';

    if (this.newPassword !== this.confirmPassword) {
      this.errorMsg = 'Las contraseñas no coinciden.';
      return;
    }

    this.loading.set(true);
    this.authService.resetPassword(this.token, this.newPassword).subscribe({
      next: () => {
        this.done.set(true);
        this.loading.set(false);
        setTimeout(() => this.goToLogin(), 2500);
      },
      error: err => {
        this.errorMsg = this.messageForError(err.status);
        this.loading.set(false);
      },
    });
  }

  goToLogin(): void {
    void this.router.navigate(['/login']);
  }

  private messageForError(status: number): string {
    if (status === 422) return 'La contraseña debe tener al menos 6 caracteres.';
    if (status === 401) return 'El enlace no es válido o ha caducado. Solicita uno nuevo.';
    return 'No se ha podido cambiar la contraseña. Vuelve a intentarlo.';
  }
}
