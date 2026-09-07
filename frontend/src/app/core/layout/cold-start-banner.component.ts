import { ChangeDetectionStrategy, Component, inject } from '@angular/core';

import { SpinnerComponent } from '../../shared/ui/spinner.component';
import { ColdStartService } from '../http/cold-start.service';

/**
 * Aviso de arranque en frío (RNF-02).
 *
 * El backend del plan gratuito se suspende y la primera petición puede tardar
 * cerca de un minuto. En vez de una pantalla en blanco o un error genérico, se
 * dice lo que está pasando. Ocupa su propia franja en el flujo, empujando el
 * contenido hacia abajo en vez de taparlo.
 */
@Component({
  selector: 'app-cold-start-banner',
  imports: [SpinnerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @if (coldStart.waking()) {
      <div
        role="status"
        aria-live="polite"
        class="motion-enter flex items-center justify-center gap-2.5 border-b border-notice-line bg-notice-soft px-4 py-2.5 text-sm text-notice"
      >
        <ui-spinner [size]="16" />
        <span>Despertando el servidor… la primera carga del día tarda un poco.</span>
      </div>
    }
  `,
})
export class ColdStartBannerComponent {
  protected readonly coldStart = inject(ColdStartService);
}
