/**
 * Adjunta el token de acceso y renueva de forma transparente ante un 401.
 *
 * Las peticiones que fallan mientras hay un refresco en curso no disparan uno
 * nuevo: `SessionService.refresh()` comparte el que ya está en vuelo, y cada
 * petición se reintenta una sola vez con el token nuevo.
 */
import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap, throwError } from 'rxjs';

import { SKIP_AUTH_REFRESH, SessionService } from './session.service';

function withToken<T>(req: HttpRequest<T>, token: string): HttpRequest<T> {
  return req.clone({ setHeaders: { Authorization: `Bearer ${token}` } });
}

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const session = inject(SessionService);
  const router = inject(Router);

  const token = session.accessToken();
  const outgoing = token ? withToken(req, token) : req;

  return next(outgoing).pipe(
    catchError((error: unknown) => {
      const is401 = error instanceof HttpErrorResponse && error.status === 401;
      const skipRefresh = req.context.get(SKIP_AUTH_REFRESH);

      // Sin sesión guardada no hay nada que renovar: el 401 es la respuesta
      // real (credenciales incorrectas, por ejemplo) y le toca a la pantalla.
      if (!is401 || skipRefresh || !session.hasStoredSession()) {
        return throwError(() => error);
      }

      return session.refresh().pipe(
        switchMap((fresh) => next(withToken(req, fresh))),
        catchError((refreshError: unknown) => {
          // El refresco tampoco sirvió: la sesión terminó de verdad.
          session.clear();
          void router.navigate(['/ingresar'], {
            queryParams: { expirada: '1' },
          });
          return throwError(() => refreshError);
        }),
      );
    }),
  );
};
