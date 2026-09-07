import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiClient } from '../../core/api/api-client.service';
import { ApiError } from '../../core/api/api-error';
import { TASK_STATUS_LABEL, TASK_STATUS_ORDER, MyTask, TaskStatus } from '../../core/api/models';
import { TasksApi } from '../../core/api/tasks.api';
import { SessionService } from '../../core/auth/session.service';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';

type HealthState = 'checking' | 'up' | 'down';

/**
 * Pantalla de inicio: «Mis tareas» entre todos los proyectos (RF-36).
 *
 * Es la vista que cruza proyectos, así que cada fila dice de cuál viene. El
 * orden lo decide el backend —la fecha más próxima primero, y las tareas sin
 * fecha al final—, que es también el orden en el que hay que ocuparse de ellas.
 */
@Component({
  selector: 'app-home-page',
  imports: [
    FormsModule,
    RouterLink,
    BogotaDatePipe,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    EmptyStateComponent,
    InputDirective,
    PageHeaderComponent,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
      <ui-page-header [title]="greeting()" [description]="summary()" />

      <section class="mt-8" aria-labelledby="mis-tareas">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <h2 id="mis-tareas" class="text-sm font-medium text-ink">Mis tareas</h2>

          <label class="sr-only" for="filtro-estado">Filtrar por estado</label>
          <select
            uiInput
            [compact]="true"
            id="filtro-estado"
            class="w-full sm:w-48"
            [ngModel]="status()"
            (ngModelChange)="setStatus($event)"
          >
            <option value="">Todos los estados</option>
            @for (option of statuses; track option) {
              <option [value]="option">{{ label(option) }}</option>
            }
          </select>
        </div>

        @if (loading()) {
          <div class="flex items-center gap-2.5 py-10 text-sm text-ink-muted">
            <ui-spinner [size]="18" />
            <span>Buscando tus tareas…</span>
          </div>
        } @else if (error()) {
          <div class="mt-4">
            <ui-alert tone="error">{{ error() }}</ui-alert>
          </div>
        } @else if (!tasks().length) {
          <ui-empty-state
            [title]="status() ? 'Ninguna tarea en ese estado' : 'No tienes tareas asignadas'"
            [description]="
              status()
                ? 'Prueba con otro estado para ver el resto de tus tareas.'
                : 'Cuando alguien te ponga como responsable de una tarea, aparecerá aquí con su proyecto y su fecha límite.'
            "
          >
            <a
              routerLink="/proyectos"
              class="inline-flex min-h-11 items-center rounded-[var(--radius-control)] border border-line-strong bg-surface px-4 text-sm font-medium text-ink transition-colors hover:bg-sunken"
            >
              Ver mis proyectos
            </a>
          </ui-empty-state>
        } @else {
          <ul class="mt-3 grid gap-2">
            @for (task of tasks(); track task.id) {
              <li>
                <a
                  [routerLink]="['/proyectos', task.project.id, 'tablero']"
                  class="flex min-h-11 flex-col gap-1.5 rounded-[var(--radius-control)] border border-line bg-surface p-3 transition-colors hover:border-line-strong sm:flex-row sm:items-center sm:justify-between sm:gap-4"
                >
                  <span class="min-w-0">
                    <span class="block text-sm font-medium text-balance text-ink">
                      {{ task.title }}
                    </span>
                    <span class="mt-0.5 block text-xs text-ink-muted">
                      {{ task.project.name }}
                      @if (task.due_date; as due) {
                        · vence el {{ due | bogotaDate }}
                      } @else {
                        · sin fecha límite
                      }
                    </span>
                  </span>

                  <span class="flex shrink-0 items-center gap-1.5">
                    @if (task.is_overdue) {
                      <ui-badge tone="danger">Vencida</ui-badge>
                    }
                    <ui-badge tone="neutral">{{ label(task.status) }}</ui-badge>
                  </span>
                </a>
              </li>
            }
          </ul>
        }
      </section>

      <section class="mt-10 border-t border-line pt-8" aria-labelledby="estado-servidor">
        <h2 id="estado-servidor" class="text-sm font-medium text-ink">Estado del servidor</h2>
        <div class="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
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
            @switch (health()) {
              @case ('checking') {
                Preguntándole al servidor. Si estaba dormido, puede tardar.
              }
              @case ('up') {
                La base de datos responde a la sonda del servidor.
              }
              @case ('down') {
                No respondió. Si acaba de despertar, vuelve a intentarlo en un momento.
              }
            }
          </p>
          <!-- El margen negativo compensa el relleno del botón, para que su
               texto quede a plomo con el encabezado de la sección. -->
          <div class="-ml-3">
            <ui-button variant="ghost" size="sm" (pressed)="checkHealth()">
              Volver a probar
            </ui-button>
          </div>
        </div>
      </section>

      @if (session.isAdmin()) {
        <section class="mt-10 border-t border-line pt-8" aria-labelledby="administracion">
          <h2 id="administracion" class="text-sm font-medium text-ink">Administración</h2>
          <ul class="mt-3 -mx-3 flex flex-col gap-1">
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
  private readonly tasksApi = inject(TasksApi);

  protected readonly statuses = TASK_STATUS_ORDER;

  protected readonly health = signal<HealthState>('checking');
  protected readonly tasks = signal<MyTask[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly status = signal<TaskStatus | ''>('');

  protected readonly greeting = computed(() => {
    const name = this.session.user()?.full_name ?? '';
    const firstName = name.split(' ')[0];
    return firstName ? `Hola, ${firstName}` : 'Inicio';
  });

  protected readonly summary = computed(() => {
    if (this.loading() || this.error()) return '';
    const overdue = this.tasks().filter((task) => task.is_overdue).length;
    if (overdue) {
      return overdue === 1
        ? 'Tienes una tarea vencida. Empieza por ahí.'
        : `Tienes ${overdue} tareas vencidas. Empieza por ahí.`;
    }
    return this.tasks().length
      ? 'Esto es lo que tienes asignado, con lo más próximo primero.'
      : 'Aquí aparecen las tareas de las que eres responsable, en cualquier proyecto.';
  });

  constructor() {
    this.checkHealth();
    this.loadTasks();
  }

  protected label(status: TaskStatus): string {
    return TASK_STATUS_LABEL[status];
  }

  protected setStatus(status: TaskStatus | ''): void {
    this.status.set(status);
    this.loadTasks();
  }

  protected loadTasks(): void {
    this.loading.set(true);
    this.error.set('');
    this.tasksApi.myTasks({ status: this.status(), size: 100 }).subscribe({
      next: (page) => {
        this.tasks.set(page.items);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err.message);
        this.loading.set(false);
      },
    });
  }

  protected checkHealth(): void {
    this.health.set('checking');
    this.api.health().subscribe({
      next: () => this.health.set('up'),
      error: () => this.health.set('down'),
    });
  }
}
