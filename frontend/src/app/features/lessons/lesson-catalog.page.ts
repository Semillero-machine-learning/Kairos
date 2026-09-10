import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';

import { ApiError } from '../../core/api/api-error';
import { LessonsApi } from '../../core/api/lessons.api';
import { LessonModule } from '../../core/api/models';
import { SessionService } from '../../core/auth/session.service';
import { AlertComponent } from '../../shared/ui/alert.component';
import { BadgeComponent } from '../../shared/ui/badge.component';
import { ButtonComponent } from '../../shared/ui/button.component';
import { EmptyStateComponent } from '../../shared/ui/empty-state.component';
import { InputDirective } from '../../shared/ui/input.directive';
import { PageHeaderComponent } from '../../shared/ui/page-header.component';
import { SpinnerComponent } from '../../shared/ui/spinner.component';

/** Lo que se espera a que el usuario termine de escribir antes de consultar. */
const SEARCH_DEBOUNCE_MS = 300;

/**
 * Catálogo de lecciones (RF-46, RF-49, RF-51).
 *
 * El árbol llega entero en una petición y se pinta tal cual: qué módulos y qué
 * lecciones viajan lo decidió el backend según quién pregunta (RN-32, RN-33).
 * Esta pantalla no filtra nada por rol, solo distingue lo que ya llegó marcado
 * como borrador —que únicamente un editor recibe— para que se note de un
 * vistazo qué está publicado y qué no.
 */
@Component({
  selector: 'app-lesson-catalog-page',
  imports: [
    FormsModule,
    RouterLink,
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
      <ui-page-header
        title="Lecciones"
        description="El material del semillero, organizado en módulos. Todo vive en GitHub y otras fuentes; aquí están los enlaces."
      >
        @if (session.canEditLessons()) {
          <ui-button variant="secondary" routerLink="/lecciones/editor">
            Editar catálogo
          </ui-button>
        }
      </ui-page-header>

      <div class="mt-6">
        <label class="sr-only" for="buscar">Buscar en el catálogo</label>
        <input
          uiInput
          id="buscar"
          name="buscar"
          type="search"
          autocomplete="off"
          placeholder="Buscar por título o descripción"
          [ngModel]="term()"
          (ngModelChange)="onSearch($event)"
        />
      </div>

      @if (loading()) {
        <div class="flex items-center gap-2 py-12 text-sm text-ink-muted">
          <ui-spinner />
          Cargando el catálogo…
        </div>
      } @else if (error()) {
        <div class="py-8">
          <ui-alert tone="error">{{ error() }}</ui-alert>
        </div>
      } @else if (modules().length === 0) {
        <ui-empty-state
          [title]="searching() ? 'Sin coincidencias' : 'Todavía no hay material'"
          [description]="
            searching()
              ? 'Ningún módulo ni lección coincide con lo que buscaste. Prueba con otra palabra.'
              : catalogHint()
          "
        >
          @if (session.canEditLessons() && !searching()) {
            <ui-button routerLink="/lecciones/editor">Crear el primer módulo</ui-button>
          }
        </ui-empty-state>
      } @else {
        <div class="mt-8 flex flex-col gap-10">
          @for (module of modules(); track module.id) {
            <section>
              <div class="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                <h2 class="text-lg font-semibold tracking-tight text-ink">{{ module.title }}</h2>
                @if (!module.is_published) {
                  <ui-badge tone="notice">Borrador</ui-badge>
                }
              </div>
              @if (module.description) {
                <p class="mt-1.5 max-w-prose text-sm leading-relaxed text-ink-muted">
                  {{ module.description }}
                </p>
              }

              @if (module.lessons.length === 0) {
                <p class="mt-4 text-sm text-ink-muted">Este módulo todavía no tiene lecciones.</p>
              } @else {
                <ul class="mt-4 divide-y divide-line border-y border-line">
                  @for (lesson of module.lessons; track lesson.id) {
                    <li>
                      <a
                        [routerLink]="['/lecciones', lesson.id]"
                        class="flex min-h-14 flex-col justify-center gap-1 py-3 transition-colors hover:bg-sunken"
                      >
                        <span class="flex flex-wrap items-baseline gap-x-2.5 gap-y-1">
                          <span class="text-sm font-medium text-ink">{{ lesson.title }}</span>
                          @if (!lesson.is_published) {
                            <ui-badge tone="notice">Borrador</ui-badge>
                          }
                        </span>
                        @if (lesson.description) {
                          <span class="line-clamp-2 text-sm text-ink-muted">
                            {{ lesson.description }}
                          </span>
                        }
                        <span class="text-xs text-ink-muted">{{
                          resourceLabel(lesson.resource_count)
                        }}</span>
                      </a>
                    </li>
                  }
                </ul>
              }
            </section>
          }
        </div>
      }
    </div>
  `,
})
export class LessonCatalogPage implements OnDestroy {
  private readonly api = inject(LessonsApi);
  protected readonly session = inject(SessionService);

  protected readonly modules = signal<LessonModule[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal('');
  protected readonly term = signal('');

  /** Lo que se buscó de verdad, no lo que se está escribiendo: el mensaje del
   * estado vacío depende de si hubo búsqueda, y adelantarlo haría parpadear
   * «sin coincidencias» mientras se teclea la primera letra. */
  private readonly applied = signal('');
  protected readonly searching = computed(() => this.applied().length > 0);

  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor() {
    this.load('');
  }

  ngOnDestroy(): void {
    if (this.timer !== null) clearTimeout(this.timer);
  }

  protected catalogHint(): string {
    return this.session.canEditLessons()
      ? 'Crea un módulo, agrégale lecciones y publícalo cuando esté listo.'
      : 'Cuando el equipo de lecciones publique material, aparecerá aquí.';
  }

  protected resourceLabel(count: number): string {
    if (count === 0) return 'Sin recursos';
    return count === 1 ? '1 recurso' : `${count} recursos`;
  }

  protected onSearch(value: string): void {
    this.term.set(value);
    if (this.timer !== null) clearTimeout(this.timer);
    this.timer = setTimeout(() => this.load(value.trim()), SEARCH_DEBOUNCE_MS);
  }

  private load(query: string): void {
    this.loading.set(true);
    this.error.set('');
    this.api.catalog(query || undefined).subscribe({
      next: (modules) => {
        this.modules.set(modules);
        this.applied.set(query);
        this.loading.set(false);
      },
      error: (err: ApiError) => {
        this.error.set(err.message);
        this.loading.set(false);
      },
    });
  }
}
