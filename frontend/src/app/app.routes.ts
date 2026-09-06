import { Routes } from '@angular/router';

/**
 * Mapa de rutas. Cada funcionalidad se carga de forma diferida
 * (`architecture.md` §5) para que el paquete inicial sea pequeño.
 *
 * Las rutas visibles van en español porque aparecen en la barra de direcciones
 * y en los enlaces de los correos: `/invitacion/{token}` y
 * `/restablecer/{token}` los construye el backend.
 */
export const routes: Routes = [];
