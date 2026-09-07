import { Directive, ElementRef, computed, inject, input } from '@angular/core';

/**
 * Estilo compartido de todo control de entrada: `input`, `select` y
 * `textarea`. Es una directiva y no un componente envolvente para que cada
 * formulario conserve su propio elemento nativo, con su tipo, su
 * autocompletado y su comportamiento de teclado intactos.
 *
 * En un `select` añade además la clase que apaga la flecha del sistema
 * operativo y dibuja la nuestra: un control con nuestro borde y nuestra
 * tipografía, rematado con el triángulo de Chrome, delata que la pantalla se
 * ensambló en vez de construirse.
 */
@Directive({
  selector: '[uiInput]',
  host: {
    '[class]': 'classes()',
    '[attr.aria-invalid]': 'invalid() ? "true" : null',
  },
})
export class InputDirective {
  readonly invalid = input(false);

  /**
   * Versión compacta, para un control que vive dentro de una fila o de una
   * barra de filtros en vez de dentro de un formulario. Solo cambia el alto y
   * el relleno vertical: el ancho lo decide el sitio de uso, porque un filtro
   * quiere ancho fijo y un control en línea quiere ajustarse a su contenido.
   *
   * Es un modo de la primitiva y no un `!important` en el sitio de uso: una
   * pantalla que se salta el primitivo con especificidad le abre la puerta a
   * la siguiente para que haga lo mismo.
   */
  readonly compact = input(false);

  private readonly isSelect =
    inject(ElementRef<HTMLElement>).nativeElement.tagName === 'SELECT';

  protected readonly classes = computed(() =>
    [
      'rounded-[var(--radius-control)] border bg-surface px-3',
      'text-sm text-ink placeholder:text-ink-placeholder',
      'transition-colors duration-150',
      'disabled:bg-sunken disabled:text-ink-muted disabled:cursor-not-allowed',
      // 44 px es el mínimo táctil de RNF-01. La versión compacta baja a 36 con
      // puntero fino y vuelve a 44 en cuanto hay algún puntero grueso.
      this.compact() ? 'min-h-9 any-pointer-coarse:min-h-11 py-1' : 'w-full min-h-11 py-2',
      this.invalid() ? 'border-danger' : 'border-line-strong hover:border-ink-faint',
      this.isSelect ? 'ui-select' : '',
    ].join(' '),
  );
}
