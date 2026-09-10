import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  contentChild,
  signal,
} from '@angular/core';

import { InputDirective } from './input.directive';

/**
 * El ojo que descubre la contraseña mientras se escribe.
 *
 * Existe porque un campo enmascarado sin forma de verificarlo obliga a
 * escribir a ciegas: quien se equivoca no lo sabe hasta que el servidor
 * responde «esa contraseña no es correcta», y en un campo de contraseña nueva
 * ni siquiera entonces.
 *
 * No sustituye al control: proyecta el `input` nativo del formulario y solo le
 * añade el botón encima, así que el tipo, el autocompletado y el
 * `formControlName` siguen siendo del sitio de uso (regla del elemento nativo
 * de `DESIGN.md`). Alternar solo cambia el atributo `type` del elemento
 * proyectado; el valor y el control de formularios no se enteran.
 *
 * El campo tiene que declarar `[trailingSlot]="true"` para reservar el sitio
 * del botón. Podría deducirse aquí, pero la clase la pinta `uiInput` con un
 * enlace a `[class]` que se recalcula entero cada vez que cambia `invalid`:
 * cualquier clase añadida desde fuera se perdería en el primer error.
 */
@Component({
  selector: 'ui-password-input',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { class: 'relative block' },
  template: `
    <ng-content />

    <button
      type="button"
      class="absolute inset-y-0 right-0 grid w-11 place-items-center rounded-[var(--radius-control)] text-ink-muted transition-colors duration-150 hover:text-ink"
      [attr.aria-label]="visible() ? 'Ocultar la contraseña' : 'Mostrar la contraseña'"
      (mousedown)="keepFocus($event)"
      (click)="toggle()"
    >
      @if (visible()) {
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.75"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M10.7 6.2A10.6 10.6 0 0 1 12 6c4.2 0 7.8 2.6 9.5 6a15.6 15.6 0 0 1-3 4.1" />
          <path d="M6.9 7.6A15.4 15.4 0 0 0 2.5 12c1.7 3.4 5.3 6 9.5 6 1.5 0 2.9-.3 4.1-.9" />
          <path d="M9.9 9.9a3 3 0 0 0 4.2 4.2" />
          <path d="m3 3 18 18" />
        </svg>
      } @else {
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.75"
          stroke-linecap="round"
          stroke-linejoin="round"
          aria-hidden="true"
        >
          <path d="M2.5 12C4.2 8.6 7.8 6 12 6s7.8 2.6 9.5 6c-1.7 3.4-5.3 6-9.5 6s-7.8-2.6-9.5-6Z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      }
    </button>
  `,
})
export class PasswordInputComponent {
  private readonly field = contentChild.required(InputDirective, { read: ElementRef });

  protected readonly visible = signal(false);

  /**
   * Un clic en el botón no debe robarle el foco al campo: quien lo pulsa a
   * mitad de escribir quiere seguir escribiendo, no volver a hacer clic. Con
   * el teclado el foco sí se queda en el botón, que es donde el usuario lo
   * puso y donde espera encontrarlo.
   */
  protected keepFocus(event: MouseEvent): void {
    event.preventDefault();
  }

  protected toggle(): void {
    const field = this.field().nativeElement as HTMLInputElement;
    const visible = !this.visible();

    this.visible.set(visible);
    field.type = visible ? 'text' : 'password';

    // Cambiar `type` reposiciona el cursor al principio en algunos
    // navegadores. Si el campo tenía el foco, se devuelve al final: no hay
    // nada más desconcertante que revelar lo escrito y que la siguiente letra
    // aparezca delante.
    if (document.activeElement === field) {
      const end = field.value.length;
      field.setSelectionRange(end, end);
    }
  }
}
