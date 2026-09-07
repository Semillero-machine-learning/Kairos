import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type BrandVariant = 'horizontal' | 'stacked';

/**
 * Marca de la aplicación.
 *
 * Los assets salen del logo original: el JPEG venía con el fondo blanco
 * horneado, así que se le quitó el fondo (la inversa exacta de componer tinta
 * sobre blanco) y se recortó el margen. No se redibujó nada.
 *
 * `stacked` usa el lockup completo tal cual viene la marca, para las pantallas
 * sin sesión. `horizontal` combina el monograma con el nombre compuesto en la
 * tipografía de la interfaz, porque el lockup original es vertical y no cabe
 * en una barra sin encogerse hasta lo ilegible.
 *
 * El degradado del logo se queda dentro del logo: ninguna superficie de la
 * interfaz lo reproduce (ver PRODUCT.md).
 */
@Component({
  selector: 'ui-brand',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (variant() === 'stacked') {
      <img
        src="/brand/kairos-lockup.png"
        alt="KAIROS"
        [width]="stackedWidth()"
        [height]="stackedHeight()"
        class="h-auto"
        [style.width.px]="stackedWidth()"
      />
    } @else {
      <span class="inline-flex items-center gap-2.5">
        <img
          src="/brand/kairos-mark.png"
          alt=""
          aria-hidden="true"
          width="93"
          height="96"
          class="h-6 w-auto"
        />
        <span [class]="wordmarkClasses()">KAIROS</span>
      </span>
    }
  `,
})
export class BrandComponent {
  readonly variant = input<BrandVariant>('horizontal');
  /** Ancho del lockup apilado, en píxeles. Su alto sale de la proporción. */
  readonly width = input(148);

  /** Proporción del asset: 400 × 327. */
  protected readonly stackedWidth = computed(() => this.width());
  protected readonly stackedHeight = computed(() => Math.round((this.width() * 327) / 400));

  protected readonly wordmarkClasses = computed(() =>
    ['text-sm font-semibold tracking-[0.22em] text-ink select-none'].join(' '),
  );
}
