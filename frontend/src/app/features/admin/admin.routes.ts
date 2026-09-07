import { Routes } from '@angular/router';

/** Pantallas de administración. El `adminGuard` ya se aplicó en el padre. */
export const ADMIN_ROUTES: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'usuarios' },
  {
    path: 'usuarios',
    title: 'Usuarios · KAIROS',
    loadComponent: () => import('./users.page').then((m) => m.UsersPage),
  },
  {
    path: 'invitaciones',
    title: 'Invitaciones · KAIROS',
    loadComponent: () => import('./invitations.page').then((m) => m.InvitationsPage),
  },
];
