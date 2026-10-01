import { Component, inject } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs/operators';
import { AuthService } from './auth/auth.service';
import { CHANGE_INITIAL_PASSWORD_ROUTE } from './auth/auth.guard';

// Pantallas a plena página, sin barra lateral: el usuario aún no puede navegar
// por la aplicación (no ha iniciado sesión o sigue con la contraseña inicial).
const CHROMELESS_ROUTES = ['/login', CHANGE_INITIAL_PASSWORD_ROUTE];

function isChromeless(url: string): boolean {
  return CHROMELESS_ROUTES.some(route => url.startsWith(route));
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, CommonModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss'],
})
export class AppComponent {
  private router = inject(Router);
  authService = inject(AuthService);

  showSidebar = toSignal(
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map((e: NavigationEnd) => !isChromeless(e.urlAfterRedirects))
    ),
    { initialValue: !isChromeless(this.router.url) }
  );

  isSidebarHidden = false;

  toggleSidebar() {
    this.isSidebarHidden = !this.isSidebarHidden;
  }

  logout() {
    this.authService.logout();
  }
}
