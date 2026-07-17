import { Component, computed, effect, inject, signal, HostListener } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive, Router, NavigationEnd } from '@angular/router';
import { CommonModule } from '@angular/common';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs/operators';
import { AuthService } from './auth/auth.service';
import { CHANGE_INITIAL_PASSWORD_ROUTE } from './auth/auth.guard';
import { BannerService } from './services/banner.service';
import { BANNER_DEVELOPER_USERNAME } from './config/banner.config';

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
  bannerService = inject(BannerService);

  showSidebar = toSignal(
    this.router.events.pipe(
      filter(e => e instanceof NavigationEnd),
      map((e: NavigationEnd) => !isChromeless(e.urlAfterRedirects))
    ),
    { initialValue: !isChromeless(this.router.url) }
  );

  // El banner solo se muestra a los administradores, salvo a la cuenta de desarrollo
  // (que solo gestiona el botón para desactivarlo, pero no ve el banner).
  canViewBanner = computed(() => {
    const user = this.authService.currentUser();
    if (!user) return false;
    return user.role === 'admin' && user.username !== BANNER_DEVELOPER_USERNAME;
  });

  isSidebarHidden = false;

  // Banner que se puede cerrar, pero que vuelve a aparecer en cuanto el usuario
  // hace clic en cualquier parte de la app.
  showBanner = signal(true);

  constructor() {
    // Carga (y recarga) el estado global del banner cada vez que hay un usuario
    // autenticado, para reflejar si la cuenta de desarrollo lo ha activado o apagado.
    effect(() => {
      if (this.authService.currentUser()) {
        this.bannerService.load();
      }
    });
  }

  // Cualquier clic dentro de la app vuelve a mostrar el banner. El clic sobre la
  // "×" de cerrar no llega hasta aquí porque detiene su propagación.
  @HostListener('document:click')
  onDocumentClick() {
    this.showBanner.set(true);
  }

  closeBanner(event: MouseEvent) {
    event.stopPropagation();
    this.showBanner.set(false);
  }

  toggleSidebar() {
    this.isSidebarHidden = !this.isSidebarHidden;
  }

  logout() {
    this.authService.logout();
  }
}
