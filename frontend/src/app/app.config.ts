import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter, withComponentInputBinding, withInMemoryScrolling } from '@angular/router';

import { routes } from './app.routes';
import { authInterceptor } from './core/auth/auth.interceptor';
import { coldStartInterceptor } from './core/http/cold-start.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // `withComponentInputBinding` deja que los parámetros de ruta (el token de
    // invitación, por ejemplo) lleguen como `input()` al componente.
    provideRouter(
      routes,
      withComponentInputBinding(),
      withInMemoryScrolling({ scrollPositionRestoration: 'enabled' }),
    ),
    // El orden importa: el de arranque en frío va por fuera, para que su
    // tiempo de espera cubra también el reintento posterior a renovar el token.
    provideHttpClient(withInterceptors([coldStartInterceptor, authInterceptor])),
  ],
};
