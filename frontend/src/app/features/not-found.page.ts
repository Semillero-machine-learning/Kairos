import { ChangeDetectionStrategy, Component } from '@angular/core';
import { RouterLink } from '@angular/router';

import { BrandComponent } from '../shared/ui/brand.component';

@Component({
  selector: 'app-not-found-page',
  imports: [RouterLink, BrandComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="flex min-h-dvh flex-col items-center justify-center gap-6 px-5 text-center">
      <ui-brand variant="stacked" [width]="96" />
      <div>
        <h1 class="text-xl font-semibold text-ink">Esta página no existe</h1>
        <p class="mt-1.5 text-sm leading-relaxed text-ink-muted">
          Puede que el enlace esté incompleto o que la pantalla se haya movido.
        </p>
      </div>
      <a
        routerLink="/inicio"
        class="inline-flex min-h-11 items-center justify-center rounded-[var(--radius-control)] bg-accent px-4 text-sm font-medium text-white transition-colors hover:bg-accent-hover"
      >
        Ir al inicio
      </a>
    </div>
  `,
})
export class NotFoundPage {}
