import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable } from 'rxjs';

import { ApiError, fieldMessage } from '../../core/api/api-error';
import { LessonsApi } from '../../core/api/lessons.api';
import { LessonModule } from '../../core/api/models';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { DialogComponent } from '../../shared/ui/dialog.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { canMove, moveBy } from './ordering';

/** Lo que el backend manda en `details` al pedir confirmación (RN-36). */
interface DeletionWarning {
  moduleId: string;
  title: string;
  lessons: number;
}

/**
 * Editor del catálogo: los módulos (RF-47, RF-49, RF-50).
 *
 * Las lecciones de cada módulo tienen su propia pantalla en vez de desplegarse
 * aquí dentro. Anidarlas obligaría a meter una tarjeta dentro de otra, que es
 * uno de los antipatrones que `DESIGN.md` prohíbe, y dejaría una pantalla que
 * hace tres cosas a la vez.
 *
 * Reordenar va con botones y no arrastrando: ver `ordering.ts`.
 */
@Component({
  selector: 'app-lesson-editor-page',
  imports: [
    FormsModule,
    RouterLink,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    DialogComponent,
    EmptyStateComponent,
    FieldComponent,
    InputDirective,
    PageHeaderComponent,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
      <a
        routerLink="/lecciones"
        class="inline-flex min-h-11 items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
      >
        <span aria-hidden="true">←</span> Ver el catálogo
      </a>

      <div class="mt-4">
        <ui-page-header
          title="Editar el catálogo"
          description="Los módulos agrupan las lecciones. Un módulo en borrador esconde todo lo que tiene dentro, aunque sus lecciones estén publicadas."
        >
          <ui-button [variant]="formOpen() ? 'secondary' : 'primary'" (pressed)="toggleForm()">
            {{ formOpen() ? 'Cancelar' : 'Agregar módulo' }}
          </ui-button>
        </ui-page-header>
      </div>

      @if (formOpen()) {
        <form
          class="mt-6 rounded-[var(--radius-panel)] border border-line bg-surface p-5 sm:p-6"
          (ngSubmit)="save()"
        >
          <h2 class="text-base font-semibold text-ink">
            {{ editing() ? 'Editar módulo' : 'Nuevo módulo' }}
          </h2>

          <div class="mt-5 grid gap-4">
            <ui-field label="Título" for="titulo" [error]="formError()">
              <input
                uiInput
                id="titulo"
                name="titulo"
                required
                minlength="3"
                maxlength="150"
                autocomplete="off"
                [(ngModel)]="title"
                [invalid]="!!formError()"
              />
            </ui-field>
            <ui-field
              label="Descripción"
              for="descripcion"
              [optional]="true"
              hint="Una línea que diga de qué trata. Se ve en el catálogo."
            >
              <textarea
                uiInput
                id="descripcion"
                name="descripcion"
                rows="2"
                maxlength="2000"
                [(ngModel)]="description"
              ></textarea>
            </ui-field>
          </div>

          <div class="mt-5 flex gap-2">
            <ui-button type="submit" [loading]="saving()">
              {{ editing() ? 'Guardar' : 'Crear' }}
            </ui-button>
            <ui-button variant="ghost" (pressed)="toggleForm()">Cancelar</ui-button>
          </div>
        </form>
      }

      @if (error()) {
        <div class="mt-6">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      }

      @if (loading()) {
        <div class="flex items-center gap-2 py-12 text-sm text-ink-muted">
          <ui-spinner />
          Cargando el catálogo…
        </div>
      } @else if (modules().length === 0) {
        <ui-empty-state
          title="El catálogo está vacío"
          description="Crea un módulo, agrégale lecciones y publícalo cuando esté listo. Nadie lo ve hasta entonces."
        />
      } @else {
        <ul class="mt-8 divide-y divide-line border-y border-line">
          @for (module of modules(); track module.id; let i = $index) {
            <li class="flex flex-col gap-3 py-4 sm:flex-row sm:items-start sm:justify-between">
              <div class="min-w-0">
                <div class="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                  <a
                    [routerLink]="['/lecciones/editor', module.id]"
                    class="text-sm font-medium text-ink hover:text-accent hover:underline"
                  >
                    {{ module.title }}
                  </a>
                  <ui-badge [tone]="module.is_published ? 'success' : 'notice'">
                    {{ module.is_published ? 'Publicado' : 'Borrador' }}
                  </ui-badge>
                </div>
                @if (module.description) {
                  <p class="mt-1 line-clamp-2 max-w-prose text-sm text-ink-muted">
                    {{ module.description }}
                  </p>
                }
                <p class="mt-1 text-xs text-ink-faint">{{ lessonLabel(module.lessons.length) }}</p>
              </div>

              <div class="flex shrink-0 flex-wrap items-center gap-1">
                <button
                  type="button"
                  [class]="iconButton"
                  [disabled]="!canMoveUp(i) || busy()"
                  (click)="move(i, -1)"
                >
                  <span class="sr-only">Subir {{ module.title }}</span>
                  <span aria-hidden="true">↑</span>
                </button>
                <button
                  type="button"
                  [class]="iconButton"
                  [disabled]="!canMoveDown(i) || busy()"
                  (click)="move(i, 1)"
                >
                  <span class="sr-only">Bajar {{ module.title }}</span>
                  <span aria-hidden="true">↓</span>
                </button>
                <ui-button
                  size="sm"
                  variant="secondary"
                  [disabled]="busy()"
                  (pressed)="togglePublished(module)"
                >
                  {{ module.is_published ? 'Retirar' : 'Publicar' }}
                </ui-button>
                <ui-button size="sm" variant="ghost" [disabled]="busy()" (pressed)="edit(module)">
                  Editar
                </ui-button>
                <ui-button
                  size="sm"
                  variant="ghost"
                  [disabled]="busy()"
                  (pressed)="askDelete(module)"
                >
                  Eliminar
                </ui-button>
              </div>
            </li>
          }
        </ul>
      }

      <ui-dialog
        [open]="warning() !== null"
        label="Confirmar la eliminación del módulo"
        (closed)="warning.set(null)"
      >
        @if (warning(); as pending) {
          <h2 class="text-lg font-semibold text-ink">Eliminar «{{ pending.title }}»</h2>
          <p class="mt-3 text-sm leading-relaxed text-ink-muted">
            {{ deletionMessage(pending.lessons) }}
          </p>
          <div class="mt-6 flex flex-wrap gap-2">
            <ui-button variant="danger" [loading]="busy()" (pressed)="confirmDelete(pending)">
              Eliminar
            </ui-button>
            <ui-button variant="secondary" (pressed)="warning.set(null)">Cancelar</ui-button>
          </div>
        }
      </ui-dialog>
    </div>
  `,
})
export class LessonEditorPage {
  private readonly api = inject(LessonsApi);

  protected readonly modules = signal<LessonModule[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly busy = signal(false);

  protected readonly formOpen = signal(false);
  protected readonly editing = signal<LessonModule | null>(null);
  protected readonly saving = signal(false);
  protected readonly formError = signal('');
  protected readonly warning = signal<DeletionWarning | null>(null);

  protected title = '';
  protected description = '';

  /** El mismo botón cuadrado de 44 px para subir y bajar. */
  protected readonly iconButton =
    'grid size-11 place-items-center rounded-[var(--radius-control)] text-ink-muted ' +
    'transition-colors hover:bg-sunken hover:text-ink disabled:text-ink-faint ' +
    'disabled:hover:bg-transparent disabled:cursor-not-allowed';

  private readonly count = computed(() => this.modules().length);

  constructor() {
    this.load();
  }

  protected canMoveUp(index: number): boolean {
    return canMove(this.count(), index, -1);
  }

  protected canMoveDown(index: number): boolean {
    return canMove(this.count(), index, 1);
  }

  protected lessonLabel(count: number): string {
    if (count === 0) return 'Sin lecciones';
    return count === 1 ? '1 lección' : `${count} lecciones`;
  }

  protected deletionMessage(lessons: number): string {
    if (lessons === 0) return 'El módulo no tiene lecciones. Esta acción no se puede deshacer.';
    const cuantas = lessons === 1 ? '1 lección' : `${lessons} lecciones`;
    return `Se eliminarán también ${cuantas} con todos sus recursos. Esta acción no se puede deshacer.`;
  }

  protected toggleForm(): void {
    const next = !this.formOpen();
    this.formOpen.set(next);
    if (!next) this.reset();
  }

  protected edit(module: LessonModule): void {
    this.editing.set(module);
    this.title = module.title;
    this.description = module.description ?? '';
    this.formError.set('');
    this.formOpen.set(true);
  }

  protected save(): void {
    const body = {
      title: this.title.trim(),
      description: this.description.trim() || null,
    };
    const target = this.editing();
    const request = target ? this.api.updateModule(target.id, body) : this.api.createModule(body);

    this.saving.set(true);
    this.formError.set('');
    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.formOpen.set(false);
        this.reset();
        this.load();
      },
      error: (err: ApiError) => {
        this.formError.set(fieldMessage(err));
        this.saving.set(false);
      },
    });
  }

  protected togglePublished(module: LessonModule): void {
    this.run(this.api.publishModule(module.id, !module.is_published));
  }

  /**
   * Reordena en la pantalla y manda el orden completo.
   *
   * La lista se pinta como quedó antes de que responda el servidor: el
   * movimiento tiene que sentirse inmediato, y si la petición falla la recarga
   * del `run` devuelve el orden real.
   */
  protected move(index: number, delta: number): void {
    const reordered = moveBy(this.modules(), index, delta);
    this.modules.set(reordered);
    this.run(this.api.reorderModules(reordered.map((module) => module.id)));
  }

  /**
   * Pide el borrado sin confirmar, a propósito.
   *
   * El 409 que responde el backend trae el conteo exacto de lecciones que se
   * perderían (RN-36), y ese número es justo lo que hay que enseñar antes de
   * preguntar. Contarlas aquí con lo que tenga cargada la pantalla sería
   * arriesgarse a decir «3» cuando otro editor ya agregó la cuarta.
   */
  protected askDelete(module: LessonModule): void {
    this.busy.set(true);
    this.error.set('');
    this.api.deleteModule(module.id).subscribe({
      next: () => {
        // No debería ocurrir: el backend siempre exige confirmación.
        this.busy.set(false);
        this.load();
      },
      error: (err: ApiError) => {
        this.busy.set(false);
        if (err.is('CONFIRMATION_REQUIRED')) {
          const details = err.details as { lessons?: number } | null;
          this.warning.set({
            moduleId: module.id,
            title: module.title,
            lessons: details?.lessons ?? 0,
          });
          return;
        }
        this.error.set(err.message);
      },
    });
  }

  protected confirmDelete(pending: DeletionWarning): void {
    this.run(this.api.deleteModule(pending.moduleId, true), () => this.warning.set(null));
  }

  private run(request: Observable<unknown>, done?: () => void): void {
    this.busy.set(true);
    this.error.set('');
    request.subscribe({
      next: () => {
        this.busy.set(false);
        done?.();
        this.load();
      },
      error: (err: ApiError) => {
        this.error.set(err.message);
        this.busy.set(false);
        done?.();
        // Recargar también al fallar: la pantalla pudo pintar un orden que el
        // servidor no aceptó, y dejarlo ahí sería mentir.
        this.load();
      },
    });
  }

  private reset(): void {
    this.editing.set(null);
    this.title = '';
    this.description = '';
    this.formError.set('');
  }

  private load(): void {
    this.api.catalog().subscribe({
      next: (modules) => {
        this.modules.set(modules);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err.message);
        this.loading.set(false);
      },
    });
  }
}
