import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiError } from '../../core/api/api-error';
import {
  PERMISSION_CATEGORY_LABEL,
  Permission,
  PermissionCategory,
  PermissionCode,
  ProjectRole,
  VIEW_PERMISSION,
} from '../../core/api/models';
import { ProjectsApi } from '../../core/api/projects.api';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { ProjectStore } from './project.store';
import { RoleChipComponent } from './role-chip.component';

/** Paleta sugerida para los roles nuevos. Son colores propios del rol, no
 * tokens del sistema de diseño: quien crea el rol elige el suyo. */
const ROLE_COLORS = ['#B8860B', '#1F6F5C', '#2E5C8A', '#7A3E9D', '#A8442A', '#6B6B6B'];

interface PermissionGroup {
  category: PermissionCategory;
  label: string;
  items: Permission[];
}

/**
 * Roles del proyecto y su editor de permisos (RF-20 a RF-24).
 *
 * El catálogo se pide al backend: es una lista cerrada de 14 códigos y esta
 * pantalla no inventa ninguno. `task.view` va marcado y bloqueado, porque sin él
 * el rol no tiene sentido y el backend lo rechaza (RN-05).
 */
@Component({
  selector: 'app-project-roles-page',
  imports: [
    FormsModule,
    BogotaDatePipe,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    EmptyStateComponent,
    FieldComponent,
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

      @if (loading()) {
        <div class="flex items-center gap-2.5 py-10 text-sm text-ink-muted">
          <ui-spinner [size]="18" />
          <span>Cargando roles…</span>
        </div>
      } @else {
        @if (store.can('role.manage') && !editorOpen()) {
          <div class="mb-6">
            <ui-button (pressed)="openEditor(null)">Crear un rol</ui-button>
          </div>
        }

        @if (editorOpen()) {
          <form
            class="mb-6 rounded-[var(--radius-panel)] border border-line bg-surface p-5 sm:p-6"
            (ngSubmit)="save()"
          >
            <h2 class="text-base font-semibold text-ink">
              {{ editingId() ? 'Editar el rol' : 'Nuevo rol' }}
            </h2>
            <p class="mt-1 text-sm text-ink-muted">
              Elige exactamente lo que este rol puede hacer. Los permisos no se implican
              entre sí.
            </p>

            <div class="mt-5 grid gap-4 sm:grid-cols-[minmax(0,1fr)_auto]">
              <ui-field label="Nombre" for="rol-nombre">
                <input
                  uiInput
                  id="rol-nombre"
                  name="nombre"
                  required
                  minlength="2"
                  maxlength="40"
                  placeholder="Revisor"
                  [(ngModel)]="form.name"
                />
              </ui-field>

              <fieldset class="min-w-0">
                <legend class="mb-1.5 text-sm font-medium text-ink">Color</legend>
                <div class="flex flex-wrap gap-2">
                  @for (color of colors; track color) {
                    <!-- El radio real va oculto, así que el foco tiene que
                         verse en la etiqueta: si no, quien navega con el teclado
                         no sabe dónde está. -->
                    <label
                      class="flex size-11 cursor-pointer items-center justify-center rounded-[var(--radius-control)] border-2 transition-colors has-[:focus-visible]:outline has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-2 has-[:focus-visible]:outline-accent"
                      [class.border-accent]="form.color === color"
                      [class.border-line]="form.color !== color"
                    >
                      <input
                        type="radio"
                        name="color"
                        class="sr-only"
                        [value]="color"
                        [(ngModel)]="form.color"
                      />
                      <span class="sr-only">Color {{ color }}</span>
                      <span
                        class="size-5 rounded-full"
                        [style.background-color]="color"
                        aria-hidden="true"
                      ></span>
                    </label>
                  }
                </div>
              </fieldset>
            </div>

            <fieldset class="mt-6">
              <legend class="text-sm font-medium text-ink">Permisos</legend>
              <div class="mt-3 grid gap-5 sm:grid-cols-2">
                @for (group of groups(); track group.category) {
                  <div>
                    <p class="text-xs font-medium tracking-wide text-ink-muted uppercase">
                      {{ group.label }}
                    </p>
                    <ul class="mt-2 flex flex-col gap-1">
                      @for (permission of group.items; track permission.code) {
                        <li>
                          <label
                            class="flex min-h-11 cursor-pointer items-start gap-2.5 rounded-[var(--radius-control)] px-2 py-2 transition-colors hover:bg-sunken"
                          >
                            <input
                              type="checkbox"
                              class="mt-0.5 size-4 shrink-0 accent-[var(--color-accent)]"
                              [checked]="selected().has(permission.code)"
                              [disabled]="permission.code === viewPermission"
                              (change)="toggle(permission.code)"
                            />
                            <span class="min-w-0">
                              <span class="block text-sm text-ink">
                                {{ permission.description }}
                                @if (permission.code === viewPermission) {
                                  <span class="text-ink-muted">· obligatorio</span>
                                }
                              </span>
                              <code class="text-xs text-ink-muted">{{ permission.code }}</code>
                            </span>
                          </label>
                        </li>
                      }
                    </ul>
                  </div>
                }
              </div>
            </fieldset>

            @if (formError()) {
              <div class="mt-4">
                <ui-alert tone="error">{{ formError() }}</ui-alert>
              </div>
            }

            <div class="mt-5 flex flex-col gap-2 sm:flex-row-reverse">
              <ui-button type="submit" [loading]="saving()">
                {{ editingId() ? 'Guardar cambios' : 'Crear el rol' }}
              </ui-button>
              <ui-button variant="ghost" (pressed)="closeEditor()">Cancelar</ui-button>
            </div>
          </form>
        }

        @if (roles().length === 0) {
          <ui-empty-state
            title="Este proyecto no tiene roles"
            description="Algo salió mal: todo proyecto nace con Líder, Colaborador y Observador."
          />
        } @else {
          <ul class="flex flex-col gap-3">
            @for (role of roles(); track role.id) {
              <li class="rounded-[var(--radius-panel)] border border-line bg-surface p-4 sm:p-5">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-center gap-2">
                      <app-role-chip [name]="role.name" [color]="role.color" />
                      @if (role.is_system) {
                        <ui-badge tone="neutral">Predeterminado</ui-badge>
                      }
                      <span class="text-xs text-ink-muted">
                        {{ role.member_count }}
                        {{ role.member_count === 1 ? 'miembro' : 'miembros' }}
                      </span>
                    </div>

                    <p class="mt-2 max-w-prose text-sm text-ink-muted">
                      {{ role.permissions.length }}
                      {{ role.permissions.length === 1 ? 'permiso' : 'permisos' }}:
                      {{ describe(role) }}
                    </p>

                    @if (role.created_by; as author) {
                      <p class="mt-1.5 text-xs text-ink-muted">
                        Creado por {{ author.full_name }} el {{ role.created_at | bogotaDate }}
                      </p>
                    }
                  </div>

                  @if (store.can('role.manage') && !role.is_system) {
                    <div class="flex shrink-0 gap-2">
                      <ui-button size="sm" variant="secondary" (pressed)="openEditor(role)">
                        Editar
                      </ui-button>
                      @if (confirmingId() === role.id) {
                        <ui-button
                          size="sm"
                          variant="danger"
                          [loading]="busyId() === role.id"
                          (pressed)="remove(role)"
                        >
                          Sí, eliminar
                        </ui-button>
                        <ui-button size="sm" variant="ghost" (pressed)="confirmingId.set(null)">
                          Cancelar
                        </ui-button>
                      } @else {
                        <ui-button
                          size="sm"
                          variant="ghost"
                          (pressed)="confirmingId.set(role.id)"
                        >
                          Eliminar
                        </ui-button>
                      }
                    </div>
                  }
                </div>
              </li>
            }
          </ul>
        }
      }
    </div>
  `,
})
export class ProjectRolesPage {
  protected readonly store = inject(ProjectStore);
  private readonly api = inject(ProjectsApi);

  protected readonly viewPermission = VIEW_PERMISSION;
  protected readonly colors = ROLE_COLORS;

  protected readonly roles = signal<ProjectRole[]>([]);
  protected readonly catalog = signal<Permission[]>([]);
  protected readonly loading = signal(true);
  protected readonly saving = signal(false);
  protected readonly error = signal('');
  protected readonly formError = signal('');
  protected readonly busyId = signal<string | null>(null);
  /** Eliminar un rol pide confirmación en sitio, no un cuadro de diálogo del
   * navegador: se ve dónde va a pasar y no bloquea la pestaña. */
  protected readonly confirmingId = signal<string | null>(null);

  protected readonly editorOpen = signal(false);
  protected readonly editingId = signal<string | null>(null);
  protected readonly selected = signal<Set<PermissionCode>>(new Set([VIEW_PERMISSION]));
  protected form = { name: '', color: ROLE_COLORS[0] };

  /** El catálogo agrupado por categoría, en el orden en que se lee mejor. */
  protected readonly groups = computed<PermissionGroup[]>(() => {
    const order: PermissionCategory[] = ['task', 'member', 'role', 'project'];
    return order
      .map((category) => ({
        category,
        label: PERMISSION_CATEGORY_LABEL[category],
        items: this.catalog().filter((permission) => permission.category === category),
      }))
      .filter((group) => group.items.length > 0);
  });

  constructor() {
    this.load();
  }

  /** Resume un rol en una línea.
   *
   * Se listan los códigos y no las categorías: agrupar por área hacía que dos
   * roles distintos —Colaborador y Revisor— dijeran lo mismo, "tareas". El
   * código es el vocabulario de esta pantalla, y aparece junto a su descripción
   * en español dentro del editor. */
  protected describe(role: ProjectRole): string {
    const catalog = this.catalog();
    if (catalog.length > 0 && role.permissions.length === catalog.length) {
      return 'todo el catálogo';
    }
    return role.permissions.join(', ');
  }

  protected toggle(code: PermissionCode): void {
    if (code === VIEW_PERMISSION) return; // RN-05: no se puede quitar
    this.selected.update((current) => {
      const next = new Set(current);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      return next;
    });
  }

  protected openEditor(role: ProjectRole | null): void {
    this.formError.set('');
    this.editingId.set(role?.id ?? null);
    this.form = {
      name: role?.name ?? '',
      color: role?.color ?? ROLE_COLORS[0],
    };
    this.selected.set(new Set(role?.permissions ?? [VIEW_PERMISSION]));
    this.editorOpen.set(true);
  }

  protected closeEditor(): void {
    this.editorOpen.set(false);
    this.editingId.set(null);
    this.formError.set('');
  }

  protected save(): void {
    const project = this.store.project();
    if (!project) return;
    if (this.form.name.trim().length < 2) {
      this.formError.set('El nombre del rol necesita al menos 2 caracteres.');
      return;
    }

    this.saving.set(true);
    this.formError.set('');
    const body = {
      name: this.form.name.trim(),
      color: this.form.color,
      permissions: [...this.selected()],
    };
    const roleId = this.editingId();
    const request = roleId
      ? this.api.updateRole(project.id, roleId, body)
      : this.api.createRole(project.id, body);

    request.subscribe({
      next: (role) => {
        this.saving.set(false);
        this.closeEditor();
        this.roles.update((list) =>
          roleId ? list.map((r) => (r.id === role.id ? role : r)) : [...list, role],
        );
        // Editar un rol puede cambiar los permisos propios de inmediato (RN-22).
        this.store.refresh();
      },
      error: (err: ApiError) => {
        this.saving.set(false);
        this.formError.set(err.message);
      },
    });
  }

  protected remove(role: ProjectRole): void {
    const project = this.store.project();
    if (!project) return;
    this.busyId.set(role.id);
    this.error.set('');

    this.api.deleteRole(project.id, role.id).subscribe({
      next: () => {
        this.busyId.set(null);
        this.confirmingId.set(null);
        this.roles.update((list) => list.filter((r) => r.id !== role.id));
      },
      error: (err: ApiError) => {
        this.busyId.set(null);
        this.confirmingId.set(null);
        // Un rol con miembros no se borra: el mensaje del backend trae el conteo
        // exacto de a cuántos hay que reasignar primero (RN-21, EB-05).
        this.error.set(err.message);
      },
    });
  }

  private load(): void {
    const project = this.store.project();
    if (!project) return;
    this.loading.set(true);

    this.api.roles(project.id).subscribe({
      next: (roles) => {
        this.roles.set(roles);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.loading.set(false);
        this.error.set(err.message);
      },
    });

    this.api.permissions().subscribe({
      next: (catalog) => this.catalog.set(catalog),
      error: () => undefined,
    });
  }
}
