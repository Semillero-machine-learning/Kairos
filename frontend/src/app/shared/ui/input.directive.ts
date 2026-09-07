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

  private readonly isSelect =
    inject(ElementRef<HTMLElement>).nativeElement.tagName === 'SELECT';

  protected readonly classes = computed(() =>
    [
      'w-full min-h-11 rounded-[var(--radius-control)] border bg-surface px-3 py-2',
      'text-sm text-ink placeholder:text-ink-placeholder',
      'transition-colors duration-150',
      'disabled:bg-sunken disabled:text-ink-muted disabled:cursor-not-allowed',
      this.invalid() ? 'border-danger' : 'border-line-strong hover:border-ink-faint',
      this.isSelect ? 'ui-select' : '',
    ].join(' '),
  );
}
