import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';

export type AlertTone = 'error' | 'success' | 'notice' | 'info';

const TONES: Record<AlertTone, string> = {
  error: 'bg-danger-soft border-danger-line text-danger',
  success: 'bg-success-soft border-success-line text-success',
  notice: 'bg-notice-soft border-notice-line text-notice',
  info: 'bg-accent-soft border-accent-line text-accent',
};

/**
 * Aviso en línea. El tono se acompaña siempre del texto que dice qué pasó: el
 * color nunca es la única señal (RNF-09).
 */
@Component({
  selector: 'ui-alert',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div [class]="classes()" [attr.role]="tone() === 'error' ? 'alert' : 'status'">
      <ng-content />
    </div>
  `,
})
export class AlertComponent {
  readonly tone = input<AlertTone>('info');

  protected readonly classes = computed(() =>
    [
      'rounded-[var(--radius-control)] border px-3.5 py-3 text-sm leading-relaxed',
      TONES[this.tone()],
    ].join(' '),
  );
}
