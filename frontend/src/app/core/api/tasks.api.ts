/**
 * Endpoints de tareas, responsables y entregas (`api-contract.md` §5, §6).
 *
 * Aquí no se decide nada. Qué transiciones existen y quién puede hacerlas lo
 * resuelve el backend en cada petición: la interfaz solo pregunta y pinta.
 */
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { ApiClient } from './api-client.service';
import { MyTask, Page, Submission, Task, TaskPeriodicity, TaskStatus } from './models';

export interface TaskFilters {
  status?: TaskStatus | '';
  assignee_id?: string | '';
  periodicity?: TaskPeriodicity | '';
  overdue?: boolean;
  page?: number;
  size?: number;
}

export interface MyTaskFilters {
  status?: TaskStatus | '';
  due_before?: string;
  page?: number;
  size?: number;
}

export interface TaskCreateBody {
  title: string;
  description: string | null;
  periodicity: TaskPeriodicity;
  due_date: string | null;
  assignee_ids: string[];
}

export interface TaskUpdateBody {
  title?: string;
  description?: string | null;
  periodicity?: TaskPeriodicity;
  due_date?: string | null;
}

export interface SubmissionBody {
  description: string;
  commit_url: string | null;
}

@Injectable({ providedIn: 'root' })
export class TasksApi {
  private readonly api = inject(ApiClient);

  // --- Tablero ---

  list(projectId: string, filters: TaskFilters = {}): Observable<Page<Task>> {
    return this.api.get<Page<Task>>(`/projects/${projectId}/tasks`, {
      ...filters,
      // `false` viajaría como "false" y el backend lo leería como filtro puesto.
      overdue: filters.overdue ? true : null,
    });
  }

  create(projectId: string, body: TaskCreateBody): Observable<Task> {
    return this.api.post<Task>(`/projects/${projectId}/tasks`, body);
  }

  // --- Una tarea ---

  get(taskId: string): Observable<Task> {
    return this.api.get<Task>(`/tasks/${taskId}`);
  }

  update(taskId: string, body: TaskUpdateBody): Observable<Task> {
    return this.api.patch<Task>(`/tasks/${taskId}`, body);
  }

  remove(taskId: string): Observable<void> {
    return this.api.delete<void>(`/tasks/${taskId}`);
  }

  changeStatus(taskId: string, status: TaskStatus): Observable<Task> {
    return this.api.post<Task>(`/tasks/${taskId}/status`, { status });
  }

  addAssignee(taskId: string, userId: string): Observable<Task> {
    return this.api.post<Task>(`/tasks/${taskId}/assignees`, { user_id: userId });
  }

  removeAssignee(taskId: string, userId: string): Observable<Task> {
    return this.api.delete<Task>(`/tasks/${taskId}/assignees/${userId}`);
  }

  // --- Entregas ---

  submissions(taskId: string): Observable<Submission[]> {
    return this.api.get<Submission[]>(`/tasks/${taskId}/submissions`);
  }

  submit(taskId: string, body: SubmissionBody): Observable<Submission> {
    return this.api.post<Submission>(`/tasks/${taskId}/submissions`, body);
  }

  // --- Entre proyectos ---

  myTasks(filters: MyTaskFilters = {}): Observable<Page<MyTask>> {
    return this.api.get<Page<MyTask>>('/me/tasks', { ...filters });
  }
}
