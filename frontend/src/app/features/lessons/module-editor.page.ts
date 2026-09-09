import { ChangeDetectionStrategy, Component, effect, inject, input, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Observable } from 'rxjs';

import { ApiError, fieldMessage } from '../../core/api/api-error';
import { LessonsApi } from '../../core/api/lessons.api';
import {
  Lesson,
  LessonModule,
  LessonResource,
  RESOURCE_TYPES,
  RESOURCE_TYPE_LABEL,
  ResourceType,
} from '../../core/api/models';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { FieldComponent } from '../../shared/ui/field.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { canMove, moveBy } from './ordering';

/**
 * Las lecciones de un módulo y los recursos de cada lección (RF-48, RF-50).
 *
 * Los recursos se despliegan bajo su lección en vez de tener una tercera
 * pantalla: son una lista de enlaces, no una entidad con vida propia, y
 * mandarlos a otra ruta pondría tres clics entre el editor y pegar una URL.
 * Van sobre fondo hundido y sin borde, para que se lean como un despliegue y no
 * como una tarjeta dentro de otra.
 *
 * No hay `GET /lesson-modules/{id}`: el contrato devuelve el árbol entero de una
 * vez, así que esta pantalla lo pide y se queda con su módulo. Con decenas de
 * módulos como techo, un endpoint más para ahorrar unas filas sería superficie
 * sin ganancia.
 */
@Component({
  selector: 'app-module-editor-page',
  imports: [
    FormsModule,
    RouterLink,
    AlertComponent,
    BadgeComponent,
    ButtonComponent,
    EmptyStateComponent,
    FieldComponent,
    InputDirective,
    SpinnerComponent,
  ],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
      <a
        routerLink="/lecciones/editor"
        class="inline-flex min-h-11 items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
      >
        <span aria-hidden="true">←</span> Volver a los módulos
      </a>

      @if (loading()) {
        <div class="flex items-center gap-2 py-12 text-sm text-ink-muted">
          <ui-spinner />
          Cargando el módulo…
        </div>
      } @else if (!module()) {
        <div class="py-8">
          <ui-alert tone="error">
            {{ error() || 'Este módulo no existe o fue eliminado.' }}
          </ui-alert>
        </div>
      } @else if (module(); as current) {
        <header
          class="mt-4 flex flex-col gap-4 border-b border-line pb-6 sm:flex-row sm:items-start sm:justify-between"
        >
          <div class="min-w-0">
            <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h1 class="text-2xl font-semibold tracking-tight text-ink">{{ current.title }}</h1>
              <ui-badge [tone]="current.is_published ? 'success' : 'notice'">
                {{ current.is_published ? 'Publicado' : 'Borrador' }}
              </ui-badge>
            </div>
            @if (current.description) {
              <p class="mt-1.5 max-w-prose text-sm leading-relaxed text-ink-muted">
                {{ current.description }}
              </p>
            }
          </div>
          <div class="shrink-0">
            <ui-button [variant]="formOpen() ? 'secondary' : 'primary'" (pressed)="toggleForm()">
              {{ formOpen() ? 'Cancelar' : 'Agregar lección' }}
            </ui-button>
          </div>
        </header>

        @if (!current.is_published) {
          <div class="mt-6">
            <ui-alert tone="notice">
              El módulo está en borrador: nadie fuera del equipo de lecciones ve nada de lo que hay
              aquí, aunque una lección esté publicada.
            </ui-alert>
          </div>
        }

        @if (formOpen()) {
          <form
            class="mt-6 rounded-[var(--radius-panel)] border border-line bg-surface p-5 sm:p-6"
            (ngSubmit)="saveLesson()"
          >
            <h2 class="text-base font-semibold text-ink">
              {{ editingLesson() ? 'Editar lección' : 'Nueva lección' }}
            </h2>
            <div class="mt-5 grid gap-4">
              <ui-field label="Título" for="leccion-titulo" [error]="formError()">
                <input
                  uiInput
                  id="leccion-titulo"
                  name="leccionTitulo"
                  required
                  minlength="3"
                  maxlength="150"
                  autocomplete="off"
                  [(ngModel)]="lessonTitle"
                  [invalid]="!!formError()"
                />
              </ui-field>
              <ui-field label="Descripción" for="leccion-descripcion" [optional]="true">
                <textarea
                  uiInput
                  id="leccion-descripcion"
                  name="leccionDescripcion"
                  rows="2"
                  maxlength="2000"
                  [(ngModel)]="lessonDescription"
                ></textarea>
              </ui-field>
            </div>
            <div class="mt-5 flex gap-2">
              <ui-button type="submit" [loading]="saving()">
                {{ editingLesson() ? 'Guardar' : 'Crear' }}
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

        @if (lessons().length === 0) {
          <ui-empty-state
            title="Este módulo no tiene lecciones"
            description="Agrega la primera. Cada lección reúne los enlaces al material: cuadernos, repositorios, PDF, videos o artículos."
          />
        } @else {
          <ul class="mt-8 divide-y divide-line border-y border-line">
            @for (lesson of lessons(); track lesson.id; let i = $index) {
              <li class="py-4">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div class="min-w-0">
                    <div class="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                      <span class="text-sm font-medium text-ink">{{ lesson.title }}</span>
                      <ui-badge [tone]="lesson.is_published ? 'success' : 'notice'">
                        {{ lesson.is_published ? 'Publicada' : 'Borrador' }}
                      </ui-badge>
                    </div>
                    @if (lesson.description) {
                      <p class="mt-1 line-clamp-2 max-w-prose text-sm text-ink-muted">
                        {{ lesson.description }}
                      </p>
                    }
                  </div>

                  <div class="flex shrink-0 flex-wrap items-center gap-1">
                    <button
                      type="button"
                      [class]="iconButton"
                      [disabled]="!canMoveUp(i) || busy()"
                      (click)="moveLesson(i, -1)"
                    >
                      <span class="sr-only">Subir {{ lesson.title }}</span>
                      <span aria-hidden="true">↑</span>
                    </button>
                    <button
                      type="button"
                      [class]="iconButton"
                      [disabled]="!canMoveDown(i) || busy()"
                      (click)="moveLesson(i, 1)"
                    >
                      <span class="sr-only">Bajar {{ lesson.title }}</span>
                      <span aria-hidden="true">↓</span>
                    </button>
                    <ui-button
                      size="sm"
                      variant="secondary"
                      [disabled]="busy()"
                      (pressed)="togglePublished(lesson)"
                    >
                      {{ lesson.is_published ? 'Retirar' : 'Publicar' }}
                    </ui-button>
                    <ui-button
                      size="sm"
                      variant="ghost"
                      [disabled]="busy()"
                      (pressed)="editLesson(lesson)"
                    >
                      Editar
                    </ui-button>
                    <ui-button
                      size="sm"
                      variant="ghost"
                      [disabled]="busy()"
                      (pressed)="removeLesson(lesson)"
                    >
                      Eliminar
                    </ui-button>
                  </div>
                </div>

                <button
                  type="button"
                  class="mt-2 inline-flex min-h-11 items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
                  [attr.aria-expanded]="expanded() === lesson.id"
                  (click)="toggleResources(lesson)"
                >
                  <span aria-hidden="true">{{ expanded() === lesson.id ? '▾' : '▸' }}</span>
                  {{ resourceLabel(lesson.resource_count) }}
                </button>

                @if (expanded() === lesson.id) {
                  <div class="mt-2 rounded-[var(--radius-control)] bg-sunken px-4 py-4">
                    @if (resourcesLoading()) {
                      <p class="text-sm text-ink-muted">Cargando el material…</p>
                    } @else {
                      @if (resources().length === 0) {
                        <p class="text-sm text-ink-muted">Esta lección todavía no enlaza nada.</p>
                      } @else {
                        <ul class="divide-y divide-line-strong/40">
                          @for (resource of resources(); track resource.id; let r = $index) {
                            <li
                              class="flex flex-col gap-2 py-2 sm:flex-row sm:items-center sm:justify-between"
                            >
                              <span class="flex min-w-0 flex-col gap-0.5">
                                <span class="flex items-center gap-2">
                                  <ui-badge>{{ typeLabel(resource.type) }}</ui-badge>
                                  <span class="truncate text-sm text-ink">
                                    {{ resource.title }}
                                  </span>
                                </span>
                                <a
                                  [href]="resource.url"
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  class="truncate text-xs text-ink-faint hover:text-accent hover:underline"
                                >
                                  {{ resource.url }}
                                </a>
                              </span>
                              <span class="flex shrink-0 items-center gap-1">
                                <button
                                  type="button"
                                  [class]="iconButton"
                                  [disabled]="!canMoveResourceUp(r) || busy()"
                                  (click)="moveResource(lesson, r, -1)"
                                >
                                  <span class="sr-only">Subir {{ resource.title }}</span>
                                  <span aria-hidden="true">↑</span>
                                </button>
                                <button
                                  type="button"
                                  [class]="iconButton"
                                  [disabled]="!canMoveResourceDown(r) || busy()"
                                  (click)="moveResource(lesson, r, 1)"
                                >
                                  <span class="sr-only">Bajar {{ resource.title }}</span>
                                  <span aria-hidden="true">↓</span>
                                </button>
                                <ui-button
                                  size="sm"
                                  variant="ghost"
                                  [disabled]="busy()"
                                  (pressed)="removeResource(lesson, resource)"
                                >
                                  Quitar
                                </ui-button>
                              </span>
                            </li>
                          }
                        </ul>
                      }

                      <form
                        class="mt-4 grid gap-3 sm:grid-cols-[10rem_1fr]"
                        (ngSubmit)="addResource(lesson)"
                      >
                        <ui-field label="Tipo" for="recurso-tipo">
                          <select
                            uiInput
                            id="recurso-tipo"
                            name="recursoTipo"
                            [(ngModel)]="resourceType"
                          >
                            @for (type of resourceTypes; track type) {
                              <option [value]="type">{{ typeLabel(type) }}</option>
                            }
                          </select>
                        </ui-field>
                        <ui-field label="Título" for="recurso-titulo">
                          <input
                            uiInput
                            id="recurso-titulo"
                            name="recursoTitulo"
                            required
                            maxlength="200"
                            autocomplete="off"
                            [(ngModel)]="resourceTitle"
                          />
                        </ui-field>
                        <div class="sm:col-span-2">
                          <ui-field
                            label="Enlace"
                            for="recurso-url"
                            [error]="resourceError()"
                            hint="La dirección del material en GitHub, Drive, YouTube o donde esté. La plataforma no aloja archivos."
                          >
                            <input
                              uiInput
                              id="recurso-url"
                              name="recursoUrl"
                              type="url"
                              required
                              placeholder="https://github.com/…"
                              [(ngModel)]="resourceUrl"
                              [invalid]="!!resourceError()"
                            />
                          </ui-field>
                        </div>
                        <div class="sm:col-span-2">
                          <ui-button type="submit" size="sm" [loading]="busy()">
                            Enlazar recurso
                          </ui-button>
                        </div>
                      </form>
                    }
                  </div>
                }
              </li>
            }
          </ul>
        }
      }
    </div>
  `,
})
export class ModuleEditorPage {
  private readonly api = inject(LessonsApi);

  /** Enlazado desde la ruta con `withComponentInputBinding`. */
  readonly moduleId = input.required<string>();

  protected readonly module = signal<LessonModule | null>(null);
  protected readonly lessons = signal<Lesson[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly busy = signal(false);

  protected readonly formOpen = signal(false);
  protected readonly editingLesson = signal<Lesson | null>(null);
  protected readonly saving = signal(false);
  protected readonly formError = signal('');

  protected readonly expanded = signal<string | null>(null);
  protected readonly resources = signal<LessonResource[]>([]);
  protected readonly resourcesLoading = signal(false);
  protected readonly resourceError = signal('');

  protected readonly resourceTypes = RESOURCE_TYPES;

  protected lessonTitle = '';
  protected lessonDescription = '';
  protected resourceType: ResourceType = 'NOTEBOOK';
  protected resourceTitle = '';
  protected resourceUrl = '';

  protected readonly iconButton =
    'grid size-11 place-items-center rounded-[var(--radius-control)] text-ink-muted ' +
    'transition-colors hover:bg-surface hover:text-ink disabled:text-ink-faint ' +
    'disabled:hover:bg-transparent disabled:cursor-not-allowed';

  constructor() {
    effect(() => this.load(this.moduleId()));
  }

  protected typeLabel(type: ResourceType): string {
    return RESOURCE_TYPE_LABEL[type];
  }

  protected resourceLabel(count: number): string {
    if (count === 0) return 'Sin recursos';
    return count === 1 ? '1 recurso' : `${count} recursos`;
  }

  protected canMoveUp(index: number): boolean {
    return canMove(this.lessons().length, index, -1);
  }

  protected canMoveDown(index: number): boolean {
    return canMove(this.lessons().length, index, 1);
  }

  protected canMoveResourceUp(index: number): boolean {
    return canMove(this.resources().length, index, -1);
  }

  protected canMoveResourceDown(index: number): boolean {
    return canMove(this.resources().length, index, 1);
  }

  // --- Lecciones ---

  protected toggleForm(): void {
    const next = !this.formOpen();
    this.formOpen.set(next);
    if (!next) this.resetForm();
  }

  protected editLesson(lesson: Lesson): void {
    this.editingLesson.set(lesson);
    this.lessonTitle = lesson.title;
    this.lessonDescription = lesson.description ?? '';
    this.formError.set('');
    this.formOpen.set(true);
  }

  protected saveLesson(): void {
    const body = {
      title: this.lessonTitle.trim(),
      description: this.lessonDescription.trim() || null,
    };
    const target = this.editingLesson();
    const request = target
      ? this.api.updateLesson(target.id, body)
      : this.api.createLesson(this.moduleId(), body);

    this.saving.set(true);
    this.formError.set('');
    request.subscribe({
      next: () => {
        this.saving.set(false);
        this.formOpen.set(false);
        this.resetForm();
        this.load(this.moduleId());
      },
      error: (err: ApiError) => {
        this.formError.set(fieldMessage(err));
        this.saving.set(false);
      },
    });
  }

  protected togglePublished(lesson: Lesson): void {
    this.run(this.api.publishLesson(lesson.id, !lesson.is_published));
  }

  protected moveLesson(index: number, delta: number): void {
    const reordered = moveBy(this.lessons(), index, delta);
    this.lessons.set(reordered);
    this.run(
      this.api.reorderLessons(
        this.moduleId(),
        reordered.map((lesson) => lesson.id),
      ),
    );
  }

  protected removeLesson(lesson: Lesson): void {
    // Sin diálogo: lo que se pierde son enlaces, y RN-36 pide la advertencia
    // con conteo para el módulo, que sí arrastra lecciones enteras.
    this.run(this.api.deleteLesson(lesson.id), () => {
      if (this.expanded() === lesson.id) this.expanded.set(null);
    });
  }

  // --- Recursos ---

  protected toggleResources(lesson: Lesson): void {
    if (this.expanded() === lesson.id) {
      this.expanded.set(null);
      return;
    }
    this.expanded.set(lesson.id);
    this.resourceError.set('');
    this.loadResources(lesson.id);
  }

  protected addResource(lesson: Lesson): void {
    this.busy.set(true);
    this.resourceError.set('');
    this.api
      .addResource(lesson.id, {
        type: this.resourceType,
        title: this.resourceTitle.trim(),
        url: this.resourceUrl.trim(),
      })
      .subscribe({
        next: () => {
          this.busy.set(false);
          this.resourceTitle = '';
          this.resourceUrl = '';
          this.loadResources(lesson.id);
          this.load(this.moduleId());
        },
        error: (err: ApiError) => {
          this.resourceError.set(fieldMessage(err));
          this.busy.set(false);
        },
      });
  }

  protected moveResource(lesson: Lesson, index: number, delta: number): void {
    const reordered = moveBy(this.resources(), index, delta);
    this.resources.set(reordered);
    this.run(
      this.api.reorderResources(
        lesson.id,
        reordered.map((resource) => resource.id),
      ),
      () => this.loadResources(lesson.id),
    );
  }

  protected removeResource(lesson: Lesson, resource: LessonResource): void {
    this.run(this.api.deleteResource(resource.id), () => {
      this.loadResources(lesson.id);
      this.load(this.moduleId());
    });
  }

  // --- Carga ---

  private run(request: Observable<unknown>, done?: () => void): void {
    this.busy.set(true);
    this.error.set('');
    request.subscribe({
      next: () => {
        this.busy.set(false);
        done?.();
        this.load(this.moduleId());
      },
      error: (err: ApiError) => {
        this.error.set(err.message);
        this.busy.set(false);
        done?.();
        // También al fallar: la pantalla pudo pintar un orden que el servidor
        // no aceptó, y dejarlo ahí sería mentir.
        this.load(this.moduleId());
      },
    });
  }

  private resetForm(): void {
    this.editingLesson.set(null);
    this.lessonTitle = '';
    this.lessonDescription = '';
    this.formError.set('');
  }

  private load(moduleId: string): void {
    this.api.catalog().subscribe({
      next: (modules) => {
        const found = modules.find((module) => module.id === moduleId) ?? null;
        this.module.set(found);
        this.lessons.set(found?.lessons ?? []);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err.message);
        this.loading.set(false);
      },
    });
  }

  private loadResources(lessonId: string): void {
    this.resourcesLoading.set(true);
    this.api.lesson(lessonId).subscribe({
      next: (detail) => {
        this.resources.set(detail.resources);
        this.resourcesLoading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err.message);
        this.resourcesLoading.set(false);
      },
    });
  }
}
