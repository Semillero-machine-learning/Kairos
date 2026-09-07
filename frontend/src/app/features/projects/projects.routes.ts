import { Routes } from '@angular/router';

/**
 * Rutas de proyectos.
 *
 * El detalle vive bajo un armazón que carga el proyecto una vez y lo comparte
 * con las tres pestañas, para no pedir el mismo detalle tres veces al cambiar
 * de sección. Sin guardas propias: quien no sea miembro recibe un 404 del
 * backend y ve el estado vacío correspondiente.
 */
export const PROJECTS_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Proyectos · KAIROS',
    loadComponent: () => import('./projects-list.page').then((m) => m.ProjectsListPage),
  },
  {
    path: ':projectId',
    title: 'Proyecto · KAIROS',
    loadComponent: () =>
      import('./project-shell.component').then((m) => m.ProjectShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'resumen' },
      {
        path: 'resumen',
        loadComponent: () =>
          import('./project-overview.page').then((m) => m.ProjectOverviewPage),
      },
      {
        path: 'miembros',
        loadComponent: () =>
          import('./project-members.page').then((m) => m.ProjectMembersPage),
      },
      {
        path: 'roles',
        loadComponent: () => import('./project-roles.page').then((m) => m.ProjectRolesPage),
      },
    ],
  },
];
