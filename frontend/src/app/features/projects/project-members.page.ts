import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiError } from '../../core/api/api-error';
import { ProjectMember, ProjectRole, UserListItem } from '../../core/api/models';
import { ProjectsApi } from '../../core/api/projects.api';
import { UsersApi } from '../../core/api/users.api';
import { SessionService } from '../../core/auth/session.service';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../shared/ui/alert.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { ProjectStore } from './project.store';
import { RoleChipComponent } from './role-chip.component';

/**
 * Miembros del proyecto (RF-15, RF-16, RF-17).
 *
 * Desde aquí solo se agrega gente que ya existe en la plataforma: invitar a
 * alguien nuevo es cosa del administrador, en otra pantalla.
 *
 * La regla del último líder (RN-14) la impone el backend con un 409
 * `LAST_PROJECT_ADMIN`. No se replica aquí: sería una segunda fuente de verdad
 * que se desincroniza en cuanto alguien cree un rol con `project.archive`.
 */
@Component({
  selector: 'app-project-members-page',
  imports: [
    FormsModule,
    BogotaDatePipe,
    AlertComponent,
    ButtonComponent,
    EmptyStateComponent,
    InputDirective,
    RoleChipComponent,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="py-6">
      @if (error()) {
        <div class="mb-5">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      }

      @if (store.can('member.add')) {
        <form
          class="mb-6 rounded-[var(--radius-panel)] border border-line bg-surface p-4 sm:p-5"
          (ngSubmit)="add()"
        >
          <h2 class="text-sm font-semibold text-ink">Agregar a alguien del semillero</h2>
          <div class="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end">
            <div class="flex-1">
              <label for="nuevo-miembro" class="mb-1.5 block text-sm font-medium text-ink">
                Persona
              </label>
              <select uiInput id="nuevo-miembro" name="persona" [(ngModel)]="newUserId">
                <option value="">Elige a una persona</option>
                @for (candidate of candidates(); track candidate.id) {
                  <option [value]="candidate.id">
                    {{ candidate.full_name }} · {{ candidate.email }}
                  </option>
                }
              </select>
            </div>
            <div class="sm:w-52">
              <label for="nuevo-rol" class="mb-1.5 block text-sm font-medium text-ink">Rol</label>
              <select uiInput id="nuevo-rol" name="rol" [(ngModel)]="newRoleId">
                @for (role of roles(); track role.id) {
                  <option [value]="role.id">{{ role.name }}</option>
                }
              </select>
            </div>
            <ui-button type="submit" [loading]="adding()" [disabled]="!newUserId">
              Agregar
            </ui-button>
          </div>
          @if (candidates().length === 0 && !loading()) {
            <p class="mt-3 text-sm text-ink-muted">
              Ya están todas las personas activas de la plataforma en este proyecto.
            </p>
          }
        </form>
      }

      @if (loading()) {
        <div class="flex items-center gap-2.5 py-10 text-sm text-ink-muted">
          <ui-spinner [size]="18" />
          <span>Cargando miembros…</span>
        </div>
      } @else if (members().length === 0) {
        <ui-empty-state
          title="Este proyecto no tiene miembros"
          description="Agrega a quienes van a trabajar en él y dales el rol que corresponda."
        />
      } @else {
        <ul class="border-t border-line">
          @for (member of members(); track member.user.id) {
            <li
              class="-mx-3 rounded-[var(--radius-control)] px-3 transition-colors hover:bg-sunken"
            >
              <div
                class="grid grid-cols-1 gap-3 border-b border-line py-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center sm:gap-6"
              >
                <div class="min-w-0">
                  <p class="truncate text-sm font-medium text-ink">
                    {{ member.user.full_name }}
                    @if (member.user.id === session.user()?.id) {
                      <span class="ml-1.5 font-normal text-ink-muted">(tú)</span>
                    }
                  </p>
                  <p class="truncate text-sm text-ink-muted">{{ member.user.email }}</p>
                  <p class="mt-1 text-xs text-ink-muted">
                    Se unió el {{ member.joined_at | bogotaDate }}
                  </p>
                </div>

                <div class="flex flex-wrap items-center gap-2 sm:justify-end">
                  @if (store.can('role.assign')) {
                    <label class="sr-only" [attr.for]="'rol-' + member.user.id">
                      Rol de {{ member.user.full_name }}
                    </label>
                    <select
                      uiInput
                      [compact]="true"
                      class="w-auto"
                      [id]="'rol-' + member.user.id"
                      [ngModel]="member.role.id"
                      [disabled]="busyId() === member.user.id"
                      (ngModelChange)="changeRole(member, $event)"
                    >
                      @for (role of roles(); track role.id) {
                        <option [value]="role.id">{{ role.name }}</option>
                      }
                    </select>
                  } @else {
                    <app-role-chip [name]="member.role.name" [color]="member.role.color" />
                  }

                  @if (store.can('member.remove')) {
                    @if (confirmingId() === member.user.id) {
                      <ui-button
                        size="sm"
                        variant="danger"
                        [loading]="busyId() === member.user.id"
                        (pressed)="remove(member)"
                      >
                        Sí, retirar
                      </ui-button>
                      <ui-button size="sm" variant="ghost" (pressed)="confirmingId.set(null)">
                        Cancelar
                      </ui-button>
                    } @else {
                      <ui-button
                        size="sm"
                        variant="secondary"
                        (pressed)="confirmingId.set(member.user.id)"
                      >
                        Retirar
                      </ui-button>
                    }
                  }
                </div>
              </div>
            </li>
          }
        </ul>
      }
    </div>
  `,
})
export class ProjectMembersPage {
  protected readonly store = inject(ProjectStore);
  protected readonly session = inject(SessionService);
  private readonly api = inject(ProjectsApi);
  private readonly usersApi = inject(UsersApi);

  protected readonly members = signal<ProjectMember[]>([]);
  protected readonly roles = signal<ProjectRole[]>([]);
  private readonly allUsers = signal<UserListItem[]>([]);
  protected readonly loading = signal(true);
  protected readonly adding = signal(false);
  protected readonly error = signal('');
  protected readonly busyId = signal<string | null>(null);
  /** Confirmación en sitio antes de retirar: la acción no se deshace sola, hay
   * que volver a agregar a la persona. */
  protected readonly confirmingId = signal<string | null>(null);

  protected newUserId = '';
  protected newRoleId = '';

  /** Solo se ofrece a quien todavía no es miembro: agregar dos veces a la misma
   * persona devuelve 409, y ofrecerlo sería invitar al error. */
  protected readonly candidates = computed(() => {
    const taken = new Set(this.members().map((m) => m.user.id));
    return this.allUsers().filter((user) => !taken.has(user.id));
  });

  constructor() {
    this.load();
  }

  protected add(): void {
    const project = this.store.project();
    if (!project || !this.newUserId || !this.newRoleId) return;
    this.adding.set(true);
    this.error.set('');

    this.api.addMember(project.id, this.newUserId, this.newRoleId).subscribe({
      next: (member) => {
        this.adding.set(false);
        this.newUserId = '';
        this.members.update((list) => [...list, member]);
        this.store.refresh();
      },
      error: (err: ApiError) => {
        this.adding.set(false);
        this.error.set(err.message);
      },
    });
  }

  protected changeRole(member: ProjectMember, roleId: string): void {
    const project = this.store.project();
    if (!project || roleId === member.role.id) return;
    this.busyId.set(member.user.id);
    this.error.set('');

    this.api.changeMemberRole(project.id, member.user.id, roleId).subscribe({
      next: (updated) => {
        this.busyId.set(null);
        this.replace(member.user.id, updated);
        // Cambiarse el rol a uno mismo cambia los permisos propios.
        if (member.user.id === this.session.user()?.id) this.store.refresh();
      },
      error: (err: ApiError) => {
        this.busyId.set(null);
        this.error.set(err.message);
        // Devuelve el selector a su valor real: el cambio no ocurrió.
        this.replace(member.user.id, { ...member });
      },
    });
  }

  protected remove(member: ProjectMember): void {
    const project = this.store.project();
    if (!project) return;
    this.busyId.set(member.user.id);
    this.error.set('');

    this.api.removeMember(project.id, member.user.id).subscribe({
      next: () => {
        this.busyId.set(null);
        this.confirmingId.set(null);
        this.members.update((list) => list.filter((m) => m.user.id !== member.user.id));
        this.store.refresh();
      },
      error: (err: ApiError) => {
        this.busyId.set(null);
        this.confirmingId.set(null);
        this.error.set(err.message);
      },
    });
  }

  private replace(userId: string, member: ProjectMember): void {
    this.members.update((list) => list.map((m) => (m.user.id === userId ? member : m)));
  }

  private load(): void {
    const project = this.store.project();
    if (!project) return;
    this.loading.set(true);

    this.api.members(project.id).subscribe({
      next: (members) => {
        this.members.set(members);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.loading.set(false);
        this.error.set(err.message);
      },
    });

    this.api.roles(project.id).subscribe({
      next: (roles) => {
        this.roles.set(roles);
        this.newRoleId = roles.find((role) => role.name === 'Colaborador')?.id ?? roles[0]?.id ?? '';
      },
      error: () => undefined,
    });

    if (this.store.can('member.add')) {
      this.usersApi.list({ status: 'ACTIVE', size: 100 }).subscribe({
        next: (result) => this.allUsers.set(result.items),
        error: () => undefined,
      });
    }
  }
}
