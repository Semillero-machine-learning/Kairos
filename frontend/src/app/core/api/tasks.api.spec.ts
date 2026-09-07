import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { TasksApi } from './tasks.api';

describe('TasksApi', () => {
  let api: TasksApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(TasksApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('descarta los filtros vacíos del tablero', () => {
    api.list('p1', { assignee_id: '', periodicity: '', overdue: false }).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1/tasks'));
    expect(request.request.params.has('assignee_id')).toBe(false);
    expect(request.request.params.has('periodicity')).toBe(false);
    // `overdue=false` viajaría como la cadena "false", que el backend leería
    // como un filtro puesto: se omite en vez de mandarse apagado.
    expect(request.request.params.has('overdue')).toBe(false);
    request.flush({ items: [], total: 0, page: 1, size: 50 });
  });

  it('manda los filtros que sí traen valor', () => {
    api.list('p1', { assignee_id: 'u1', periodicity: 'WEEKLY', overdue: true }).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1/tasks'));
    expect(request.request.params.get('assignee_id')).toBe('u1');
    expect(request.request.params.get('periodicity')).toBe('WEEKLY');
    expect(request.request.params.get('overdue')).toBe('true');
    request.flush({ items: [], total: 0, page: 1, size: 50 });
  });

  it('el cambio de estado va por POST a la ruta de la tarea', () => {
    api.changeStatus('t1', 'IN_PROGRESS').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/tasks/t1/status'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ status: 'IN_PROGRESS' });
    request.flush({});
  });

  it('la entrega manda descripción y enlace con los nombres del contrato', () => {
    api
      .submit('t1', {
        description: 'Entrené el modelo base con los datos de agosto.',
        commit_url: 'https://github.com/semillero-ml/anomalias/commit/a1b2c3d',
      })
      .subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/tasks/t1/submissions'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      description: 'Entrené el modelo base con los datos de agosto.',
      commit_url: 'https://github.com/semillero-ml/anomalias/commit/a1b2c3d',
    });
    request.flush({});
  });

  it('agregar un responsable usa el identificador del usuario', () => {
    api.addAssignee('t1', 'u1').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/tasks/t1/assignees'));
    expect(request.request.body).toEqual({ user_id: 'u1' });
    request.flush({});
  });

  it('«Mis tareas» cuelga de /me y no de un proyecto', () => {
    api.myTasks({ status: 'IN_PROGRESS', due_before: '2026-09-20' }).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/me/tasks'));
    expect(request.request.params.get('status')).toBe('IN_PROGRESS');
    expect(request.request.params.get('due_before')).toBe('2026-09-20');
    request.flush({ items: [], total: 0, page: 1, size: 20 });
  });
});
