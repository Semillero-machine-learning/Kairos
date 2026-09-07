/**
 * Estado global del arranque en frío (RNF-02).
 *
 * El backend vive en el plan gratuito de Render y se suspende tras un rato sin
 * tráfico; la primera petición después de eso puede tardar decenas de segundos.
 * En vez de dejar la pantalla en blanco o mostrar un error genérico, contamos
 * cuántas peticiones llevan demasiado tiempo y la interfaz avisa que está
 * despertando el servidor.
 */
import { Injectable, computed, signal } from '@angular/core';

/** A partir de aquí se considera que el servidor está dormido. */
export const SLOW_REQUEST_MS = 3_000;

/** Tope absoluto de espera antes de dar la petición por fallida. */
export const REQUEST_TIMEOUT_MS = 90_000;

@Injectable({ providedIn: 'root' })
export class ColdStartService {
  private readonly slowRequests = signal(0);

  /** `true` mientras haya al menos una petición pasada de los 3 segundos. */
  readonly waking = computed(() => this.slowRequests() > 0);

  markSlow(): void {
    this.slowRequests.update((count) => count + 1);
  }

  clearSlow(): void {
    this.slowRequests.update((count) => Math.max(0, count - 1));
  }
}
