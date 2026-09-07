import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import { ApiError } from '../../core/api/api-error';
import { ProjectsApi } from '../../core/api/projects.api';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { AlertComponent } from '../../shared/ui/alert.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { ProjectStore } from './project.store';

/**
 * Resumen del proyecto: sus datos, la edición en sitio y el archivado (RF-18).
 *
 * Los botones aparecen según `my_permissions`, que es comodidad; quien llame al
 * endpoint sin el permiso recibe 403 igual.
 */
@Component({
  selector: 'app-project-overview-page',
  imports: [
    FormsModule,
    BogotaDatePipe,
    AlertComponent,
    ButtonComponent,
    FieldComponent,
    InputDirective,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (store.project(); as project) {
      <div class="py-6">
        @if (error()) {
          <div class="mb-5">
            <ui-alert tone="error">{{ error() }}</ui-alert>
          </div>
        }

        @if (editing()) {
          <form
            class="rounded-[var(--radius-panel)] border border-line bg-surface p-5 sm:p-6"
            (ngSubmit)="save()"
          >
            <h2 class="text-base font-semibold text-ink">Editar el proyecto</h2>

            <div class="mt-5 grid gap-4">
              <ui-field label="Nombre" for="editar-nombre">
                <input
                  uiInput
                  id="editar-nombre"
                  name="nombre"
                  required
                  minlength="3"
                  maxlength="120"
                  [(ngModel)]="form.name"
                />
              </ui-field>

              <ui-field label="Descripción" for="editar-descripcion" [optional]="true">
                <textarea
                  uiInput
                  id="editar-descripcion"
                  name="descripcion"
                  rows="3"
                  class="min-h-24 py-2.5"
                  [(ngModel)]="form.description"
                ></textarea>
              </ui-field>

              <ui-field label="Fecha de inicio" for="editar-inicio" [optional]="true">
                <input
                  uiInput
                  id="editar-inicio"
                  name="inicio"
                  type="date"
                  [(ngModel)]="form.startDate"
                />
              </ui-field>
            </div>

            <div class="mt-5 flex flex-col gap-2 sm:flex-row-reverse">
              <ui-button type="submit" [loading]="saving()">Guardar cambios</ui-button>
              <ui-button variant="ghost" (pressed)="editing.set(false)">Cancelar</ui-button>
            </div>
          </form>
        } @else {
          <dl class="grid gap-5 sm:grid-cols-2">
            <div class="sm:col-span-2">
              <dt class="text-xs font-medium tracking-wide text-ink-muted uppercase">
                Descripción
              </dt>
              <dd class="mt-1 max-w-prose text-sm leading-relaxed text-ink">
                {{ project.description || 'Sin descripción.' }}
              </dd>
            </div>

            <div>
              <dt class="text-xs font-medium tracking-wide text-ink-muted uppercase">
                Fecha de inicio
              </dt>
              <dd class="mt-1 text-sm text-ink">
                {{ project.start_date ? (project.start_date | bogotaDate) : 'Sin definir' }}
              </dd>
            </div>

            <div>
              <dt class="text-xs font-medium tracking-wide text-ink-muted uppercase">
                Integrantes
              </dt>
              <dd class="mt-1 text-sm text-ink">
                {{ project.member_count }}
                {{ project.member_count === 1 ? 'persona' : 'personas' }}
              </dd>
            </div>

            @if (project.archived_at) {
              <div>
                <dt class="text-xs font-medium tracking-wide text-ink-muted uppercase">
                  Archivado el
                </dt>
                <dd class="mt-1 text-sm text-ink">{{ project.archived_at | bogotaDate }}</dd>
              </div>
            }
          </dl>

          @if (store.can('project.edit') || canToggleArchive()) {
            <div class="mt-8 flex flex-col gap-2 border-t border-line pt-6 sm:flex-row">
              @if (store.can('project.edit')) {
                <ui-button variant="secondary" (pressed)="startEditing()">
                  Editar el proyecto
                </ui-button>
              }
              @if (canToggleArchive()) {
                <ui-button
                  [variant]="store.isArchived() ? 'primary' : 'secondary'"
                  [loading]="archiving()"
                  (pressed)="toggleArchive()"
                >
                  {{ store.isArchived() ? 'Desarchivar' : 'Archivar el proyecto' }}
                </ui-button>
              }
            </div>
            @if (!store.isArchived() && canToggleArchive()) {
              <p class="mt-2 max-w-prose text-sm text-ink-muted">
                Archivar deja el proyecto de solo lectura y detiene sus recordatorios. Se
                puede deshacer.
              </p>
            }
          }
        }
      </div>
    }
  `,
})
export class ProjectOverviewPage {
  protected readonly store = inject(ProjectStore);
  private readonly api = inject(ProjectsApi);

  protected readonly editing = signal(false);
  protected readonly saving = signal(false);
  protected readonly archiving = signal(false);
  protected readonly error = signal('');
  protected form = { name: '', description: '', startDate: '' };

  /** `project.archive` es el único permiso que sigue vivo con el proyecto
   * archivado, porque es el que lo saca de ahí (RN-15). */
  protected canToggleArchive(): boolean {
    return this.store.project()?.my_permissions.includes('project.archive') ?? false;
  }

  protected startEditing(): void {
    const project = this.store.project();
    if (!project) return;
    this.form = {
      name: project.name,
      description: project.description ?? '',
      startDate: project.start_date ?? '',
    };
    this.error.set('');
    this.editing.set(true);
  }

  protected save(): void {
    const project = this.store.project();
    if (!project) return;
    this.saving.set(true);
    this.error.set('');

    this.api
      .update(project.id, {
        name: this.form.name.trim(),
        description: this.form.description.trim() || null,
        start_date: this.form.startDate || null,
      })
      .subscribe({
        next: (updated) => {
          this.saving.set(false);
          this.editing.set(false);
          this.store.set(updated);
        },
        error: (err: ApiError) => {
          this.saving.set(false);
          this.error.set(err.message);
        },
      });
  }

  protected toggleArchive(): void {
    const project = this.store.project();
    if (!project) return;
    this.archiving.set(true);
    this.error.set('');

    const request = this.store.isArchived()
      ? this.api.unarchive(project.id)
      : this.api.archive(project.id);

    request.subscribe({
      next: (updated) => {
        this.archiving.set(false);
        this.store.set(updated);
      },
      error: (err: ApiError) => {
        this.archiving.set(false);
        this.error.set(err.message);
      },
    });
  }
}
