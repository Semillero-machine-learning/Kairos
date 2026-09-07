import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/**
 * Etiqueta, control y mensaje de un campo.
 *
 * El error sustituye a la pista cuando existe, para no apilar dos líneas de
 * texto bajo el mismo campo, y va enlazado por `aria-describedby` para que un
 * lector de pantalla lo anuncie al enfocar el control.
 */
@Component({
  selector: 'ui-field',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex flex-col gap-1.5">
      <label [attr.for]="for()" class="text-sm font-medium text-ink">
        {{ label() }}
        @if (optional()) {
          <span class="ml-1 font-normal text-ink-muted">(opcional)</span>
        }
      </label>

      <ng-content />

      @if (error()) {
        <p [id]="for() + '-msg'" class="text-sm text-danger">{{ error() }}</p>
      } @else if (hint()) {
        <p [id]="for() + '-msg'" class="text-sm text-ink-muted">{{ hint() }}</p>
      }
    </div>
  `,
})
export class FieldComponent {
  readonly label = input.required<string>();
  readonly for = input.required<string>();
  readonly hint = input<string>('');
  readonly error = input<string>('');
  readonly optional = input(false);
}
