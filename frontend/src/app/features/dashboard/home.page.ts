import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ApiClient } from '../../core/api/api-client.service';
import { SessionService } from '../../core/auth/session.service';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';

type HealthState = 'checking' | 'up' | 'down';

/**
 * Pantalla de inicio.
 *
 * En la Fase 1 la plataforma todavía no tiene proyectos ni tareas, así que
 * esta pantalla dice la verdad sobre lo que hay y muestra el estado del
 * servidor, que es el cierre de la Fase 0 del `roadmap.md`. Cuando lleguen las
 * fases siguientes, aquí va "Mis tareas" entre proyectos (RF-36).
 */
@Component({
  selector: 'app-home-page',
  imports: [RouterLink, PageHeaderComponent, BadgeComponent, ButtonComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
      <ui-page-header
        [title]="greeting()"
        description="Aquí van a aparecer tus tareas cuando existan los proyectos. Por ahora la plataforma tiene el acceso listo: invitaciones, cuentas y roles."
      />

      <section class="mt-8" aria-labelledby="estado-servidor">
        <h2 id="estado-servidor" class="text-sm font-medium text-ink">Estado del servidor</h2>
        <div class="mt-3 flex flex-wrap items-center gap-3">
          @switch (health()) {
            @case ('checking') {
              <ui-badge tone="neutral">Comprobando…</ui-badge>
            }
            @case ('up') {
              <ui-badge tone="success">En línea</ui-badge>
            }
            @case ('down') {
              <ui-badge tone="danger">Sin respuesta</ui-badge>
            }
          }
          <p class="text-sm text-ink-muted">
            @if (health() === 'down') {
              El servidor no respondió. Si acaba de despertar, vuelve a intentarlo en un momento.
            } @else {
              La base de datos responde a la sonda del servidor.
            }
          </p>
          <ui-button variant="ghost" size="sm" (pressed)="checkHealth()">Volver a probar</ui-button>
        </div>
      </section>

      @if (session.isAdmin()) {
        <section class="mt-10 border-t border-line pt-8" aria-labelledby="administracion">
          <h2 id="administracion" class="text-sm font-medium text-ink">Administración</h2>
          <ul class="mt-3 flex flex-col gap-1">
            <li>
              <a
                routerLink="/admin/usuarios"
                class="flex min-h-11 items-center rounded-[var(--radius-control)] px-3 text-sm text-accent transition-colors hover:bg-accent-soft"
              >
                Usuarios y roles globales
              </a>
            </li>
            <li>
              <a
                routerLink="/admin/invitaciones"
                class="flex min-h-11 items-center rounded-[var(--radius-control)] px-3 text-sm text-accent transition-colors hover:bg-accent-soft"
              >
                Invitaciones
              </a>
            </li>
          </ul>
        </section>
      }
    </div>
  `,
})
export class HomePage {
  protected readonly session = inject(SessionService);
  private readonly api = inject(ApiClient);

  protected readonly health = signal<HealthState>('checking');

  protected readonly greeting = computed(() => {
    const name = this.session.user()?.full_name ?? '';
    const firstName = name.split(' ')[0];
    return firstName ? `Hola, ${firstName}` : 'Inicio';
  });

  constructor() {
    this.checkHealth();
  }

  protected checkHealth(): void {
    this.health.set('checking');
    this.api.health().subscribe({
      next: () => this.health.set('up'),
      error: () => this.health.set('down'),
    });
  }
}
