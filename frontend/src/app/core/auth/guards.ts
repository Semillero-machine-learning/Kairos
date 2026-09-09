/**
 * Guardas de ruta.
 *
 * Son comodidad, no seguridad: evitan que alguien aterrice en una pantalla que
 * el backend le va a negar de todas formas. Toda autorización real ocurre por
 * petición, en el servidor (RNF-05).
 */
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map, of } from 'rxjs';

import { SessionService } from './session.service';

/** Resuelve la sesión una sola vez por carga de la aplicación: al recargar en
 * una ruta protegida hay tokens guardados pero todavía no hay perfil. */
function ensureSession(session: SessionService) {
  if (session.isAuthenticated()) return of(true);
  if (!session.restoring()) return of(false);
  return session.restore();
}

export const authGuard: CanActivateFn = (_route, state) => {
  const session = inject(SessionService);
  const router = inject(Router);

  return ensureSession(session).pipe(
    map((ok) =>
      ok
        ? true
        : router.createUrlTree(['/ingresar'], {
            queryParams: { volverA: state.url },
          }),
    ),
  );
};

/** Solo administradores. Manda al inicio, no a una pantalla de error: el
 * usuario no hizo nada malo, simplemente no es su sitio. */
export const adminGuard: CanActivateFn = (route, state) => {
  const session = inject(SessionService);
  const router = inject(Router);

  return ensureSession(session).pipe(
    map((ok) => {
      if (!ok) {
        return router.createUrlTree(['/ingresar'], { queryParams: { volverA: state.url } });
      }
      return session.isAdmin() ? true : router.createUrlTree(['/inicio']);
    }),
  );
};

/** Solo quien puede escribir el catálogo de lecciones (RN-31). Como el
 * `adminGuard`, manda al catálogo y no a una pantalla de error: quien llega
 * aquí sin permiso quería ver lecciones, y ahí las tiene. */
export const lessonEditorGuard: CanActivateFn = (route, state) => {
  const session = inject(SessionService);
  const router = inject(Router);

  return ensureSession(session).pipe(
    map((ok) => {
      if (!ok) {
        return router.createUrlTree(['/ingresar'], { queryParams: { volverA: state.url } });
      }
      return session.canEditLessons() ? true : router.createUrlTree(['/lecciones']);
    }),
  );
};

/** Impide volver al ingreso con la sesión abierta. */
export const guestGuard: CanActivateFn = () => {
  const session = inject(SessionService);
  const router = inject(Router);

  return ensureSession(session).pipe(map((ok) => (ok ? router.createUrlTree(['/inicio']) : true)));
};
