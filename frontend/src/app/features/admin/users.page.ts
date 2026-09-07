import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiError } from '../../core/api/api-error';
import {
  GlobalRole,
  USER_STATUS_LABEL,
  UserListItem,
  UserStatus,
} from '../../core/api/models';
import { UsersApi } from '../../core/api/users.api';
import { SessionService } from '../../core/auth/session.service';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';

const PAGE_SIZE = 20;

/**
 * Administración de usuarios (RF-09 a RF-12).
 *
 * La protección del último administrador (RF-12, RN-02) la impone el backend
 * con un 409 `LAST_ADMIN`; aquí solo se muestra su mensaje. No se replica la
 * regla en el navegador: sería una segunda fuente de verdad que se desincroniza.
 */
@Component({
  selector: 'app-users-page',
  imports: [
    FormsModule,
    BogotaDatePipe,
    PageHeaderComponent,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    EmptyStateComponent,
    InputDirective,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-5xl px-5 py-8 sm:px-8 sm:py-12">
      <ui-page-header
        title="Usuarios"
        description="Todas las cuentas de la plataforma. Los usuarios no se eliminan: se desactivan, y su historial se conserva."
      />

      <!-- Filtros -->
      <div class="mt-6 flex flex-col gap-3 sm:flex-row sm:items-end">
        <div class="flex-1">
          <label for="buscar" class="mb-1.5 block text-sm font-medium text-ink">Buscar</label>
          <input
            uiInput
            id="buscar"
            type="search"
            placeholder="Nombre o correo"
            [ngModel]="search()"
            (ngModelChange)="onSearchChange($event)"
          />
        </div>
        <div class="sm:w-44">
          <label for="filtro-estado" class="mb-1.5 block text-sm font-medium text-ink">Estado</label>
          <select
            uiInput
            id="filtro-estado"
            [ngModel]="statusFilter()"
            (ngModelChange)="onStatusChange($event)"
          >
            <option value="">Todos</option>
            <option value="ACTIVE">Activos</option>
            <option value="DISABLED">Desactivados</option>
          </select>
        </div>
        <div class="sm:w-52">
          <label for="filtro-rol" class="mb-1.5 block text-sm font-medium text-ink">Rol global</label>
          <select
            uiInput
            id="filtro-rol"
            [ngModel]="roleFilter()"
            (ngModelChange)="onRoleChange($event)"
          >
            <option value="">Todos</option>
            <option value="ADMIN">Administrador</option>
            <option value="LESSON_EDITOR">Editor de lecciones</option>
            <option value="MEMBER">Miembro</option>
          </select>
        </div>
      </div>

      @if (error()) {
        <div class="mt-5">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      }

      <!-- Lista -->
      <div class="mt-6 border-t border-line">
        @if (loading()) {
          <div class="flex items-center gap-2.5 px-1 py-10 text-sm text-ink-muted">
            <ui-spinner [size]="18" />
            <span>Cargando usuarios…</span>
          </div>
        } @else if (users().length === 0) {
          <ui-empty-state
            title="Ningún usuario coincide"
            [description]="
              hasFilters()
                ? 'Prueba con otro término o quita los filtros.'
                : 'Todavía no hay cuentas creadas en la plataforma.'
            "
          >
            @if (hasFilters()) {
              <ui-button variant="secondary" size="sm" (pressed)="clearFilters()">
                Quitar los filtros
              </ui-button>
            }
          </ui-empty-state>
        } @else {
          <ul>
            @for (user of users(); track user.id) {
              <li
                class="-mx-3 rounded-[var(--radius-control)] px-3 transition-colors hover:bg-sunken"
              >
                <div class="grid grid-cols-1 gap-3 border-b border-line py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6">
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-ink">
                    {{ user.full_name }}
                    @if (user.id === session.user()?.id) {
                      <span class="ml-1.5 font-normal text-ink-muted">(tú)</span>
                    }
                  </p>
                  <p class="truncate text-sm text-ink-muted">{{ user.email }}</p>
                  <p class="mt-1 text-xs text-ink-muted">
                    Se unió el {{ user.created_at | bogotaDate }}
                  </p>
                </div>

                <div class="flex flex-wrap items-center gap-2 sm:justify-end">
                  @if (user.status === 'DISABLED') {
                    <ui-badge tone="neutral">{{ statusLabel(user.status) }}</ui-badge>
                  } @else {
                    <ui-badge tone="success">{{ statusLabel(user.status) }}</ui-badge>
                  }

                  <label class="sr-only" [attr.for]="'rol-' + user.id">
                    Rol global de {{ user.full_name }}
                  </label>
                  <select
                    uiInput
                    [compact]="true"
                    class="w-auto"
                    [id]="'rol-' + user.id"
                    [ngModel]="user.global_role"
                    [disabled]="busyId() === user.id"
                    (ngModelChange)="changeRole(user, $event)"
                  >
                    <option value="ADMIN">Administrador</option>
                    <option value="LESSON_EDITOR">Editor de lecciones</option>
                    <option value="MEMBER">Miembro</option>
                  </select>

                  <ui-button
                    size="sm"
                    [variant]="user.status === 'ACTIVE' ? 'secondary' : 'primary'"
                    [loading]="busyId() === user.id"
                    (pressed)="toggleStatus(user)"
                  >
                    {{ user.status === 'ACTIVE' ? 'Desactivar' : 'Activar' }}
                  </ui-button>
                </div>
                </div>
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
                Página {{ page() }} de {{ totalPages() }} · {{ total() }} usuarios
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
export class UsersPage {
  protected readonly session = inject(SessionService);
  private readonly usersApi = inject(UsersApi);

  protected readonly users = signal<UserListItem[]>([]);
  protected readonly total = signal(0);
  protected readonly page = signal(1);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly busyId = signal<string | null>(null);

  protected readonly search = signal('');
  protected readonly statusFilter = signal<UserStatus | ''>('');
  protected readonly roleFilter = signal<GlobalRole | ''>('');

  protected readonly totalPages = computed(() => Math.max(1, Math.ceil(this.total() / PAGE_SIZE)));
  protected readonly hasFilters = computed(
    () => this.search() !== '' || this.statusFilter() !== '' || this.roleFilter() !== '',
  );

  private searchTimer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.load();
  }

  protected statusLabel(status: UserStatus | null): string {
    return status ? USER_STATUS_LABEL[status] : '';
  }

  /** La búsqueda espera a que el usuario deje de escribir: una petición por
   * pulsación saturaría un backend que además puede estar despertando. */
  protected onSearchChange(value: string): void {
    this.search.set(value);
    if (this.searchTimer) clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.page.set(1);
      this.load();
    }, 300);
  }

  protected onStatusChange(value: UserStatus | ''): void {
    this.statusFilter.set(value);
    this.page.set(1);
    this.load();
  }

  protected onRoleChange(value: GlobalRole | ''): void {
    this.roleFilter.set(value);
    this.page.set(1);
    this.load();
  }

  protected clearFilters(): void {
    this.search.set('');
    this.statusFilter.set('');
    this.roleFilter.set('');
    this.page.set(1);
    this.load();
  }

  protected goTo(page: number): void {
    this.page.set(page);
    this.load();
  }

  protected changeRole(user: UserListItem, role: GlobalRole): void {
    if (role === user.global_role) return;
    this.error.set('');
    this.busyId.set(user.id);

    this.usersApi.changeRole(user.id, role).subscribe({
      next: (updated) => {
        this.busyId.set(null);
        this.replace(user.id, { global_role: updated.global_role });
      },
      error: (err: ApiError) => {
        this.busyId.set(null);
        this.error.set(err.message);
        // Devuelve el selector a su valor real: el cambio no ocurrió.
        this.replace(user.id, { global_role: user.global_role });
      },
    });
  }

  protected toggleStatus(user: UserListItem): void {
    const next: UserStatus = user.status === 'ACTIVE' ? 'DISABLED' : 'ACTIVE';
    this.error.set('');
    this.busyId.set(user.id);

    this.usersApi.changeStatus(user.id, next).subscribe({
      next: (updated) => {
        this.busyId.set(null);
        this.replace(user.id, { status: updated.status });
      },
      error: (err: ApiError) => {
        this.busyId.set(null);
        this.error.set(err.message);
      },
    });
  }

  private replace(userId: string, patch: Partial<UserListItem>): void {
    this.users.update((list) =>
      list.map((user) => (user.id === userId ? { ...user, ...patch } : user)),
    );
  }

  private load(): void {
    this.loading.set(true);
    this.error.set('');

    this.usersApi
      .list({
        search: this.search() || undefined,
        status: this.statusFilter() || undefined,
        global_role: this.roleFilter() || undefined,
        page: this.page(),
        size: PAGE_SIZE,
      })
      .subscribe({
        next: (result) => {
          this.users.set(result.items);
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
