import { Component, inject } from '@angular/core';
import { AuthService } from '../../auth/auth.service';
import { ChangePasswordFormComponent } from '../../shared/components/change-password-form/change-password-form.component';

/**
 * Vista de gestión de la cuenta para usuarios no administradores.
 *
 * Reúne las acciones que un usuario puede realizar sobre su propia cuenta. De
 * momento, el cambio de contraseña.
 */
@Component({
  selector: 'app-account',
  standalone: true,
  imports: [ChangePasswordFormComponent],
  templateUrl: './account.component.html',
  styleUrl: './account.component.scss',
})
export class AccountComponent {
  readonly authService = inject(AuthService);
}
