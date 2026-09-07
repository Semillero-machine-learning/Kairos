import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Encabezado de una pantalla con sesión: título, una línea de contexto y un
 * espacio a la derecha para la acción principal. */
@Component({
  selector: 'ui-page-header',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <header
      class="flex flex-col gap-4 border-b border-line pb-6 sm:flex-row sm:items-start sm:justify-between"
    >
      <div class="min-w-0">
        <h1 class="text-2xl font-semibold tracking-tight text-ink">{{ title() }}</h1>
        @if (description()) {
          <p class="mt-1.5 max-w-prose text-sm leading-relaxed text-ink-muted">
            {{ description() }}
          </p>
        }
      </div>
      <div class="shrink-0 empty:hidden">
        <ng-content />
      </div>
    </header>
  `,
})
export class PageHeaderComponent {
  readonly title = input.required<string>();
  readonly description = input<string>('');
}
