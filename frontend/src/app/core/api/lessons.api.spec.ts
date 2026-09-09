import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';

import { LessonsApi } from './lessons.api';

describe('LessonsApi', () => {
  let api: LessonsApi;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    api = TestBed.inject(LessonsApi);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('pide el catálogo sin parámetros cuando no hay búsqueda', () => {
    api.catalog().subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules'));
    expect(request.request.params.has('q')).toBe(false);
    request.flush([]);
  });

  it('manda el término de búsqueda cuando lo hay', () => {
    api.catalog('redes').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules'));
    expect(request.request.params.get('q')).toBe('redes');
    request.flush([]);
  });

  it('publicar y despublicar es el mismo endpoint con el valor contrario', () => {
    api.publishModule('m1', false).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules/m1/publish'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ published: false });
    request.flush({});
  });

  it('el borrado de un módulo no confirma por su cuenta', () => {
    api.deleteModule('m1').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules/m1'));
    expect(request.request.method).toBe('DELETE');
    // Sin `confirm` el backend responde 409 con el conteo (RN-36), que es
    // justo lo que la pantalla necesita para preguntar con el número exacto.
    expect(request.request.params.has('confirm')).toBe(false);
    request.flush(null);
  });

  it('confirmar el borrado viaja como parámetro de consulta', () => {
    api.deleteModule('m1', true).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules/m1'));
    expect(request.request.params.get('confirm')).toBe('true');
    request.flush(null);
  });

  it('reordenar manda la lista completa de identificadores', () => {
    api.reorderModules(['b', 'a']).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules/reorder'));
    expect(request.request.body).toEqual({ ids: ['b', 'a'] });
    request.flush([]);
  });

  it('las lecciones se crean colgando de su módulo', () => {
    api.createLesson('m1', { title: 'Perceptrón', description: null }).subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules/m1/lessons'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({ title: 'Perceptrón', description: null });
    request.flush({});
  });

  it('el orden de las lecciones cuelga del módulo y el de los recursos, de la lección', () => {
    api.reorderLessons('m1', ['l2', 'l1']).subscribe();
    api.reorderResources('l1', ['r2', 'r1']).subscribe();

    http.expectOne((r) => r.url.endsWith('/api/v1/lesson-modules/m1/lessons/reorder')).flush([]);
    http.expectOne((r) => r.url.endsWith('/api/v1/lessons/l1/resources/reorder')).flush([]);
  });

  it('un recurso viaja con su tipo, su título y su enlace', () => {
    api
      .addResource('l1', {
        type: 'NOTEBOOK',
        title: 'Cuaderno',
        url: 'https://github.com/semillero-ml/redes',
      })
      .subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/lessons/l1/resources'));
    expect(request.request.body).toEqual({
      type: 'NOTEBOOK',
      title: 'Cuaderno',
      url: 'https://github.com/semillero-ml/redes',
    });
    request.flush({});
  });

  it('el recurso se borra por su propia ruta, no por la de la lección', () => {
    api.deleteResource('r1').subscribe();

    const request = http.expectOne((r) => r.url.endsWith('/api/v1/resources/r1'));
    expect(request.request.method).toBe('DELETE');
    request.flush(null);
  });
});
