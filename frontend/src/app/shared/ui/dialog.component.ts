import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  effect,
  input,
  output,
  viewChild,
} from '@angular/core';

/**
 * Capa emergente.
 *
 * Envuelve el `<dialog>` nativo en vez de recrearlo: el navegador ya trae la
 * trampa de foco, el cierre con Escape, el fondo inerte y el anuncio como
 * diálogo modal a los lectores de pantalla (RNF-09). Reimplementar todo eso a
 * mano es la vía rápida a una pantalla que no se puede cerrar con el teclado.
 *
 * Es la única superficie del sistema que lleva sombra: `--shadow-float` está
 * reservada para lo que de verdad flota sobre el contenido.
 */
@Component({
  selector: 'ui-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <dialog
      #dialog
      [attr.aria-label]="label()"
      class="m-auto w-[min(38rem,calc(100vw-1.5rem))] rounded-[var(--radius-panel)] border border-line bg-surface p-0 text-ink shadow-float backdrop:bg-ink/25"
      (close)="closed.emit()"
      (click)="onClick($event)"
    >
      <div class="max-h-[85vh] overflow-y-auto overscroll-contain p-5 sm:p-6">
        <ng-content />
      </div>
    </dialog>
  `,
})
export class DialogComponent {
  readonly open = input(false);
  /** Nombra el diálogo para quien no ve su encabezado. */
  readonly label = input.required<string>();

  readonly closed = output<void>();

  private readonly dialog = viewChild.required<ElementRef<HTMLDialogElement>>('dialog');

  constructor() {
    effect(() => {
      const element = this.dialog().nativeElement;
      if (this.open() && !element.open) element.showModal();
      if (!this.open() && element.open) element.close();
    });
  }

  /** Un clic sobre el fondo cierra. El `<dialog>` recibe el evento solo cuando
   * el punto queda fuera de su contenido, así que el propio destino distingue
   * el fondo del panel. */
  protected onClick(event: MouseEvent): void {
    if (event.target === this.dialog().nativeElement) this.closed.emit();
  }
}
