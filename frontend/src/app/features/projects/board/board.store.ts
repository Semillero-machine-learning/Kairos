/**
 * Estado del tablero de un proyecto.
 *
 * Los filtros viajan al backend en vez de aplicarse aquí: «vencida» es una
 * comparación contra la fecha de Colombia, y hacerla dos veces —una en el
 * servidor para el filtro y otra en el navegador para la insignia— es pedir que
 * un día no coincidan. El tablero completo llega en una sola petición, que a la
 * escala prevista son decenas de tareas (RNF-04).
 */
import { Injectable, computed, inject, signal } from '@angular/core';

import { ApiError } from '../../../core/api/api-error';
import { TASK_STATUS_ORDER, Task, TaskPeriodicity, TaskStatus } from '../../../core/api/models';
import { TasksApi } from '../../../core/api/tasks.api';

export interface BoardFilters {
  assigneeId: string;
  periodicity: TaskPeriodicity | '';
  overdue: boolean;
}

const NO_FILTERS: BoardFilters = { assigneeId: '', periodicity: '', overdue: false };

export type TasksByStatus = Record<TaskStatus, Task[]>;

@Injectable()
export class BoardStore {
  private readonly api = inject(TasksApi);

  private readonly tasksSignal = signal<Task[]>([]);
  private readonly loadingSignal = signal(true);
  private readonly errorSignal = signal('');
  private readonly actionErrorSignal = signal('');
  private readonly filtersSignal = signal<BoardFilters>(NO_FILTERS);
  private projectId = '';

  readonly tasks = this.tasksSignal.asReadonly();
  readonly loading = this.loadingSignal.asReadonly();
  readonly error = this.errorSignal.asReadonly();
  /** Lo que falló en la última acción, sin tumbar el tablero que ya se ve. */
  readonly actionError = this.actionErrorSignal.asReadonly();
  readonly filters = this.filtersSignal.asReadonly();

  readonly hasFilters = computed(() => {
    const { assigneeId, periodicity, overdue } = this.filtersSignal();
    return assigneeId !== '' || periodicity !== '' || overdue;
  });

  /** Las cinco columnas, siempre las cinco, aunque alguna quede vacía. */
  readonly byStatus = computed<TasksByStatus>(() => {
    const groups = Object.fromEntries(
      TASK_STATUS_ORDER.map((status) => [status, [] as Task[]]),
    ) as TasksByStatus;
    for (const task of this.tasksSignal()) groups[task.status].push(task);
    return groups;
  });

  load(projectId: string): void {
    this.projectId = projectId;
    this.loadingSignal.set(true);
    this.fetch();
  }

  setFilters(patch: Partial<BoardFilters>): void {
    this.filtersSignal.update((current) => ({ ...current, ...patch }));
    this.fetch();
  }

  clearFilters(): void {
    this.filtersSignal.set(NO_FILTERS);
    this.fetch();
  }

  private fetch(): void {
    const { assigneeId, periodicity, overdue } = this.filtersSignal();
    this.errorSignal.set('');
    this.actionErrorSignal.set('');
    this.api
      .list(this.projectId, {
        assignee_id: assigneeId,
        periodicity,
        overdue,
        size: 200,
      })
      .subscribe({
        next: (page) => {
          this.tasksSignal.set(page.items);
          this.loadingSignal.set(false);
        },
        error: (err: ApiError) => {
          this.errorSignal.set(err.message);
          this.loadingSignal.set(false);
        },
      });
  }

  /** Mueve una tarea de columna. Pinta el destino de inmediato y lo revierte si
   * el backend dice que no: el que manda es él. */
  move(task: Task, status: TaskStatus): void {
    const previous = task.status;
    this.replace({ ...task, status });
    this.actionErrorSignal.set('');
    this.api.changeStatus(task.id, status).subscribe({
      next: (updated) => this.replace(updated),
      error: (err: ApiError) => {
        this.replace({ ...task, status: previous });
        this.actionErrorSignal.set(err.message);
      },
    });
  }

  remove(taskId: string): void {
    this.tasksSignal.update((tasks) => tasks.filter((task) => task.id !== taskId));
  }

  add(task: Task): void {
    this.tasksSignal.update((tasks) => [...tasks, task]);
  }

  replace(task: Task): void {
    this.tasksSignal.update((tasks) =>
      tasks.some((current) => current.id === task.id)
        ? tasks.map((current) => (current.id === task.id ? task : current))
        : [...tasks, task],
    );
  }

  clearActionError(): void {
    this.actionErrorSignal.set('');
  }
}
