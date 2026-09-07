import { Directive, computed, input } from '@angular/core';

/**
 * Estilo compartido de todo control de entrada: `input`, `select` y
 * `textarea`. Es una directiva y no un componente envolvente para que cada
 * formulario conserve su propio elemento nativo, con su tipo, su
 * autocompletado y su comportamiento de teclado intactos.
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

  protected readonly classes = computed(() =>
    [
      'w-full min-h-11 rounded-[var(--radius-control)] border bg-surface px-3 py-2',
      'text-sm text-ink placeholder:text-ink-faint',
      'transition-colors duration-150',
      'disabled:bg-sunken disabled:text-ink-muted disabled:cursor-not-allowed',
      this.invalid() ? 'border-danger' : 'border-line-strong hover:border-ink-faint',
    ].join(' '),
  );
}
