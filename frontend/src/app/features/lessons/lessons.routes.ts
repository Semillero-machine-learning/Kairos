import { Routes } from '@angular/router';

/** Catálogo de lecciones (RF-46, RF-48, RF-51). */
export const LESSONS_ROUTES: Routes = [
  {
    path: '',
    pathMatch: 'full',
    title: 'Lecciones · KAIROS',
    loadComponent: () => import('./lesson-catalog.page').then((m) => m.LessonCatalogPage),
  },
  {
    path: ':lessonId',
    title: 'Lección · KAIROS',
    loadComponent: () => import('./lesson-detail.page').then((m) => m.LessonDetailPage),
  },
];
