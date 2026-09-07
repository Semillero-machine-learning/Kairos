import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * Estado vacío.
 *
 * Muestra la forma de lo que iría ahí en vez de un texto centrado pidiendo
 * disculpas: un encabezado que nombra qué falta, una frase que dice por qué
 * está vacío, y la acción que lo llena cuando existe.
 */
@Component({
  selector: 'ui-empty-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex flex-col items-start gap-2 px-5 py-12 sm:items-center sm:text-center">
      <p class="text-base font-medium text-ink">{{ title() }}</p>
      <p class="max-w-md text-sm leading-relaxed text-ink-muted">{{ description() }}</p>
      <div class="mt-3 empty:hidden">
        <ng-content />
      </div>
    </div>
  `,
})
export class EmptyStateComponent {
  readonly title = input.required<string>();
  readonly description = input<string>('');
}
