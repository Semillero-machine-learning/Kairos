/**
 * Endpoints del catálogo de lecciones (`api-contract.md` §8).
 *
 * El catálogo llega entero en una petición: son decenas de módulos como mucho,
 * y paginarlo sería complicar sin motivo. Lo que llega no es lo mismo para
 * todos —los borradores son de quien edita— pero eso lo decide el servidor;
 * aquí no se filtra nada.
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from './api-client.service';
import { Lesson, LessonDetail, LessonModule, LessonResource, ResourceType } from './models';

export interface ModuleBody {
  title: string;
  description: string | null;
}

export type LessonBody = ModuleBody;

export interface ResourceBody {
  type: ResourceType;
  title: string;
  url: string;
}

@Injectable({ providedIn: 'root' })
export class LessonsApi {
  private readonly api = inject(ApiClient);

  // --- Catálogo ---

  catalog(query?: string): Observable<LessonModule[]> {
    return this.api.get<LessonModule[]>('/lesson-modules', { q: query ?? null });
  }

  lesson(lessonId: string): Observable<LessonDetail> {
    return this.api.get<LessonDetail>(`/lessons/${lessonId}`);
  }

  // --- Módulos ---

  createModule(body: ModuleBody): Observable<LessonModule> {
    return this.api.post<LessonModule>('/lesson-modules', body);
  }

  updateModule(moduleId: string, body: Partial<ModuleBody>): Observable<LessonModule> {
    return this.api.patch<LessonModule>(`/lesson-modules/${moduleId}`, body);
  }

  publishModule(moduleId: string, published: boolean): Observable<LessonModule> {
    return this.api.post<LessonModule>(`/lesson-modules/${moduleId}/publish`, { published });
  }

  /** Sin `confirm` el backend responde 409 con el conteo de lecciones que se
   * perderían (RN-36). La pantalla lo usa para preguntar con el número exacto. */
  deleteModule(moduleId: string, confirm = false): Observable<void> {
    return this.api.delete<void>(`/lesson-modules/${moduleId}`, {
      confirm: confirm ? true : null,
    });
  }

  reorderModules(ids: string[]): Observable<LessonModule[]> {
    return this.api.post<LessonModule[]>('/lesson-modules/reorder', { ids });
  }

  // --- Lecciones ---

  createLesson(moduleId: string, body: LessonBody): Observable<Lesson> {
    return this.api.post<Lesson>(`/lesson-modules/${moduleId}/lessons`, body);
  }

  reorderLessons(moduleId: string, ids: string[]): Observable<Lesson[]> {
    return this.api.post<Lesson[]>(`/lesson-modules/${moduleId}/lessons/reorder`, { ids });
  }

  updateLesson(lessonId: string, body: Partial<LessonBody>): Observable<Lesson> {
    return this.api.patch<Lesson>(`/lessons/${lessonId}`, body);
  }

  publishLesson(lessonId: string, published: boolean): Observable<Lesson> {
    return this.api.post<Lesson>(`/lessons/${lessonId}/publish`, { published });
  }

  deleteLesson(lessonId: string): Observable<void> {
    return this.api.delete<void>(`/lessons/${lessonId}`);
  }

  // --- Recursos ---

  addResource(lessonId: string, body: ResourceBody): Observable<LessonResource> {
    return this.api.post<LessonResource>(`/lessons/${lessonId}/resources`, body);
  }

  reorderResources(lessonId: string, ids: string[]): Observable<LessonResource[]> {
    return this.api.post<LessonResource[]>(`/lessons/${lessonId}/resources/reorder`, { ids });
  }

  deleteResource(resourceId: string): Observable<void> {
    return this.api.delete<void>(`/resources/${resourceId}`);
  }
}
