import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiError } from '../../core/api/api-error';
import {
  PROJECT_STATUS_LABEL,
  ProjectListItem,
  ProjectStatus,
  UserListItem,
} from '../../core/api/models';
import { ProjectsApi } from '../../core/api/projects.api';
import { UsersApi } from '../../core/api/users.api';
import { SessionService } from '../../core/auth/session.service';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { RoleChipComponent } from './role-chip.component';

const PAGE_SIZE = 20;

/**
 * Lista de proyectos (RF-13, RF-14).
 *
 * Un integrante ve los suyos; un administrador ve todos, porque necesita
 * supervisar (RN-01). El formulario de creación solo aparece para el
 * administrador, y el backend lo verifica igual.
 */
@Component({
  selector: 'app-projects-list-page',
  imports: [
    FormsModule,
    RouterLink,
    BogotaDatePipe,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    EmptyStateComponent,
    FieldComponent,
    InputDirective,
    PageHeaderComponent,
    RoleChipComponent,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
      <ui-page-header
        title="Proyectos"
        [description]="
          session.isAdmin()
            ? 'Todos los proyectos del semillero. Los proyectos no se eliminan: se archivan.'
            : 'Los proyectos de los que haces parte.'
        "
      >
        @if (session.isAdmin()) {
          <ui-button
            [variant]="formOpen() ? 'secondary' : 'primary'"
            (pressed)="toggleForm()"
          >
            {{ formOpen() ? 'Cancelar' : 'Crear proyecto' }}
          </ui-button>
        }
      </ui-page-header>

      @if (formOpen()) {
        <form
          class="mt-6 rounded-[var(--radius-panel)] border border-line bg-surface p-5 sm:p-6"
          (ngSubmit)="create()"
        >
          <h2 class="text-base font-semibold text-ink">Nuevo proyecto</h2>
          <p class="mt-1 text-sm text-ink-muted">
            Se crean los roles Líder, Colaborador y Observador, y la persona que designes
            queda como líder.
          </p>

          <div class="mt-5 grid gap-4 sm:grid-cols-2">
            <div class="sm:col-span-2">
              <ui-field label="Nombre" for="nombre" [error]="fieldError('name')">
                <input
                  uiInput
                  id="nombre"
                  name="nombre"
                  required
                  minlength="3"
                  maxlength="120"
                  placeholder="Detección de anomalías"
                  [(ngModel)]="form.name"
                />
              </ui-field>
            </div>

            <div class="sm:col-span-2">
              <ui-field label="Descripción" for="descripcion" [optional]="true">
                <textarea
                  uiInput
                  id="descripcion"
                  name="descripcion"
                  rows="3"
                  class="min-h-24 py-2.5"
                  placeholder="Qué se va a construir y con qué datos."
                  [(ngModel)]="form.description"
                ></textarea>
              </ui-field>
            </div>

            <ui-field label="Fecha de inicio" for="inicio" [optional]="true">
              <input uiInput id="inicio" name="inicio" type="date" [(ngModel)]="form.startDate" />
            </ui-field>

            <ui-field
              label="Líder"
              for="lider"
              [error]="fieldError('leader')"
              hint="Solo aparecen las cuentas activas."
            >
              <select uiInput id="lider" name="lider" required [(ngModel)]="form.leaderId">
                <option value="">Elige a una persona</option>
                @for (candidate of candidates(); track candidate.id) {
                  <option [value]="candidate.id">
                    {{ candidate.full_name }} · {{ candidate.email }}
                  </option>
                }
              </select>
            </ui-field>
          </div>

          @if (formError()) {
            <div class="mt-4">
              <ui-alert tone="error">{{ formError() }}</ui-alert>
            </div>
          }

          <div class="mt-5 flex flex-col gap-2 sm:flex-row-reverse">
            <ui-button type="submit" [loading]="saving()" [disabled]="!canSubmit()">
              Crear proyecto
            </ui-button>
            <ui-button variant="ghost" (pressed)="toggleForm()">Cancelar</ui-button>
          </div>
        </form>
      }

      <div class="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div class="sm:w-48">
          <label for="filtro-estado" class="mb-1.5 block text-sm font-medium text-ink">
            Estado
          </label>
          <select
            uiInput
            id="filtro-estado"
            [ngModel]="statusFilter()"
            (ngModelChange)="onStatusChange($event)"
          >
            <option value="">Todos</option>
            <option value="ACTIVE">Activos</option>
            <option value="ARCHIVED">Archivados</option>
          </select>
        </div>
      </div>

      @if (error()) {
        <div class="mt-5">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      }

      <div class="mt-6 border-t border-line">
        @if (loading()) {
          <div class="flex items-center gap-2.5 px-1 py-10 text-sm text-ink-muted">
            <ui-spinner [size]="18" />
            <span>Cargando proyectos…</span>
          </div>
        } @else if (projects().length === 0) {
          <ui-empty-state
            title="Todavía no hay proyectos"
            [description]="
              statusFilter()
                ? 'Ningún proyecto está en ese estado.'
                : session.isAdmin()
                  ? 'Crea el primero y designa a quien lo va a liderar.'
                  : 'Cuando te agreguen a un proyecto, aparecerá aquí.'
            "
          >
            @if (statusFilter()) {
              <ui-button variant="secondary" size="sm" (pressed)="onStatusChange('')">
                Ver todos
              </ui-button>
            }
          </ui-empty-state>
        } @else {
          <ul>
            @for (project of projects(); track project.id) {
              <li>
                <a
                  [routerLink]="['/proyectos', project.id]"
                  class="-mx-3 flex flex-col gap-3 rounded-[var(--radius-control)] border-b border-line px-3 py-4 transition-colors hover:bg-sunken sm:flex-row sm:items-center sm:gap-6"
                >
                  <div class="min-w-0 flex-1">
                    <p class="flex flex-wrap items-center gap-2 text-sm font-medium text-ink">
                      {{ project.name }}
                      @if (project.status === 'ARCHIVED') {
                        <ui-badge tone="neutral">{{ statusLabel(project.status) }}</ui-badge>
                      }
                    </p>
                    @if (project.description) {
                      <p class="mt-1 line-clamp-2 max-w-prose text-sm text-ink-muted">
                        {{ project.description }}
                      </p>
                    }
                    <p class="mt-1.5 text-xs text-ink-muted">
                      {{ project.member_count }}
                      {{ project.member_count === 1 ? 'integrante' : 'integrantes' }}
                      @if (project.start_date) {
                        · Inicia el {{ project.start_date | bogotaDate }}
                      }
                    </p>
                  </div>

                  <div class="shrink-0">
                    @if (project.my_role; as role) {
                      <app-role-chip [name]="role.name" [color]="role.color" />
                    } @else {
                      <span class="text-xs text-ink-muted">Solo lectura</span>
                    }
                  </div>
                </a>
              </li>
            }
          </ul>

          @if (totalPages() > 1) {
            <nav class="flex items-center justify-between py-5" aria-label="Paginación">
              <ui-button
                variant="secondary"
                size="sm"
                [disabled]="page() === 1"
                (pressed)="goTo(page() - 1)"
              >
                Anterior
              </ui-button>
              <span class="text-sm text-ink-muted">
                Página {{ page() }} de {{ totalPages() }} · {{ total() }} proyectos
              </span>
              <ui-button
                variant="secondary"
                size="sm"
                [disabled]="page() === totalPages()"
                (pressed)="goTo(page() + 1)"
              >
                Siguiente
              </ui-button>
            </nav>
          }
        }
      </div>
    </div>
  `,
})
export class ProjectsListPage {
  protected readonly session = inject(SessionService);
  private readonly projectsApi = inject(ProjectsApi);
  private readonly usersApi = inject(UsersApi);

  protected readonly projects = signal<ProjectListItem[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly statusFilter = signal<ProjectStatus | ''>('');

  protected readonly formOpen = signal(false);
  protected readonly saving = signal(false);
  protected readonly formError = signal('');
  /** Se enciende al primer envío. Antes de eso no se marca ningún campo. */
  protected readonly submitted = signal(false);
  protected readonly candidates = signal<UserListItem[]>([]);
  protected form = { name: '', description: '', startDate: '', leaderId: '' };

  protected readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / PAGE_SIZE)));
  protected readonly canSubmit = computed(() => !this.saving());

  constructor() {
    this.load();
  }

  protected statusLabel(status: ProjectStatus): string {
    return PROJECT_STATUS_LABEL[status];
  }

  /** Los errores por campo solo aparecen después de intentar enviar: un
   * formulario recién abierto no acusa a nadie de nada. */
  protected fieldError(field: 'name' | 'leader'): string {
    if (!this.submitted()) return '';
    if (field === 'name' && this.form.name.trim().length < 3) {
      return 'El nombre necesita al menos 3 caracteres.';
    }
    if (field === 'leader' && !this.form.leaderId) {
      return 'Elige quién va a liderar el proyecto.';
    }
    return '';
  }

  protected toggleForm(): void {
    const opening = !this.formOpen();
    this.formOpen.set(opening);
    this.formError.set('');
    this.submitted.set(false);
    if (opening && this.candidates().length === 0) {
      // La lista reducida de usuarios activos: cualquier autenticado la consulta.
      this.usersApi.list({ status: 'ACTIVE', size: 100 }).subscribe({
        next: (result) => this.candidates.set(result.items),
        error: (err: ApiError) => this.formError.set(err.message),
      });
    }
  }

  protected create(): void {
    this.submitted.set(true);
    if (this.form.name.trim().length < 3 || !this.form.leaderId) {
      this.formError.set('Revisa el nombre y la persona que va a liderar el proyecto.');
      return;
    }
    this.saving.set(true);
    this.formError.set('');

    this.projectsApi
      .create({
        name: this.form.name.trim(),
        description: this.form.description.trim() || null,
        start_date: this.form.startDate || null,
        leader_user_id: this.form.leaderId,
      })
      .subscribe({
        next: () => {
          this.saving.set(false);
          this.formOpen.set(false);
          this.submitted.set(false);
          this.form = { name: '', description: '', startDate: '', leaderId: '' };
          this.page.set(1);
          this.load();
        },
        error: (err: ApiError) => {
          this.saving.set(false);
          this.formError.set(err.message);
        },
      });
  }

  protected onStatusChange(value: ProjectStatus | ''): void {
    this.statusFilter.set(value);
    this.page.set(1);
    this.load();
  }

  protected goTo(page: number): void {
    this.page.set(page);
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set('');

    this.projectsApi
      .list({ status: this.statusFilter() || undefined, page: this.page(), size: PAGE_SIZE })
      .subscribe({
        next: (result) => {
          this.projects.set(result.items);
          this.total.set(result.total);
          this.loading.set(false);
        },
        error: (err: ApiError) => {
          this.loading.set(false);
          this.error.set(err.message);
        },
      });
  }
}
