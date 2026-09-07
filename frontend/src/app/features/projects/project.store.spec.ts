import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { PermissionCode, ProjectDetail } from '../../core/api/models';
import { ProjectStore } from './project.store';

function detail(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    id: 'p1',
    name: 'Detección de anomalías',
    description: null,
    status: 'ACTIVE',
    start_date: null,
    archived_at: null,
    member_count: 1,
    task_counts: { BACKLOG: 0, TODO: 0, IN_PROGRESS: 0, IN_REVIEW: 0, DONE: 0 },
    my_permissions: ['task.view', 'task.comment'] as PermissionCode[],
    my_role: { id: 'r1', name: 'Colaborador', color: '#2E5C8A' },
    created_at: '2026-09-01T12:00:00Z',
    updated_at: '2026-09-01T12:00:00Z',
    ...overrides,
  };
}

describe('ProjectStore', () => {
  let store: ProjectStore;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), ProjectStore],
    });
    store = TestBed.inject(ProjectStore);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sin proyecto cargado no habilita nada', () => {
    expect(store.can('task.view')).toBe(false);
  });

  it('habilita solo los permisos que trae el proyecto', () => {
    store.set(detail());

    expect(store.can('task.view')).toBe(true);
    expect(store.can('task.comment')).toBe(true);
    expect(store.can('role.manage')).toBe(false);
    expect(store.can('member.add')).toBe(false);
  });

  it('un proyecto archivado no habilita ninguna escritura', () => {
    // RN-15: solo lectura absoluta. El permiso sigue en la lista, pero mientras
    // el proyecto esté archivado no se ofrece la acción.
    store.set(
      detail({
        status: 'ARCHIVED',
        archived_at: '2026-09-05T12:00:00Z',
        my_permissions: ['task.view', 'project.edit', 'member.add'] as PermissionCode[],
      }),
    );

    expect(store.isArchived()).toBe(true);
    expect(store.can('task.view')).toBe(true);
    expect(store.can('project.edit')).toBe(false);
    expect(store.can('member.add')).toBe(false);
  });

  it('desarchivar sigue disponible con el proyecto archivado', () => {
    store.set(
      detail({
        status: 'ARCHIVED',
        archived_at: '2026-09-05T12:00:00Z',
        my_permissions: ['task.view', 'project.archive'] as PermissionCode[],
      }),
    );

    expect(store.can('project.archive')).toBe(true);
  });

  it('carga el detalle del proyecto', () => {
    store.load('p1');

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1'));
    expect(request.request.method).toBe('GET');
    request.flush(detail());

    expect(store.loading()).toBe(false);
    expect(store.project()?.name).toBe('Detección de anomalías');
    expect(store.error()).toBe('');
  });

  it('un proyecto ajeno deja el estado vacío y el mensaje del backend', () => {
    store.load('ajeno');

    http
      .expectOne((r) => r.url.endsWith('/api/v1/projects/ajeno'))
      .flush(
        { error: { code: 'NOT_FOUND', message: 'Proyecto no encontrado.', details: null } },
        { status: 404, statusText: 'Not Found' },
      );

    expect(store.project()).toBeNull();
    expect(store.error()).toBe('Proyecto no encontrado.');
    expect(store.loading()).toBe(false);
    expect(store.can('task.view')).toBe(false);
  });
});
