import { Routes } from '@angular/router';

import { guestGuard } from '../../core/auth/guards';

/**
 * Rutas sin sesión.
 *
 * `/invitacion/:token` y `/restablecer/:token` no llevan `guestGuard`: alguien
 * con la sesión abierta puede llegar ahí desde un correo, y expulsarlo al
 * inicio sin explicación sería peor que dejarlo continuar.
 */
export const AUTH_ROUTES: Routes = [
  {
    path: 'ingresar',
    canActivate: [guestGuard],
    title: 'Ingresar · KAIROS',
    loadComponent: () => import('./login.page').then((m) => m.LoginPage),
  },
  {
    path: 'recuperar',
    canActivate: [guestGuard],
    title: 'Recuperar contraseña · KAIROS',
    loadComponent: () => import('./forgot-password.page').then((m) => m.ForgotPasswordPage),
  },
  {
    path: 'invitacion/:token',
    title: 'Invitación · KAIROS',
    loadComponent: () => import('./accept-invitation.page').then((m) => m.AcceptInvitationPage),
  },
  {
    path: 'restablecer/:token',
    title: 'Contraseña nueva · KAIROS',
    loadComponent: () => import('./reset-password.page').then((m) => m.ResetPasswordPage),
  },
];
