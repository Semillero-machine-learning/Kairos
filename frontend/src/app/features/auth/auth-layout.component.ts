import { ChangeDetectionStrategy, Component, input } from '@angular/core';

import { BrandComponent } from '../../shared/ui/brand.component';

/**
 * Marco común de las pantallas sin sesión.
 *
 * Columna única centrada sobre el fondo liso, sin tarjeta flotante: no hay
 * nada más en la pantalla de lo que la tarjeta tendría que separarla.
 */
@Component({
  selector: 'app-auth-layout',
  imports: [BrandComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex min-h-dvh flex-col items-center px-5 py-14 sm:py-20">
      <div class="w-full max-w-[380px]">
        <div class="mb-9 flex justify-center">
          <ui-brand variant="stacked" [width]="132" />
        </div>

        <h1 class="text-xl font-semibold text-ink">{{ title() }}</h1>
        @if (subtitle()) {
          <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">{{ subtitle() }}</p>
        }

        <div class="mt-7">
          <ng-content />
        </div>
      </div>
    </div>
  `,
})
export class AuthLayoutComponent {
  readonly title = input.required<string>();
  readonly subtitle = input<string>('');
}
