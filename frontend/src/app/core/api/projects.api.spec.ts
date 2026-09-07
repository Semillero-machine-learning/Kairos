import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { ProjectsApi } from './projects.api';

describe('ProjectsApi', () => {
  let api: ProjectsApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(ProjectsApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('descarta los filtros vacíos de la lista', () => {
    api.list({ status: '', page: 2, size: 20 }).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects'));
    expect(request.request.params.has('status')).toBe(false);
    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.get('size')).toBe('20');
    request.flush({ items: [], total: 0, page: 2, size: 20 });
  });

  it('conserva el filtro de estado cuando trae valor', () => {
    api.list({ status: 'ARCHIVED' }).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects'));
    expect(request.request.params.get('status')).toBe('ARCHIVED');
    request.flush({ items: [], total: 0, page: 1, size: 20 });
  });

  it('envía el rol y la persona con los nombres del contrato', () => {
    api.addMember('p1', 'u1', 'r1').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1/members'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ user_id: 'u1', project_role_id: 'r1' });
    request.flush({});
  });

  it('el cambio de rol de un miembro va por PATCH a su propia ruta', () => {
    api.changeMemberRole('p1', 'u1', 'r2').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1/members/u1/role'));
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ project_role_id: 'r2' });
    request.flush({});
  });

  it('crear un rol manda nombre, color y permisos', () => {
    api
      .createRole('p1', {
        name: 'Revisor',
        color: '#B8860B',
        permissions: ['task.view', 'task.review'],
      })
      .subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/projects/p1/roles'));
    expect(request.request.body).toEqual({
      name: 'Revisor',
      color: '#B8860B',
      permissions: ['task.view', 'task.review'],
    });
    request.flush({});
  });

  it('el catálogo de permisos cuelga de la raíz, no del proyecto', () => {
    api.permissions().subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/permissions'));
    expect(request.request.method).toBe('GET');
    request.flush([]);
  });
});
