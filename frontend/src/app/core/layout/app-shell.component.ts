import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { BrandComponent } from '../../shared/ui/brand.component';
import { SessionService } from '../auth/session.service';
import { NotificationStore } from '../notifications/notification.store';
import { NotificationBellComponent } from './notification-bell.component';

interface NavItem {
  path: string;
  label: string;
  adminOnly: boolean;
}

/**
 * Armazón de la aplicación autenticada.
 *
 * Solo se listan destinos que existen: poner enlaces a pantallas inexistentes
 * sería mentirle al usuario.
 *
 * «Lecciones» va sin marca de administración porque el catálogo publicado es de
 * todo el semillero (RF-51). Quien puede editarlo entra al editor desde esa
 * misma pantalla.
 *
 * Adaptación (RNF-01): barra lateral fija desde 768 px; por debajo, barra
 * superior con menú desplegable, porque la lateral se come el ancho útil de un
 * teléfono de 360 px.
 */
@Component({
  selector: 'app-shell',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, BrandComponent, NotificationBellComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex min-h-dvh flex-col md:flex-row">
      <!-- Barra superior: solo móvil -->
      <header
        class="flex items-center justify-between border-b border-line bg-surface px-4 py-3 md:hidden"
      >
        <a routerLink="/inicio" class="flex min-h-11 items-center" (click)="menuOpen.set(false)">
          <ui-brand />
        </a>
        <div class="flex items-center gap-1">
          <app-notification-bell />
          <button
            type="button"
            class="inline-flex min-h-11 min-w-11 items-center justify-center rounded-[var(--radius-control)] text-ink-muted hover:bg-sunken hover:text-ink"
            [attr.aria-expanded]="menuOpen()"
            aria-controls="menu-principal"
            (click)="menuOpen.set(!menuOpen())"
          >
            <span class="sr-only">{{ menuOpen() ? 'Cerrar menú' : 'Abrir menú' }}</span>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
              @if (menuOpen()) {
                <path
                  d="M6 6l12 12M18 6L6 18"
                  stroke="currentColor"
                  stroke-width="1.75"
                  stroke-linecap="round"
                />
              } @else {
                <path
                  d="M4 7h16M4 12h16M4 17h16"
                  stroke="currentColor"
                  stroke-width="1.75"
                  stroke-linecap="round"
                />
              }
            </svg>
          </button>
        </div>
      </header>

      <!-- Navegación: desplegable en móvil, lateral fija desde 768 px -->
      <nav
        id="menu-principal"
        class="border-line bg-surface md:block md:w-60 md:shrink-0 md:border-r"
        [class.hidden]="!menuOpen()"
        [class.border-b]="menuOpen()"
      >
        <div class="flex h-full flex-col md:sticky md:top-0 md:h-dvh">
          <div class="hidden items-center justify-between px-5 py-4 md:flex">
            <a routerLink="/inicio" class="flex items-center">
              <ui-brand />
            </a>
            <app-notification-bell />
          </div>

          <ul class="flex flex-col gap-0.5 p-3 md:px-3 md:py-0">
            @for (item of visibleNav(); track item.path) {
              <li>
                <a
                  [routerLink]="item.path"
                  routerLinkActive="bg-accent-soft text-accent font-medium"
                  class="flex min-h-11 items-center rounded-[var(--radius-control)] px-3 text-sm text-ink-muted transition-colors hover:bg-sunken hover:text-ink"
                  (click)="menuOpen.set(false)"
                >
                  {{ item.label }}
                </a>
              </li>
            }
          </ul>

          <div class="mt-auto border-t border-line p-3">
            <a
              routerLink="/perfil"
              routerLinkActive="bg-accent-soft"
              class="flex min-h-11 flex-col justify-center rounded-[var(--radius-control)] px-3 py-1.5 transition-colors hover:bg-sunken"
              (click)="menuOpen.set(false)"
            >
              <span class="truncate text-sm font-medium text-ink">{{ userName() }}</span>
              <span class="truncate text-xs text-ink-muted">{{ userEmail() }}</span>
            </a>
            <button
              type="button"
              class="mt-0.5 flex min-h-11 w-full items-center rounded-[var(--radius-control)] px-3 text-sm text-ink-muted transition-colors hover:bg-sunken hover:text-ink"
              (click)="signOut()"
            >
              Cerrar sesión
            </button>
          </div>
        </div>
      </nav>

      <main class="min-w-0 flex-1">
        <router-outlet />
      </main>
    </div>
  `,
})
export class AppShellComponent {
  private readonly session = inject(SessionService);
  private readonly router = inject(Router);
  private readonly notifications = inject(NotificationStore);

  protected readonly menuOpen = signal(false);

  constructor() {
    // Aquí y no en el arranque de la aplicación: este armazón es lo único que
    // no se pinta sin sesión, así que nada consulta el contador desde la
    // pantalla de ingreso.
    this.notifications.start();
  }

  private readonly nav: NavItem[] = [
    { path: '/inicio', label: 'Inicio', adminOnly: false },
    { path: '/proyectos', label: 'Proyectos', adminOnly: false },
    { path: '/lecciones', label: 'Lecciones', adminOnly: false },
    { path: '/admin/usuarios', label: 'Usuarios', adminOnly: true },
    { path: '/admin/invitaciones', label: 'Invitaciones', adminOnly: true },
    { path: '/admin/notificaciones', label: 'Notificaciones', adminOnly: true },
  ];

  protected readonly visibleNav = computed(() =>
    this.nav.filter((item) => !item.adminOnly || this.session.isAdmin()),
  );

  protected readonly userName = computed(() => this.session.user()?.full_name ?? '');
  protected readonly userEmail = computed(() => this.session.user()?.email ?? '');

  protected signOut(): void {
    this.menuOpen.set(false);
    // Sin esto, quien entre después vería por un instante el número del anterior.
    this.notifications.reset();
    this.session.logout().subscribe(() => {
      void this.router.navigate(['/ingresar']);
    });
  }
}
