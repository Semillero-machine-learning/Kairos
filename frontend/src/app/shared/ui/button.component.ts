import { ChangeDetectionStrategy, Component, computed, input, output } from '@angular/core';

import { SpinnerComponent } from './spinner.component';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'md' | 'sm';

const VARIANTS: Record<ButtonVariant, string> = {
  primary: 'bg-accent text-white hover:bg-accent-hover disabled:bg-accent/45',
  secondary:
    'bg-surface text-ink border border-line-strong hover:bg-sunken disabled:text-ink-faint',
  ghost: 'bg-transparent text-ink-muted hover:bg-sunken hover:text-ink disabled:text-ink-faint',
  danger: 'bg-danger text-white hover:bg-danger-hover disabled:bg-danger/45',
};

const SIZES: Record<ButtonSize, string> = {
  // 44 px de alto: el mínimo táctil de RNF-01.
  md: 'min-h-11 px-4 text-sm',
  sm: 'min-h-9 px-3 text-sm',
};

@Component({
  selector: 'ui-button',
  imports: [SpinnerComponent],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <button
      [type]="type()"
      [class]="classes()"
      [disabled]="disabled() || loading()"
      [attr.aria-busy]="loading() ? 'true' : null"
      (click)="pressed.emit()"
    >
      @if (loading()) {
        <ui-spinner [size]="16" />
      }
      <ng-content />
    </button>
  `,
})
export class ButtonComponent {
  readonly type = input<'button' | 'submit'>('button');
  readonly variant = input<ButtonVariant>('primary');
  readonly size = input<ButtonSize>('md');
  readonly disabled = input(false);
  readonly loading = input(false);
  readonly full = input(false);

  readonly pressed = output<void>();

  protected readonly classes = computed(() =>
    [
      'inline-flex items-center justify-center gap-2 rounded-[var(--radius-control)]',
      'font-medium transition-colors duration-150',
      'disabled:cursor-not-allowed',
      VARIANTS[this.variant()],
      SIZES[this.size()],
      this.full() ? 'w-full' : '',
    ].join(' '),
  );
}
