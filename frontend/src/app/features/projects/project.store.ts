/**
 * Estado del proyecto abierto, compartido entre el armazón y sus pestañas.
 *
 * Se carga una sola vez al entrar y se recarga cuando algo lo cambia, para que
 * `my_permissions` no se quede viejo: los permisos de un rol pueden cambiar en
 * cualquier momento y surten efecto de inmediato (RN-22).
 *
 * `can()` decide qué se muestra, no qué se permite. La autorización real ocurre
 * en el backend, en cada petición (RNF-05).
 */
import { Injectable, computed, inject, signal } from '@angular/core';

import { ApiError } from '../../core/api/api-error';
import { PermissionCode, ProjectDetail, VIEW_PERMISSION } from '../../core/api/models';
import { ProjectsApi } from '../../core/api/projects.api';

@Injectable()
export class ProjectStore {
  private readonly api = inject(ProjectsApi);

  private readonly projectSignal = signal<ProjectDetail | null>(null);
  private readonly loadingSignal = signal(true);
  private readonly errorSignal = signal('');

  readonly project = this.projectSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();

  readonly isArchived = computed(() => this.projectSignal()?.status === 'ARCHIVED');

  /**
   * Si la interfaz debe ofrecer una acción.
   *
   * Un proyecto archivado es de solo lectura (RN-15), no invisible: se consulta
   * completo (RF-18). Por eso `task.view` sigue habilitado y `project.archive`
   * también, que es el permiso que lo desarchiva; el resto se apaga. Es la misma
   * frontera que aplica `require_project_permission` en el backend, y hay que
   * moverlas juntas.
   */
  can(permission: PermissionCode): boolean {
    const project = this.projectSignal();
    if (!project) return false;
    if (!project.my_permissions.includes(permission)) return false;
    if (!this.isArchived()) return true;
    return permission === VIEW_PERMISSION || permission === 'project.archive';
  }

  load(projectId: string): void {
    this.loadingSignal.set(true);
    this.errorSignal.set('');
    this.api.get(projectId).subscribe({
      next: (project) => {
        this.projectSignal.set(project);
        this.loadingSignal.set(false);
      },
      error: (err: ApiError) => {
        this.projectSignal.set(null);
        this.errorSignal.set(err.message);
        this.loadingSignal.set(false);
      },
    });
  }

  /** Reemplaza el proyecto tras una operación que ya devolvió su versión nueva,
   * para no pedir otra vez lo que el backend acaba de responder. */
  set(project: ProjectDetail): void {
    this.projectSignal.set(project);
  }

  /** Vuelve a pedir el detalle sin mostrar el esqueleto de carga: se usa cuando
   * cambia algo que altera los conteos o los permisos propios. */
  refresh(): void {
    const current = this.projectSignal();
    if (!current) return;
    this.api.get(current.id).subscribe({
      next: (project) => this.projectSignal.set(project),
      error: () => undefined,
    });
  }
}
