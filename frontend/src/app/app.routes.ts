import { Routes } from '@angular/router';

import { adminGuard, authGuard } from './core/auth/guards';
import { AppShellComponent } from './core/layout/app-shell.component';
import { AUTH_ROUTES } from './features/auth/auth.routes';

/**
 * Mapa de rutas.
 *
 * Cada pantalla se carga de forma diferida con `loadComponent`
 * (`architecture.md` §5). Las definiciones de las rutas de acceso se importan
 * directamente en vez de con `loadChildren` bajo una ruta vacía: el archivo
 * solo contiene configuración, los componentes siguen siendo diferidos, y así
 * no hay dos rutas de camino vacío compitiendo por la misma URL.
 *
 * Las rutas visibles van en español porque aparecen en la barra de direcciones
 * y en los enlaces de los correos: `/invitacion/{token}` y
 * `/restablecer/{token}` los construye el backend.
 */
export const routes: Routes = [
  ...AUTH_ROUTES,
  { path: '', pathMatch: 'full', redirectTo: 'inicio' },
  {
    path: '',
    component: AppShellComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'inicio',
        title: 'Inicio · KAIROS',
        loadComponent: () => import('./features/dashboard/home.page').then((m) => m.HomePage),
      },
      {
        path: 'proyectos',
        loadChildren: () =>
          import('./features/projects/projects.routes').then((m) => m.PROJECTS_ROUTES),
      },
      {
        path: 'lecciones',
        loadChildren: () =>
          import('./features/lessons/lessons.routes').then((m) => m.LESSONS_ROUTES),
      },
      {
        path: 'perfil',
        title: 'Mi perfil · KAIROS',
        loadComponent: () => import('./features/profile/profile.page').then((m) => m.ProfilePage),
      },
      {
        path: 'admin',
        canActivate: [adminGuard],
        loadChildren: () => import('./features/admin/admin.routes').then((m) => m.ADMIN_ROUTES),
      },
    ],
  },
  {
    path: '**',
    title: 'Página no encontrada · KAIROS',
    loadComponent: () => import('./features/not-found.page').then((m) => m.NotFoundPage),
  },
];
