/**
 * Estado de la campana: contador de no leídas e historial.
 *
 * El contador se consulta cada 60 segundos **mientras la pestaña esté visible**
 * (`api-contract.md` §7). No hay WebSockets ni eventos del servidor a propósito:
 * mantener una conexión abierta contra un servicio que se suspende a los quince
 * minutos de inactividad no tiene sentido, y una consulta de un entero cada
 * minuto es más barata que reconectar.
 *
 * El historial no se sondea: solo se pide al abrir el panel. Lo que cambia
 * seguido es el número; la lista se mira cuando alguien decide mirarla.
 */
import { DestroyRef, Injectable, inject, signal } from '@angular/core';

import { ApiError } from '../api/api-error';
import { AppNotification } from '../api/models';
import { NotificationsApi } from '../api/notifications.api';
import { SessionService } from '../auth/session.service';

const POLL_MS = 60_000;

@Injectable({ providedIn: 'root' })
export class NotificationStore {
  private readonly api = inject(NotificationsApi);
  private readonly session = inject(SessionService);

  private readonly unreadSignal = signal(0);
  private readonly itemsSignal = signal<AppNotification[]>([]);
  private readonly loadingSignal = signal(false);
  private readonly errorSignal = signal('');

  readonly unread = this.unreadSignal.asReadonly();
  readonly items = this.itemsSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();

  private timer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    document.addEventListener('visibilitychange', this.onVisibilityChange);
    inject(DestroyRef).onDestroy(() => {
      document.removeEventListener('visibilitychange', this.onVisibilityChange);
      this.stop();
    });
  }

  /** Arranca el sondeo. Lo llama el armazón, que solo existe con sesión abierta. */
  start(): void {
    if (this.timer !== null) return;
    this.refreshCount();
    this.timer = setInterval(() => this.refreshCount(), POLL_MS);
  }

  stop(): void {
    if (this.timer === null) return;
    clearInterval(this.timer);
    this.timer = null;
  }

  /** Al cerrar sesión: el siguiente que entre no hereda el número del anterior. */
  reset(): void {
    this.stop();
    this.unreadSignal.set(0);
    this.itemsSignal.set([]);
    this.errorSignal.set('');
  }

  refreshCount(): void {
    if (!this.session.isAuthenticated()) return;
    this.api.unreadCount().subscribe({
      next: ({ unread }) => this.unreadSignal.set(unread),
      // Un fallo del contador no merece un mensaje: el número se queda como
      // estaba y el siguiente sondeo lo corrige.
      error: () => undefined,
    });
  }

  loadHistory(): void {
    this.loadingSignal.set(true);
    this.errorSignal.set('');
    this.api.list(false, 1, 20).subscribe({
      next: (page) => {
        this.itemsSignal.set(page.items);
        this.loadingSignal.set(false);
      },
      error: (err: ApiError) => {
        this.errorSignal.set(err.message);
        this.loadingSignal.set(false);
      },
    });
  }

  markRead(id: string): void {
    const target = this.itemsSignal().find((item) => item.id === id);
    if (!target || target.read_at !== null) return;
    this.api.markRead(id).subscribe({
      next: (updated) => {
        this.itemsSignal.update((items) => items.map((item) => (item.id === id ? updated : item)));
        this.refreshCount();
      },
      error: (err: ApiError) => this.errorSignal.set(err.message),
    });
  }

  markAllRead(): void {
    this.api.markAllRead().subscribe({
      next: () => {
        const now = new Date().toISOString();
        this.itemsSignal.update((items) =>
          items.map((item) => (item.read_at ? item : { ...item, read_at: now })),
        );
        this.unreadSignal.set(0);
      },
      error: (err: ApiError) => this.errorSignal.set(err.message),
    });
  }

  /**
   * Sondear una pestaña de fondo gasta el plan gratuito de Render sin que nadie
   * lea el resultado. Al volver se pide de inmediato, para que el número no
   * aparezca con un minuto de retraso.
   */
  private readonly onVisibilityChange = (): void => {
    if (document.visibilityState === 'visible') {
      this.start();
    } else {
      this.stop();
    }
  };
}
