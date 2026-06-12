import { Directive, inject, Input, TemplateRef, ViewContainerRef } from '@angular/core';
import { AuthService } from '../auth/auth.service';
import { Role } from '../models/user.model';

/**
 * Directiva estructural que muestra o elimina un elemento del DOM
 * según el rol del usuario autenticado.
 *
 * Uso:
 *   *appHasRole="'admin'"
 *   *appHasRole="['admin', 'limpiadora']"
 */
@Directive({
  selector: '[appHasRole]',
  standalone: true,
})
export class HasRoleDirective {
  private authService = inject(AuthService);
  private templateRef = inject(TemplateRef);
  private viewContainer = inject(ViewContainerRef);

  private hasView = false;

  @Input() set appHasRole(roles: Role | Role[]) {
    const allowed = this.authService.hasRole(roles);

    if (allowed && !this.hasView) {
      this.viewContainer.createEmbeddedView(this.templateRef);
      this.hasView = true;
    } else if (!allowed && this.hasView) {
      this.viewContainer.clear();
      this.hasView = false;
    }
  }
}
