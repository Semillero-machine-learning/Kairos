import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type BadgeTone = 'neutral' | 'accent' | 'success' | 'danger' | 'notice';

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-sunken text-ink-muted border-line',
  accent: 'bg-accent-soft text-accent border-accent-line',
  success: 'bg-success-soft text-success border-success-line',
  danger: 'bg-danger-soft text-danger border-danger-line',
  notice: 'bg-notice-soft text-notice border-notice-line',
};

/** Etiqueta de estado o de rol. Siempre lleva texto: el color acompaña, no
 * sustituye (RNF-09). */
@Component({
  selector: 'ui-badge',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span [class]="classes()"><ng-content /></span>`,
})
export class BadgeComponent {
  readonly tone = input<BadgeTone>('neutral');

  protected readonly classes = computed(() =>
    [
      'inline-flex items-center rounded-full border px-2.5 py-0.5',
      'text-xs font-medium whitespace-nowrap',
      TONES[this.tone()],
    ].join(' '),
  );
}
