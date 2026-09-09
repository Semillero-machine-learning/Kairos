import { Routes } from '@angular/router';

import { lessonEditorGuard } from '../../core/auth/guards';

/**
 * Catálogo y editor (RF-46 a RF-51).
 *
 * `editor` va **antes** que `:lessonId`: el enrutador casa por orden de
 * declaración, y al revés «editor» se leería como el identificador de una
 * lección.
 */
export const LESSONS_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Lecciones · KAIROS',
    loadComponent: () => import('./lesson-catalog.page').then((m) => m.LessonCatalogPage),
  },
  {
    path: 'editor',
    canActivate: [lessonEditorGuard],
    title: 'Editar el catálogo · KAIROS',
    loadComponent: () => import('./lesson-editor.page').then((m) => m.LessonEditorPage),
  },
  {
    path: 'editor/:moduleId',
    canActivate: [lessonEditorGuard],
    title: 'Editar el módulo · KAIROS',
    loadComponent: () => import('./module-editor.page').then((m) => m.ModuleEditorPage),
  },
  {
    path: ':lessonId',
    title: 'Lección · KAIROS',
    loadComponent: () => import('./lesson-detail.page').then((m) => m.LessonDetailPage),
  },
];
