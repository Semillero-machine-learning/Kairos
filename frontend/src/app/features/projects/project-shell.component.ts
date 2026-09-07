import { ChangeDetectionStrategy, Component, effect, inject, input } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';

import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { ProjectStore } from './project.store';
import { RoleChipComponent } from './role-chip.component';

/**
 * Armazón del proyecto abierto.
 *
 * Carga el detalle una sola vez y lo comparte con las pestañas por el
 * `ProjectStore`, que se provee aquí: cada proyecto tiene su propia instancia y
 * muere al salir. Así las pestañas no repiten la misma petición ni se quedan
 * con permisos de otro proyecto.
 *
 * Un proyecto ajeno responde 404, no 403, así que el mensaje no confirma que
 * exista.
 */
@Component({
  selector: 'app-project-shell',
  imports: [
    RouterOutlet,
    RouterLink,
    RouterLinkActive,
    AlertComponent,
    BadgeComponent,
    EmptyStateComponent,
    RoleChipComponent,
    SpinnerComponent,
  ],
  providers: [ProjectStore],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (store.loading()) {
      <div class="mx-auto flex w-full max-w-5xl items-center gap-2.5 px-5 py-12 text-sm text-ink-muted sm:px-8">
        <ui-spinner [size]="18" />
        <span>Cargando el proyecto…</span>
      </div>
    } @else if (!store.project()) {
      <div class="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
        <ui-empty-state
          title="No encontramos ese proyecto"
          description="Puede que ya no exista o que no hagas parte de él. Pídele acceso a quien lo lidera."
        >
          <a
            routerLink="/proyectos"
            class="inline-flex min-h-11 items-center rounded-[var(--radius-control)] border border-line-strong bg-surface px-4 text-sm font-medium text-ink transition-colors hover:bg-sunken"
          >
            Volver a proyectos
          </a>
        </ui-empty-state>
      </div>
    } @else if (store.project(); as project) {
      <div class="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
        <a
          routerLink="/proyectos"
          class="inline-flex min-h-11 items-center text-sm text-ink-muted transition-colors hover:text-ink"
        >
          ← Proyectos
        </a>

        <header class="mt-2 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div class="min-w-0">
            <h1 class="text-2xl font-semibold tracking-tight text-ink">{{ project.name }}</h1>
            <div class="mt-2 flex flex-wrap items-center gap-2">
              @if (project.my_role; as role) {
                <app-role-chip [name]="role.name" [color]="role.color" suffix="· tu rol" />
              } @else {
                <ui-badge tone="neutral">Solo lectura</ui-badge>
              }
              @if (store.isArchived()) {
                <ui-badge tone="notice">Archivado</ui-badge>
              }
            </div>
          </div>
        </header>

        @if (store.isArchived()) {
          <div class="mt-5">
            <ui-alert tone="notice">
              Este proyecto está archivado. Se puede consultar completo, pero no admite
              cambios ni genera recordatorios.
            </ui-alert>
          </div>
        }

        <nav class="mt-6 flex gap-1 overflow-x-auto border-b border-line" aria-label="Secciones del proyecto">
          @for (tab of tabs; track tab.path) {
            <a
              [routerLink]="tab.path"
              routerLinkActive
              #active="routerLinkActive"
              [attr.aria-current]="active.isActive ? 'page' : null"
              [class]="tabClass(active.isActive)"
            >
              {{ tab.label }}
            </a>
          }
        </nav>

        <router-outlet />
      </div>
    }
  `,
})
export class ProjectShellComponent {
  /** Enlazado desde la ruta con `withComponentInputBinding`. */
  readonly projectId = input.required<string>();

  protected readonly store = inject(ProjectStore);

  protected readonly tabs = [
    { path: 'tablero', label: 'Tablero' },
    { path: 'resumen', label: 'Resumen' },
    { path: 'miembros', label: 'Miembros' },
    { path: 'roles', label: 'Roles' },
  ];

  /** El estado activo y el inactivo no comparten ninguna clase de color: son la
   * misma propiedad CSS, y superponerlas deja que el orden del archivo generado
   * decida cuál gana, no la intención. */
  protected tabClass(isActive: boolean): string {
    return [
      'flex min-h-11 shrink-0 items-center border-b-2 px-3 text-sm font-medium transition-colors',
      isActive
        ? 'border-accent text-accent'
        : 'border-transparent text-ink-muted hover:text-ink',
    ].join(' ');
  }

  constructor() {
    // Un efecto y no una llamada directa: los `input()` todavía no tienen valor
    // cuando corre el constructor, y así navegar de un proyecto a otro sin
    // salir de esta ruta recarga el detalle en vez de dejar el anterior.
    effect(() => this.store.load(this.projectId()));
  }
}
