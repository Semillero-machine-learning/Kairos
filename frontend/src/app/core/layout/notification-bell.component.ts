import {
  ChangeDetectionStrategy,
  Component,
  ElementRef,
  computed,
  inject,
  signal,
} from '@angular/core';
import { Router } from '@angular/router';

import { AppNotification, NOTIFICATION_TONE } from '../api/models';
import { BogotaDatePipe } from '../../shared/pipes/bogota-date.pipe';
import { NotificationStore } from '../notifications/notification.store';

/**
 * La campana: contador de no leídas e historial (RF-38).
 *
 * El contador vive siempre; la lista se pide solo al abrir el panel, porque es
 * lo que se mira de vez en cuando y sondearla sería gastar el plan gratuito en
 * datos que nadie está viendo.
 *
 * Adaptación: en móvil el panel ocupa el ancho de la pantalla en vez de colgar
 * de un botón de 44 px, donde no cabría nada legible.
 *
 * Desde 768 px el panel se despliega hacia la derecha (`md:left-0`), no hacia
 * la izquierda. La única campana visible a ese ancho es la de la barra lateral,
 * que mide 240 px: anclada por su borde derecho, un panel de 352 px se salía de
 * la barra, se salía de la ventana y se cortaba contra el borde izquierdo.
 */
@Component({
  selector: 'app-notification-bell',
  imports: [BogotaDatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: {
    class: 'relative block',
    '(document:click)': 'onDocumentClick($event)',
    '(document:keydown.escape)': 'close()',
  },
  template: `
    <button
      type="button"
      class="relative grid size-11 place-items-center rounded-[var(--radius-control)] text-ink-muted transition-colors hover:bg-sunken hover:text-ink"
      [attr.aria-expanded]="open()"
      aria-controls="panel-notificaciones"
      [attr.aria-label]="buttonLabel()"
      (click)="toggle()"
    >
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M6 9a6 6 0 0 1 12 0c0 3.1.6 4.8 1.3 5.8.4.6 0 1.4-.7 1.4H5.4c-.7 0-1.1-.8-.7-1.4C5.4 13.8 6 12.1 6 9Z"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linejoin="round"
        />
        <path
          d="M10 19a2 2 0 0 0 4 0"
          stroke="currentColor"
          stroke-width="1.6"
          stroke-linecap="round"
        />
      </svg>
      @if (store.unread() > 0) {
        <span
          class="absolute top-1 right-1 grid h-4.5 min-w-4.5 place-items-center rounded-full bg-danger px-1 text-xs font-semibold text-white"
        >
          {{ badge() }}
        </span>
      }
    </button>

    @if (open()) {
      <div
        id="panel-notificaciones"
        role="dialog"
        aria-label="Notificaciones"
        class="fixed inset-x-2 top-16 z-40 max-h-[70dvh] overflow-y-auto rounded-[var(--radius-panel)] border border-line-strong bg-surface md:absolute md:inset-x-auto md:top-auto md:left-0 md:mt-1 md:w-88"
      >
        <div class="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
          <h2 class="text-sm font-medium text-ink">Notificaciones</h2>
          @if (store.unread() > 0) {
            <button
              type="button"
              class="min-h-11 text-xs font-medium text-accent hover:underline"
              (click)="store.markAllRead()"
            >
              Marcar todas como leídas
            </button>
          }
        </div>

        @if (store.loading()) {
          <p class="px-4 py-6 text-sm text-ink-muted">Cargando…</p>
        } @else if (store.error()) {
          <p class="px-4 py-6 text-sm text-danger">{{ store.error() }}</p>
        } @else if (store.items().length === 0) {
          <div class="px-4 py-8 text-center">
            <p class="text-sm text-ink">Nada por leer</p>
            <p class="mt-1 text-xs text-ink-muted">
              Aquí llegan las asignaciones, los avisos de vencimiento y las revisiones de tus
              entregas.
            </p>
          </div>
        } @else {
          <ul>
            @for (item of store.items(); track item.id) {
              <li class="border-b border-line last:border-b-0">
                <button
                  type="button"
                  class="flex w-full flex-col items-start gap-1 border-l-2 px-4 py-3 text-left transition-colors hover:bg-sunken"
                  [class]="item.read_at ? 'border-l-transparent' : 'border-l-accent'"
                  (click)="openNotification(item)"
                >
                  <span class="flex w-full items-baseline gap-2">
                    <span
                      class="size-1.5 shrink-0 rounded-full"
                      [class]="dot(item)"
                      aria-hidden="true"
                    ></span>
                    <span class="flex-1 text-sm font-medium text-ink">{{ item.title }}</span>
                    @if (!item.read_at) {
                      <span class="sr-only">Sin leer.</span>
                    }
                  </span>
                  <span class="pl-3.5 text-sm text-ink-muted">{{ item.body }}</span>
                  <span class="pl-3.5 text-xs text-ink-faint">
                    {{ item.created_at | bogotaDate: 'datetime' }}
                  </span>
                </button>
              </li>
            }
          </ul>
        }
      </div>
    }
  `,
})
export class NotificationBellComponent {
  protected readonly store = inject(NotificationStore);
  private readonly router = inject(Router);
  private readonly host = inject(ElementRef<HTMLElement>);

  protected readonly open = signal(false);

  /** Más de 99 no aporta: lo que importa es «muchas», y tres dígitos no caben. */
  protected readonly badge = computed(() =>
    this.store.unread() > 99 ? '99+' : this.store.unread(),
  );

  protected readonly buttonLabel = computed(() => {
    const unread = this.store.unread();
    if (unread === 0) return 'Notificaciones. Ninguna sin leer.';
    return `Notificaciones. ${unread} sin leer.`;
  });

  protected toggle(): void {
    const next = !this.open();
    this.open.set(next);
    if (next) this.store.loadHistory();
  }

  protected close(): void {
    this.open.set(false);
  }

  /** Cerrar al tocar fuera. El panel no atrapa el foco: es una lista para
   * consultar de reojo, no un formulario. */
  protected onDocumentClick(event: MouseEvent): void {
    if (!this.open()) return;
    if (!this.host.nativeElement.contains(event.target as Node)) this.close();
  }

  protected dot(item: AppNotification): string {
    const tone = NOTIFICATION_TONE[item.kind];
    return {
      neutral: 'bg-ink-faint',
      notice: 'bg-notice',
      danger: 'bg-danger',
      success: 'bg-success',
    }[tone];
  }

  /**
   * Marca la notificación como leída y lleva al tablero del proyecto.
   *
   * No a la tarea: el tablero no tiene ruta para abrir una tarjeta concreta, y
   * prometer un enlace que aterriza en otro sitio es peor que llevar al lugar
   * donde la tarea se ve.
   */
  protected openNotification(item: AppNotification): void {
    this.store.markRead(item.id);
    if (item.project_id) {
      this.close();
      void this.router.navigate(['/proyectos', item.project_id, 'tablero']);
    }
  }
}
