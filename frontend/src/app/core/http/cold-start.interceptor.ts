/**
 * Interceptor de arranque en frío (RNF-02, CLAUDE.md).
 *
 * Si una petición pasa de `SLOW_REQUEST_MS`, avisa al `ColdStartService` para
 * que la interfaz muestre "Despertando el servidor...". A los
 * `REQUEST_TIMEOUT_MS` la corta con un `TimeoutError` propio, que
 * `toApiError` traduce a un mensaje honesto. Nunca una pantalla en blanco.
 */
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { throwError, timer } from 'rxjs';
import { finalize, timeout } from 'rxjs/operators';

import { TimeoutError } from '../api/api-error';
import { REQUEST_TIMEOUT_MS, SLOW_REQUEST_MS, ColdStartService } from './cold-start.service';

export const coldStartInterceptor: HttpInterceptorFn = (req, next) => {
  const coldStart = inject(ColdStartService);
  let markedSlow = false;

  // `timer` en vez de setTimeout para poder cancelarlo con el propio flujo.
  const slowTimer = timer(SLOW_REQUEST_MS).subscribe(() => {
    markedSlow = true;
    coldStart.markSlow();
  });

  return next(req).pipe(
    timeout({
      each: REQUEST_TIMEOUT_MS,
      with: () => throwError(() => new TimeoutError()),
    }),
    finalize(() => {
      slowTimer.unsubscribe();
      if (markedSlow) coldStart.clearSlow();
    }),
  );
};
