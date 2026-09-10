import { ChangeDetectionStrategy, Component, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { ApiError } from '../../core/api/api-error';
import { LessonsApi } from '../../core/api/lessons.api';
import { LessonDetail, RESOURCE_TYPE_LABEL, ResourceType } from '../../core/api/models';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';

/**
 * Una lección con sus enlaces (RF-48).
 *
 * Todo recurso abre en una pestaña nueva y va marcado como externo: la
 * plataforma no aloja nada y no debe fingir que sí (RN-34). Tampoco se
 * renderizan cuadernos ni PDF aquí dentro — está fuera de alcance en el PRD, y
 * GitHub ya los muestra mejor.
 *
 * No hay registro de avance (RF-52, RN-35): abrir un recurso no marca nada.
 */
@Component({
  selector: 'app-lesson-detail-page',
  imports: [RouterLink, AlertComponent, BadgeComponent, EmptyStateComponent, SpinnerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="mx-auto w-full max-w-3xl px-5 py-8 sm:px-8 sm:py-12">
      <a
        routerLink="/lecciones"
        class="inline-flex min-h-11 items-center gap-1.5 text-sm text-ink-muted transition-colors hover:text-ink"
      >
        <span aria-hidden="true">←</span> Volver al catálogo
      </a>

      @if (loading()) {
        <div class="flex items-center gap-2 py-12 text-sm text-ink-muted">
          <ui-spinner />
          Cargando la lección…
        </div>
      } @else if (error()) {
        <div class="py-8">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      } @else if (lesson(); as detail) {
        <header class="mt-4 border-b border-line pb-6">
          <p class="text-xs font-medium tracking-wide text-ink-muted uppercase">
            {{ detail.module_title }}
          </p>
          <div class="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
            <h1 class="text-2xl font-semibold tracking-tight text-ink">{{ detail.title }}</h1>
            @if (!detail.is_published) {
              <ui-badge tone="notice">Borrador</ui-badge>
            }
          </div>
          @if (detail.description) {
            <p class="mt-3 max-w-prose text-sm leading-relaxed text-ink-muted">
              {{ detail.description }}
            </p>
          }
        </header>

        @if (detail.resources.length === 0) {
          <ui-empty-state
            title="Sin material enlazado"
            description="Esta lección todavía no tiene recursos. Cuando los tenga, aparecerán aquí como enlaces."
          />
        } @else {
          <h2 class="mt-8 text-sm font-medium text-ink">Material</h2>
          <ul class="mt-3 divide-y divide-line border-y border-line">
            @for (resource of detail.resources; track resource.id) {
              <li>
                <a
                  [href]="resource.url"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="flex min-h-14 items-center justify-between gap-4 py-3 transition-colors hover:bg-sunken"
                >
                  <span class="flex min-w-0 flex-col gap-1">
                    <span class="flex items-center gap-2">
                      <ui-badge>{{ typeLabel(resource.type) }}</ui-badge>
                      <span class="truncate text-sm font-medium text-ink">
                        {{ resource.title }}
                      </span>
                    </span>
                    <span class="truncate text-xs text-ink-muted">{{ resource.url }}</span>
                  </span>
                  <span class="shrink-0 text-ink-muted" aria-hidden="true">↗</span>
                  <span class="sr-only">Se abre en una pestaña nueva.</span>
                </a>
              </li>
            }
          </ul>
        }
      }
    </div>
  `,
})
export class LessonDetailPage {
  private readonly api = inject(LessonsApi);

  /** Llega de la ruta con `withComponentInputBinding`. */
  readonly lessonId = input.required<string>();

  protected readonly lesson = signal<LessonDetail | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal('');

  constructor() {
    // Un efecto y no una llamada directa: los `input()` todavía no tienen valor
    // cuando corre el constructor. Mismo motivo que en `project-shell`.
    effect(() => this.load(this.lessonId()));
  }

  protected typeLabel(type: ResourceType): string {
    return RESOURCE_TYPE_LABEL[type];
  }

  private load(lessonId: string): void {
    this.loading.set(true);
    this.error.set('');
    this.api.lesson(lessonId).subscribe({
      next: (detail) => {
        this.lesson.set(detail);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(
          err.status === 404 ? 'Esta lección no existe o todavía no está publicada.' : err.message,
        );
        this.loading.set(false);
      },
    });
  }
}
