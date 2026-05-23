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

  showRecovery = false;
  recoveryEmail = '';
  recoveryMsg = '';

  onSubmit() {
    if (this.loading()) return;
    this.errorMsg = '';
    this.loading.set(true);

    this.authService.login({ username: this.username, password: this.password }).subscribe({
      next: () => this.router.navigate(['/calendar']),
      error: () => {
        this.errorMsg = 'Usuario o contraseña incorrectos.';
        this.loading.set(false);
      },
    });
  }

  onRecovery() {
    // TODO: conectar con el endpoint de recuperación de contraseña
    this.errorMsg = '';
    this.recoveryMsg = `Se ha enviado un enlace de recuperación a ${this.recoveryEmail}.`;
    this.recoveryEmail = '';
  }

  backToLogin() {
    this.showRecovery = false;
    this.errorMsg = '';
    this.recoveryMsg = '';
  }
}
