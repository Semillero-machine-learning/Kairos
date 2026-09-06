import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { ApplicationConfig, provideBrowserGlobalErrorListeners } from '@angular/core';
import { provideRouter, withComponentInputBinding } from '@angular/router';

import { routes } from './app.routes';
import { coldStartInterceptor } from './core/http/cold-start.interceptor';

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    // `withComponentInputBinding` deja que los parámetros de ruta (el token de
    // invitación, por ejemplo) lleguen como `input()` al componente.
    provideRouter(routes, withComponentInputBinding()),
    provideHttpClient(withInterceptors([coldStartInterceptor])),
  ],
};
