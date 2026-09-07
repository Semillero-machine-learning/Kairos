import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * Nombre de un rol de proyecto con su color.
 *
 * El color lo elige quien crea el rol, así que no puede venir de los tokens de
 * diseño. Se usa como punto al lado del nombre y no como fondo del texto: un
 * color arbitrario detrás de una etiqueta no garantiza contraste, y el nombre
 * siempre se lee sobre el fondo de la interfaz (RNF-09).
 */
@Component({
  selector: 'app-role-chip',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <span
      class="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-2.5 py-0.5 text-xs font-medium whitespace-nowrap text-ink"
    >
      <span
        class="size-2 shrink-0 rounded-full"
        [style.background-color]="color()"
        aria-hidden="true"
      ></span>
      {{ name() }}
      @if (suffix()) {
        <span class="font-normal text-ink-muted">{{ suffix() }}</span>
      }
    </span>
  `,
})
export class RoleChipComponent {
  readonly name = input.required<string>();
  readonly color = input.required<string>();
  readonly suffix = input<string>('');
}
