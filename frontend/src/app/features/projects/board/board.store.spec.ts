import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { Task, TaskStatus } from '../../../core/api/models';
import { BoardStore } from './board.store';

function task(id: string, status: TaskStatus, title = `Tarea ${id}`): Task {
  return {
    id,
    project_id: 'p1',
    title,
    description: null,
    status,
    periodicity: 'ONE_TIME',
    due_date: null,
    is_overdue: false,
    assignees: [],
    created_by: { id: 'u0', full_name: 'Carlos', email: 'carlos@ejemplo.com' },
    completed_at: null,
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
  };
}

describe('BoardStore', () => {
  let store: BoardStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), BoardStore],
    });
    store = TestBed.inject(BoardStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  function load(tasks: Task[]): void {
    store.load('p1');
    http
      .expectOne((r) => r.url.endsWith('/api/v1/projects/p1/tasks'))
      .flush({
        items: tasks,
        total: tasks.length,
        page: 1,
        size: 200,
      });
  }

  it('reparte las tareas en las cinco columnas, incluidas las vacías', () => {
    load([task('1', 'BACKLOG'), task('2', 'TODO'), task('3', 'TODO')]);

    const columnas = store.byStatus();
    expect(Object.keys(columnas)).toEqual(['BACKLOG', 'TODO', 'IN_PROGRESS', 'IN_REVIEW', 'DONE']);
    expect(columnas.TODO.map((t) => t.id)).toEqual(['2', '3']);
    expect(columnas.IN_PROGRESS).toEqual([]);
    expect(store.loading()).toBe(false);
  });

  it('pide el tablero completo en una sola petición', () => {
    store.load('p1');

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1/tasks'));
    expect(request.request.params.get('size')).toBe('200');
    request.flush({ items: [], total: 0, page: 1, size: 200 });
  });

  it('vuelve a pedir el tablero cuando cambia un filtro', () => {
    load([]);

    store.setFilters({ overdue: true });

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1/tasks'));
    expect(request.request.params.get('overdue')).toBe('true');
    expect(store.hasFilters()).toBe(true);
    request.flush({ items: [], total: 0, page: 1, size: 200 });
  });

  it('mueve la tarjeta de columna sin esperar al servidor', () => {
    load([task('1', 'TODO')]);

    store.move(store.tasks()[0], 'IN_PROGRESS');

    // Ya está pintada en la columna destino, antes de que llegue la respuesta.
    expect(store.byStatus().IN_PROGRESS.map((t) => t.id)).toEqual(['1']);
    http.expectOne((r) => r.url.endsWith('/api/v1/tasks/1/status')).flush(task('1', 'IN_PROGRESS'));
    expect(store.byStatus().IN_PROGRESS.map((t) => t.id)).toEqual(['1']);
  });

  it('devuelve la tarjeta a su columna si el backend rechaza el movimiento', () => {
    load([task('1', 'TODO')]);

    store.move(store.tasks()[0], 'IN_PROGRESS');
    http
      .expectOne((r) => r.url.endsWith('/api/v1/tasks/1/status'))
      .flush(
        {
          error: {
            code: 'FORBIDDEN',
            message: 'Se requiere el permiso «task.change_status_any».',
            details: null,
          },
        },
        { status: 403, statusText: 'Forbidden' },
      );

    // El que manda es el backend: la tarjeta vuelve donde estaba y se dice por qué.
    expect(store.byStatus().TODO.map((t) => t.id)).toEqual(['1']);
    expect(store.byStatus().IN_PROGRESS).toEqual([]);
    expect(store.actionError()).toContain('task.change_status_any');
  });

  it('reemplaza una tarea editada y agrega una nueva', () => {
    load([task('1', 'TODO')]);

    store.replace(task('1', 'TODO', 'Con otro título'));
    store.replace(task('2', 'BACKLOG'));

    expect(store.tasks().map((t) => t.title)).toEqual(['Con otro título', 'Tarea 2']);
  });

  it('quita del tablero la tarea eliminada', () => {
    load([task('1', 'TODO'), task('2', 'TODO')]);

    store.remove('1');

    expect(store.tasks().map((t) => t.id)).toEqual(['2']);
  });
});
