import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Indicador de espera. Hereda el color del texto para funcionar dentro de
 * cualquier botón o superficie sin necesitar variantes. */
@Component({
  selector: 'ui-spinner',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <svg
      [attr.width]="size()"
      [attr.height]="size()"
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
      class="animate-spin shrink-0"
    >
      <circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.5" opacity="0.25" />
      <path
        d="M21 12a9 9 0 0 0-9-9"
        stroke="currentColor"
        stroke-width="2.5"
        stroke-linecap="round"
      />
    </svg>
  `,
})
export class SpinnerComponent {
  readonly size = input(20);
}
